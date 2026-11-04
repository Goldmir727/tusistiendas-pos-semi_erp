from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import CashDrawerError, NotFoundError, ValidationError
from app.models.caja import EstadoCaja, SesionCaja
from app.models.consecutivo import Consecutivo
from app.models.producto import MovimientoStock, Producto
from app.models.venta import (
    MEDIOS_PAGO_VIGENTES,
    EstadoVenta,
    MedioPago,
    MetodoPago,
    Venta,
    VentaDetalle,
    VentaPago,
)
from app.schemas.venta import VentaCreate
from app.services.auditoria_service import registrar_auditoria

CENTAVO = Decimal("0.01")
TOLERANCIA = Decimal("0.01")


def _d(valor: object | None) -> Decimal:
    if valor is None:
        return Decimal("0")
    return Decimal(str(valor))


def calcular_totales(detalles: list[dict]) -> tuple[Decimal, Decimal, Decimal]:
    """Subtotal, impuestos y descuento totales. Función pura, sin base de datos."""
    subtotal = Decimal("0")
    impuestos = Decimal("0")
    descuento = Decimal("0")
    for det in detalles:
        precio = _d(det["precio_unitario"])
        desc = _d(det.get("descuento", 0))
        cantidad = _d(det["cantidad"])
        iva = _d(det.get("iva_porcentaje", 0))
        base = (precio - desc) * cantidad
        subtotal += base
        impuestos += base * iva / Decimal("100")
        descuento += desc * cantidad
    return (
        subtotal.quantize(CENTAVO, ROUND_HALF_UP),
        impuestos.quantize(CENTAVO, ROUND_HALF_UP),
        descuento.quantize(CENTAVO, ROUND_HALF_UP),
    )


async def buscar_por_uuid(db: AsyncSession, uuid: UUID) -> Venta | None:
    result = await db.execute(
        select(Venta)
        .options(selectinload(Venta.detalles), selectinload(Venta.pagos))
        .where(Venta.uuid == uuid)
    )
    return result.scalar_one_or_none()


async def _siguiente_consecutivo(db: AsyncSession, id_sucursal: int) -> int:
    result = await db.execute(
        select(Consecutivo)
        .where(Consecutivo.nombre == "venta", Consecutivo.id_sucursal == id_sucursal)
        .with_for_update()
    )
    consecutivo = result.scalar_one_or_none()
    if consecutivo is None:
        consecutivo = Consecutivo(nombre="venta", id_sucursal=id_sucursal, ultimo=0)
        db.add(consecutivo)
        await db.flush()
        result = await db.execute(
            select(Consecutivo)
            .where(Consecutivo.id_consecutivo == consecutivo.id_consecutivo)
            .with_for_update()
        )
        consecutivo = result.scalar_one()
    consecutivo.ultimo += 1
    return consecutivo.ultimo


