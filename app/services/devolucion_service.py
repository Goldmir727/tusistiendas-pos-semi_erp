from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import AuthorizationError, ConflictError, NotFoundError, ValidationError
from app.models.caja import EstadoCaja, SesionCaja
from app.models.comprobante import Comprobante, EstadoComprobante, NumeracionDIAN, TipoComprobante
from app.models.configuracion import Configuracion
from app.models.devolucion import Devolucion, DevolucionDetalle, EstadoDevolucion
from app.models.producto import MovimientoStock, Producto
from app.models.usuario import RolEnum
from app.models.venta import EstadoVenta, Venta
from app.schemas.devolucion import DevolucionCreate
from app.services.auditoria_service import registrar_auditoria

CENTAVO = Decimal("0.01")
METODOS_REEMBOLSO = ("efectivo", "transferencia", "nota_credito")


def _d(valor: object | None) -> Decimal:
    return Decimal(str(valor if valor is not None else 0))


async def _leer_config(db: AsyncSession, clave: str, default: str) -> str:
    result = await db.execute(select(Configuracion).where(Configuracion.clave == clave))
    config = result.scalar_one_or_none()
    return config.valor if config else default


async def _acumulado_turno_cajero(db: AsyncSession, id_usuario: int) -> Decimal:
    """Devoluciones aprobadas desde la apertura de la caja del cajero (o del día)."""
    sesion = (
        await db.execute(
            select(SesionCaja).where(
                SesionCaja.id_usuario_creador == id_usuario,
                SesionCaja.estado == EstadoCaja.abierta,
            )
        )
    ).scalar_one_or_none()
    desde = sesion.fecha_apertura if sesion is not None else datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    result = await db.execute(
        select(func.coalesce(func.sum(Devolucion.monto), 0)).where(
            Devolucion.id_usuario_solicita == id_usuario,
            Devolucion.fecha >= desde,
            Devolucion.estado == EstadoDevolucion.aprobada,
        )
    )
    return Decimal(str(result.scalar() or 0))


async def _cantidades_comprometidas(db: AsyncSession, id_venta: int) -> dict[int, Decimal]:
    """Unidades ya devueltas o pendientes de aprobación por producto."""
    result = await db.execute(
        select(DevolucionDetalle.id_producto, func.coalesce(func.sum(DevolucionDetalle.cantidad), 0))
        .join(Devolucion, Devolucion.id_devolucion == DevolucionDetalle.id_devolucion)
        .where(
            Devolucion.id_venta == id_venta,
            Devolucion.estado.in_([EstadoDevolucion.aprobada, EstadoDevolucion.pendiente_aprobacion]),
        )
        .group_by(DevolucionDetalle.id_producto)
    )
    return {int(fila[0]): Decimal(str(fila[1])) for fila in result.all()}


