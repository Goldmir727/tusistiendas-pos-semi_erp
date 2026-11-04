from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError, ValidationError
from app.models.abono import AbonoCliente
from app.models.sucursal import Cliente
from app.models.venta import EstadoVenta, Venta


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
) -> AbonoCliente:
    cliente = await db.get(Cliente, id_cliente)
    if not cliente:
        raise NotFoundError("Cliente", id_cliente)

    if id_venta:
        venta = await db.get(Venta, id_venta)
        if not venta:
            raise NotFoundError("Venta", id_venta)
        saldo_venta = Decimal(str(venta.total)) - Decimal(str(venta.monto_abonado)) - Decimal(str(venta.monto_devuelto))
        if monto <= 0 or monto > saldo_venta:
            raise ValidationError("Monto de abono excede el saldo de la venta")

        abono = AbonoCliente(
            id_cliente=id_cliente,
            id_venta=id_venta,
            id_usuario=id_usuario,
            monto=float(monto),
            tipo="abono",
            observacion=observacion,
        )
        db.add(abono)
        venta.monto_abonado = float(Decimal(str(venta.monto_abonado)) + monto)
        saldo_restante = Decimal(str(venta.total)) - Decimal(str(venta.monto_abonado)) - Decimal(str(venta.monto_devuelto))
        if saldo_restante <= 0:
            venta.estado = EstadoVenta.pagada
        return abono

    saldo_actual = await calcular_saldo(db, id_cliente)
    if monto <= 0 or monto > saldo_actual:
        raise ValidationError("Monto de abono inválido o excede el saldo deudor")

    abono = AbonoCliente(
        id_cliente=id_cliente,
        id_usuario=id_usuario,
        monto=float(monto),
        tipo="abono",
        observacion=observacion,
    )
    db.add(abono)
    return abono