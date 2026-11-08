from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import CashDrawerError, NotFoundError, ValidationError
from app.models.abono import AbonoCliente
from app.models.caja import EstadoCaja, SesionCaja
from app.models.sucursal import Cliente
from app.models.venta import EstadoVenta, Venta
from app.services.auditoria_service import registrar_auditoria

METODOS_ABONO = ("efectivo", "transferencia")


def _d(valor: object | None) -> Decimal:
    return Decimal(str(valor if valor is not None else 0))


async def calcular_saldo(db: AsyncSession, id_cliente: int) -> Decimal:
    result = await db.execute(
        select(func.coalesce(func.sum(Venta.total - Venta.monto_abonado - Venta.monto_devuelto), 0)).where(
            Venta.id_cliente == id_cliente,
            Venta.estado == EstadoVenta.pendiente,
        )
    )
    return Decimal(str(result.scalar() or 0))


async def registrar_abono(
    db: AsyncSession,
    id_cliente: int,
    id_venta: int | None,
    monto: Decimal,
    id_usuario: int,
    observacion: str | None = None,
    metodo: str = "efectivo",
    id_sesion_caja: int | None = None,
) -> AbonoCliente:
    """Abono a una venta fiada o a la cuenta del cliente.

    Solo el abono en efectivo dentro de una caja abierta suma al efectivo
    esperado del cierre (RN-03); la transferencia no toca el cajón.
    """
    if metodo not in METODOS_ABONO:
        raise ValidationError(f"Método de abono inválido: {metodo}")

    monto = _d(monto)
    if monto <= 0:
        raise ValidationError("El abono debe ser mayor a cero")

    cliente = await db.get(Cliente, id_cliente)
    if cliente is None:
        raise NotFoundError("Cliente", id_cliente)

    venta: Venta | None = None
    if id_venta is not None:
        venta = await db.get(Venta, id_venta)
        if venta is None:
            raise NotFoundError("Venta", id_venta)
        if venta.id_cliente != id_cliente:
            raise ValidationError("La venta no pertenece al cliente indicado")
        if venta.estado == EstadoVenta.anulada:
            raise ValidationError("No se puede abonar a una venta anulada")
        saldo_venta = _d(venta.total) - _d(venta.monto_abonado) - _d(venta.monto_devuelto)
        if monto > saldo_venta:
            raise ValidationError(
                f"El abono excede el saldo de la venta (${saldo_venta:.2f})"
            )
    else:
        saldo_actual = await calcular_saldo(db, id_cliente)
        if monto > saldo_actual:
            raise ValidationError(
                f"El abono excede el saldo deudor del cliente (${saldo_actual:.2f})"
            )

    sesion: SesionCaja | None = None
    if metodo == "efectivo" and id_sesion_caja is not None:
        sesion = await db.get(SesionCaja, id_sesion_caja)
        if sesion is None or sesion.estado != EstadoCaja.abierta:
            raise CashDrawerError("La caja indicada no está abierta")
        if sesion.id_usuario_creador != id_usuario:
            raise CashDrawerError("Solo el cajero de la sesión puede registrar abonos en efectivo")
        sesion.abonos_efectivo = float(_d(sesion.abonos_efectivo) + monto)

    abono = AbonoCliente(
        id_cliente=id_cliente,
        id_venta=id_venta,
        id_usuario=id_usuario,
        monto=float(monto),
        tipo="abono",
        metodo=metodo,
        id_sesion_caja=id_sesion_caja if sesion is not None else None,
        id_sucursal=venta.id_sucursal if venta is not None else (sesion.id_sucursal if sesion else None),
        observacion=observacion,
    )
    db.add(abono)

    if venta is not None:
        venta.monto_abonado = float(_d(venta.monto_abonado) + monto)
        saldo_restante = _d(venta.total) - _d(venta.monto_abonado) - _d(venta.monto_devuelto)
        if saldo_restante <= 0:
            venta.estado = EstadoVenta.pagada

    await db.flush()

    await registrar_auditoria(
        db,
        "cliente.abono",
        f"Abono de ${monto:.0f} ({metodo}) del cliente {cliente.nombre}",
        id_usuario=id_usuario,
        id_sucursal=abono.id_sucursal,
        datos={
            "id_abono": abono.id_abono,
            "id_venta": id_venta,
            "monto": float(monto),
            "metodo": metodo,
        },
    )
    return abono