async def crear_devolucion(db: AsyncSession, data: DevolucionCreate, solicitante) -> Devolucion:
    result_venta = await db.execute(
        select(Venta).options(selectinload(Venta.detalles)).where(Venta.id_venta == data.id_venta)
    )
    venta = result_venta.scalar_one_or_none()
    if venta is None:
        raise NotFoundError("Venta", data.id_venta)
    if venta.estado == EstadoVenta.anulada:
        raise ConflictError("La venta ya está anulada")
    if data.metodo_reembolso not in METODOS_REEMBOLSO:
        raise ValidationError(f"Método de reembolso inválido: {data.metodo_reembolso}")

    lineas_venta = {d.id_producto: d for d in venta.detalles}
    vendido: dict[int, Decimal] = {}
    for detalle in venta.detalles:
        vendido[detalle.id_producto] = vendido.get(detalle.id_producto, Decimal("0")) + _d(detalle.cantidad)

    comprometido = await _cantidades_comprometidas(db, venta.id_venta)

    pedido: dict[int, Decimal] = {}
    for det in data.detalles:
        cantidad = _d(det.cantidad)
        if cantidad <= 0:
            raise ValidationError("La cantidad a devolver debe ser mayor a cero")
        pedido[det.id_producto] = pedido.get(det.id_producto, Decimal("0")) + cantidad

    for id_producto, cantidad in pedido.items():
        if id_producto not in vendido:
            raise ValidationError("El producto no pertenece a la venta indicada")
        disponible = vendido[id_producto] - comprometido.get(id_producto, Decimal("0"))
        if cantidad > disponible:
            raise ValidationError(
                f"Solo se pueden devolver {disponible} unidad(es) del producto {id_producto}"
            )

    devolucion = Devolucion(
        id_venta=data.id_venta,
        id_usuario_solicita=solicitante.id_usuario,
        motivo=data.motivo,
        monto=0,
        metodo_reembolso=data.metodo_reembolso,
        estado=EstadoDevolucion.pendiente_aprobacion,
        id_sucursal=venta.id_sucursal,
    )
    db.add(devolucion)
    await db.flush()

    monto_total = Decimal("0")
    for id_producto, cantidad in pedido.items():
        linea = lineas_venta[id_producto]
        producto = await db.get(Producto, id_producto)
        if producto is None:
            raise NotFoundError("Producto", id_producto)

        precio = _d(linea.precio_unitario)
        descuento = _d(linea.descuento)
        iva_porcentaje = _d(linea.iva_porcentaje)
        base = (precio - descuento) * cantidad
        monto_linea = base + base * iva_porcentaje / Decimal("100")
        monto_linea = monto_linea.quantize(CENTAVO, ROUND_HALF_UP)
        monto_total += monto_linea

        db.add(
            DevolucionDetalle(
                id_devolucion=devolucion.id_devolucion,
                id_producto=id_producto,
                cantidad=float(cantidad),
                precio_unitario=float(precio),
                iva_porcentaje=float(iva_porcentaje),
                subtotal=float(monto_linea),
            )
        )

    devolucion.monto = float(monto_total.quantize(CENTAVO, ROUND_HALF_UP))
    await db.flush()

    if solicitante.rol == RolEnum.administrador:
        return await aprobar_devolucion(db, devolucion.id_devolucion, solicitante)

    limite = Decimal(await _leer_config(db, "devoluciones.max_por_turno_cajero", "50000"))
    acumulado = await _acumulado_turno_cajero(db, solicitante.id_usuario)
    if monto_total <= limite and acumulado + monto_total <= limite:
        return await aprobar_devolucion(db, devolucion.id_devolucion, solicitante)
    return devolucion


async def aprobar_devolucion(db: AsyncSession, id_devolucion: int, admin) -> Devolucion:
    if admin.rol != RolEnum.administrador:
        raise AuthorizationError("Solo el administrador puede aprobar devoluciones")

    result = await db.execute(
        select(Devolucion)
        .where(Devolucion.id_devolucion == id_devolucion)
        .options(selectinload(Devolucion.detalles))
    )
    devolucion = result.scalar_one_or_none()
    if devolucion is None:
        raise NotFoundError("Devolucion", id_devolucion)
    if devolucion.estado == EstadoDevolucion.aprobada:
        raise ConflictError("La devolución ya fue aprobada")
    if devolucion.estado == EstadoDevolucion.rechazada:
        raise ConflictError("La devolución fue rechazada")

    venta = await db.get(Venta, devolucion.id_venta)
    if venta is None:
        raise NotFoundError("Venta", devolucion.id_venta)

    devolucion.estado = EstadoDevolucion.aprobada
    devolucion.id_usuario_aprueba = admin.id_usuario

    monto_dev = _d(devolucion.monto)
    for det in devolucion.detalles:
        producto = await db.get(Producto, det.id_producto)
        if producto is None:
            continue
        producto.stock_actual = float(_d(producto.stock_actual) + _d(det.cantidad))
        db.add(
            MovimientoStock(
                id_producto=det.id_producto,
                tipo="devolucion",
                cantidad=float(_d(det.cantidad)),
                costo_unitario=producto.costo_compra,
                id_referencia=devolucion.id_devolucion,
                tabla_referencia="devoluciones",
                id_usuario=admin.id_usuario,
                id_sucursal=producto.id_sucursal,
                observacion=f"Devolución de la venta {venta.id_venta}",
            )
        )

    venta.monto_devuelto = float(_d(venta.monto_devuelto) + monto_dev)

    if venta.es_fiado:
        # En fiado la devolución descuenta deuda, no entrega efectivo.
        saldo_restante = _d(venta.total) - _d(venta.monto_abonado) - _d(venta.monto_devuelto)
        venta.estado = EstadoVenta.pagada if saldo_restante <= 0 else EstadoVenta.pendiente
    elif devolucion.metodo_reembolso == "efectivo":
        await _salida_efectivo(db, venta, monto_dev, admin)
    elif devolucion.metodo_reembolso == "nota_credito":
        await generar_nota_credito(db, venta, devolucion, admin.id_usuario)

    await registrar_auditoria(
        db,
        "devolucion.aprobada",
        f"Devolución #{devolucion.id_devolucion} por ${monto_dev:.0f} de la venta {venta.consecutivo}",
        id_usuario=admin.id_usuario,
        id_sucursal=venta.id_sucursal,
        datos={
            "id_devolucion": devolucion.id_devolucion,
            "metodo_reembolso": devolucion.metodo_reembolso,
            "monto": float(monto_dev),
            "reingresa_stock": True,
        },
    )
    return devolucion