async def procesar_venta(
    db: AsyncSession,
    data: VentaCreate,
    id_usuario: int,
    ip: str | None = None,
) -> Venta:
    # Idempotencia: una venta reenviada desde la cola offline no se duplica (RN-08).
    if data.uuid is not None:
        existente = await buscar_por_uuid(db, data.uuid)
        if existente is not None:
            return existente

    sesion = await db.get(SesionCaja, data.id_sesion_caja)
    if sesion is None:
        raise CashDrawerError("La sesión de caja no existe")
    if sesion.estado != EstadoCaja.abierta:
        raise CashDrawerError("La sesión de caja está cerrada")

    preparados: list[dict] = []
    for item in data.detalles:
        producto = await db.get(Producto, item.id_producto)
        if producto is None:
            raise NotFoundError("Producto", item.id_producto)

        cantidad = _d(item.cantidad)
        if cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor a cero")

        precio = _d(item.precio_unitario if item.precio_unitario is not None else producto.precio_venta)
        if precio < 0:
            raise ValidationError("El precio no puede ser negativo")

        descuento = _d(item.descuento)
        if descuento < 0 or descuento > precio:
            raise ValidationError("El descuento no puede ser negativo ni mayor al precio")

        iva = _d(item.iva_porcentaje if item.iva_porcentaje is not None else producto.iva_porcentaje)

        preparados.append(
            {
                "producto": producto,
                "cantidad": cantidad,
                "precio_unitario": precio,
                "descuento": descuento,
                "iva_porcentaje": iva,
            }
        )

    subtotal, impuestos, descuento_total = calcular_totales(preparados)
    total = (subtotal + impuestos).quantize(CENTAVO, ROUND_HALF_UP)

    medios: dict[int, MedioPago] = {}
    if data.pagos:
        result = await db.execute(
            select(MedioPago).where(MedioPago.id_medio_pago.in_([p.id_medio_pago for p in data.pagos]))
        )
        medios = {m.id_medio_pago: m for m in result.scalars().all()}

    total_pagado = Decimal("0")
    es_fiado = False
    for pago in data.pagos:
        medio = medios.get(pago.id_medio_pago)
        if medio is None:
            raise NotFoundError("Medio de pago", pago.id_medio_pago)
        if medio.tipo not in MEDIOS_PAGO_VIGENTES:
            raise ValidationError(f"El medio de pago '{medio.nombre}' ya no está vigente")
        monto = _d(pago.monto)
        if pago.monto_recibido is not None and _d(pago.monto_recibido) < monto:
            raise ValidationError("El monto recibido es menor al monto del pago")
        if medio.tipo == MetodoPago.fiado:
            es_fiado = True
        total_pagado += monto

    if total_pagado <= 0:
        raise ValidationError("La venta debe registrar al menos un pago")
    if abs(total_pagado - total) > TOLERANCIA:
        raise ValidationError("Los pagos no coinciden con el total de la venta")
    if es_fiado and data.id_cliente is None:
        raise ValidationError("La venta a fiado requiere un cliente identificado")

    venta = Venta(
        uuid=data.uuid or uuid4(),
        consecutivo=await _siguiente_consecutivo(db, sesion.id_sucursal),
        id_sesion_caja=sesion.id_sesion_caja,
        id_usuario=id_usuario,
        id_cliente=data.id_cliente,
        id_sucursal=sesion.id_sucursal,
        id_punto_venta=data.id_punto_venta or sesion.id_punto_venta,
        origen=data.origen,
        creado_offline_en=data.creado_offline_en,
        observacion=data.observacion,
        subtotal=float(subtotal),
        impuestos=float(impuestos),
        descuento_total=float(descuento_total),
        total=float(total),
        es_fiado=es_fiado,
        estado=EstadoVenta.pendiente if es_fiado else EstadoVenta.pagada,
    )
    movimientos: list[dict] = []

    for fila in preparados:
        producto = fila["producto"]
        cantidad = fila["cantidad"]
        disponible = _d(producto.stock_actual)
        faltante = cantidad - disponible if cantidad > disponible else Decimal("0")

        # RF-58 / RN-09: nunca stock negativo ni bloqueo de la venta.
        producto.stock_actual = float(max(Decimal("0"), disponible - cantidad))

        observacion_mov = None
        if faltante > 0:
            observacion_mov = (
                f"La venta superó el stock por {faltante} unidad(es); "
                "el stock quedó en 0 y el faltante se asume como error de conteo"
            )

        movimientos.append(
            {
                "id_producto": producto.id_producto,
                "cantidad": cantidad,
                "costo_unitario": producto.costo_compra,
                "observacion": observacion_mov,
            }
        )

        base = (fila["precio_unitario"] - fila["descuento"]) * cantidad
        venta.detalles.append(
            VentaDetalle(
                id_producto=producto.id_producto,
                cantidad=float(cantidad),
                precio_unitario=float(fila["precio_unitario"]),
                descuento=float(fila["descuento"]),
                iva_porcentaje=float(fila["iva_porcentaje"]),
                subtotal=float(base.quantize(CENTAVO, ROUND_HALF_UP)),
            )
        )

    for pago in data.pagos:
        medio = medios[pago.id_medio_pago]
        monto = _d(pago.monto)
        vuelto = Decimal("0")
        if pago.monto_recibido is not None:
            vuelto = _d(pago.monto_recibido) - monto

        venta.pagos.append(
            VentaPago(
                id_medio_pago=medio.id_medio_pago,
                monto=float(monto),
                vuelto=float(vuelto),
                referencia_manual=pago.referencia_manual,
            )
        )

        if medio.tipo == MetodoPago.efectivo:
            sesion.ventas_efectivo = float(_d(sesion.ventas_efectivo) + monto)
        elif medio.tipo == MetodoPago.transferencia:
            sesion.ventas_digitales = float(_d(sesion.ventas_digitales) + monto)
        elif medio.tipo == MetodoPago.datafono:
            sesion.total_tarjeta = float(_d(sesion.total_tarjeta) + monto)

    db.add(venta)
    await db.flush()

    for movimiento in movimientos:
        db.add(
            MovimientoStock(
                id_producto=movimiento["id_producto"],
                tipo="salida",
                cantidad=float(movimiento["cantidad"]),
                costo_unitario=movimiento["costo_unitario"],
                id_referencia=venta.id_venta,
                tabla_referencia="ventas",
                id_usuario=id_usuario,
                id_sucursal=venta.id_sucursal,
                observacion=movimiento["observacion"],
            )
        )

    await registrar_auditoria(
        db,
        "venta.registrada",
        f"Venta {venta.consecutivo} por ${venta.total:.0f}",
        id_usuario=id_usuario,
        id_sucursal=venta.id_sucursal,
        datos={
            "uuid": str(venta.uuid),
            "total": float(venta.total),
            "estado": venta.estado.value,
            "origen": venta.origen,
        },
        ip=ip,
    )

    await db.flush()
    return venta
