from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.models.caja import SesionCaja
from app.models.comprobante import Comprobante, EstadoComprobante, NumeracionDIAN, TipoComprobante
from app.models.configuracion import Configuracion
from app.models.devolucion import Devolucion, DevolucionDetalle, EstadoDevolucion
from app.models.producto import MovimientoStock, Producto
from app.models.usuario import RolEnum
from app.models.venta import EstadoVenta, MetodoPago, Venta, VentaPago
from app.schemas.devolucion import DevolucionCreate


async def _leer_config(db: AsyncSession, clave: str, default: str) -> str:
    result = await db.execute(select(Configuracion).where(Configuracion.clave == clave))
    config = result.scalar_one_or_none()
    return config.valor if config else default


async def _acumulado_hoy_cajero(db: AsyncSession, id_usuario: int) -> Decimal:
    inicio = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.coalesce(func.sum(Devolucion.monto), 0)).where(
            Devolucion.id_usuario_solicita == id_usuario,
            Devolucion.fecha >= inicio,
            Devolucion.estado == EstadoDevolucion.aprobada,
        )
    )
    return Decimal(str(result.scalar() or 0))


async def crear_devolucion(
    db: AsyncSession,
    data: DevolucionCreate,
    solicitante,
) -> Devolucion:
    result_venta = await db.execute(select(Venta).where(Venta.id_venta == data.id_venta))
    venta = result_venta.scalar_one_or_none()
    if not venta:
        raise NotFoundError("Venta", data.id_venta)
    if venta.estado == EstadoVenta.anulada:
        raise ConflictError("La venta ya está anulada")

    devolucion = Devolucion(
        id_venta=data.id_venta,
        id_usuario_solicita=solicitante.id_usuario,
        motivo=data.motivo,
        monto=0,
        estado=EstadoDevolucion.pendiente_aprobacion,
        id_sucursal=venta.id_sucursal,
    )
    db.add(devolucion)
    await db.flush()

    monto_total = Decimal("0")
    for det in data.detalles:
        producto = await db.get(Producto, det.id_producto)
        if not producto:
            raise NotFoundError("Producto", det.id_producto)

        subtotal = det.precio_unitario * det.cantidad
        iva_linea = subtotal * (det.iva_porcentaje / Decimal("100"))
        monto_linea = subtotal + iva_linea
        monto_total += monto_linea

        detalle = DevolucionDetalle(
            id_devolucion=devolucion.id_devolucion,
            id_producto=det.id_producto,
            cantidad=det.cantidad,
            precio_unitario=det.precio_unitario,
            iva_porcentaje=det.iva_porcentaje,
            subtotal=float(monto_linea),
        )
        db.add(detalle)

    devolucion.monto = float(monto_total)

    if solicitante.rol == RolEnum.administrador:
        await aprobar_devolucion(db, devolucion.id_devolucion, solicitante)
        return devolucion

    limite = Decimal(await _leer_config(db, "devoluciones.max_por_turno_cajero", "50000"))
    acumulado = await _acumulado_hoy_cajero(db, solicitante.id_usuario)
    if monto_total <= limite and acumulado + monto_total <= limite:
        await aprobar_devolucion(db, devolucion.id_devolucion, solicitante)
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
    if not devolucion:
        raise NotFoundError("Devolucion", id_devolucion)
    if devolucion.estado == EstadoDevolucion.aprobada:
        raise ConflictError("La devolución ya fue aprobada")
    if devolucion.estado == EstadoDevolucion.rechazada:
        raise ConflictError("La devolución fue rechazada")

    venta = await db.get(Venta, devolucion.id_venta)
    if not venta:
        raise NotFoundError("Venta", devolucion.id_venta)

    devolucion.estado = EstadoDevolucion.aprobada
    devolucion.id_usuario_aprueba = admin.id_usuario

    monto_dev = Decimal(str(devolucion.monto))
    for det in devolucion.detalles:
        producto = await db.get(Producto, det.id_producto)
        if producto:
            producto.stock_actual = float(Decimal(str(producto.stock_actual)) + det.cantidad)
            mov = MovimientoStock(
                id_producto=det.id_producto,
                tipo="devolucion",
                cantidad=det.cantidad,
                costo_unitario=producto.costo_compra,
                id_referencia=devolucion.id_devolucion,
                tabla_referencia="devoluciones",
                id_usuario=admin.id_usuario,
                id_sucursal=producto.id_sucursal,
                observacion=f"Devolucion venta {venta.id_venta}",
            )
            db.add(mov)

    venta.monto_devuelto = float(Decimal(str(venta.monto_devuelto)) + monto_dev)

    if venta.es_fiado:
        saldo_restante = Decimal(str(venta.total)) - Decimal(str(venta.monto_abonado)) - monto_dev
        venta.estado = EstadoVenta.pagada if saldo_restante <= 0 else EstadoVenta.pendiente
    else:
        await _revertir_caja(db, venta, monto_dev)

    await generar_nota_credito(db, venta, devolucion, admin.id_usuario)
    return devolucion


async def _revertir_caja(db: AsyncSession, venta: Venta, monto: Decimal) -> None:
    if not venta.id_sesion_caja:
        return
    sesion = await db.get(SesionCaja, venta.id_sesion_caja)
    if not sesion:
        return
    sesion.ventas_efectivo = float(Decimal(str(sesion.ventas_efectivo)) - monto)


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
        respuesta_pac=f"Reembolso {devolucion.monto} - venta {venta.id_venta}",
    )
    db.add(comprobante)
    await db.flush()
    return comprobante


async def rechazar_devolucion(db: AsyncSession, id_devolucion: int, admin) -> Devolucion:
    if admin.rol != RolEnum.administrador:
        raise AuthorizationError("Solo el administrador puede rechazar devoluciones")
    devolucion = await db.get(Devolucion, id_devolucion)
    if not devolucion:
        raise NotFoundError("Devolucion", id_devolucion)
    if devolucion.estado == EstadoDevolucion.aprobada:
        raise ConflictError("La devolución ya fue aprobada")
    devolucion.estado = EstadoDevolucion.rechazada
    return devolucion