async def _salida_efectivo(db: AsyncSession, venta: Venta, monto: Decimal, aprobador) -> None:
    """El reembolso en efectivo sale de una caja abierta y se acumula aparte (RN-03)."""
    sesion: SesionCaja | None = None
    if venta.id_sesion_caja:
        sesion_venta = await db.get(SesionCaja, venta.id_sesion_caja)
        if sesion_venta is not None and sesion_venta.estado == EstadoCaja.abierta:
            sesion = sesion_venta

    if sesion is None:
        sesion = (
            await db.execute(
                select(SesionCaja).where(
                    SesionCaja.id_usuario_creador == aprobador.id_usuario,
                    SesionCaja.estado == EstadoCaja.abierta,
                )
            )
        ).scalar_one_or_none()

    if sesion is None:
        raise ValidationError(
            "Para reembolsar en efectivo debe haber una caja abierta; "
            "use transferencia o nota de crédito"
        )

    sesion.devoluciones_efectivo = float(_d(sesion.devoluciones_efectivo) + monto)


async def generar_nota_credito(
    db: AsyncSession, venta: Venta, devolucion: Devolucion, id_usuario: int
) -> Comprobante:
    numero_serie = "NC"
    numero_sec = 1
    result = await db.execute(
        select(NumeracionDIAN).where(
            NumeracionDIAN.id_sucursal == venta.id_sucursal,
            NumeracionDIAN.activa.is_(True),
        )
    )
    num = result.scalars().first()
    if num and num.siguiente_numero <= num.rango_fin:
        numero_serie = num.prefijo or "NC"
        numero_sec = num.siguiente_numero
        num.siguiente_numero += 1

    comprobante = Comprobante(
        id_venta=venta.id_venta,
        tipo=TipoComprobante.nota_credito,
        numero_serie=numero_serie,
        numero_secuencial=numero_sec,
        estado=EstadoComprobante.pendiente,
        id_sucursal=venta.id_sucursal,
        respuesta_pac=f"Nota crédito por devolución {devolucion.id_devolucion} - venta {venta.id_venta}",
    )
    db.add(comprobante)
    await db.flush()
    return comprobante


async def rechazar_devolucion(db: AsyncSession, id_devolucion: int, admin) -> Devolucion:
    if admin.rol != RolEnum.administrador:
        raise AuthorizationError("Solo el administrador puede rechazar devoluciones")
    devolucion = await db.get(Devolucion, id_devolucion)
    if devolucion is None:
        raise NotFoundError("Devolucion", id_devolucion)
    if devolucion.estado == EstadoDevolucion.aprobada:
        raise ConflictError("La devolución ya fue aprobada")
    devolucion.estado = EstadoDevolucion.rechazada
    return devolucion
