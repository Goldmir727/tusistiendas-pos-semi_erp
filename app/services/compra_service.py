from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.compra import Compra, CompraDetalle, Proveedor
from app.models.producto import MovimientoStock, Producto
from app.schemas.compra import CompraCreate


async def registrar_compra(
    db: AsyncSession,
    data: CompraCreate,
    id_usuario: int,
) -> Compra:
    proveedor = await db.get(Proveedor, data.id_proveedor)
    if not proveedor:
        raise NotFoundError("Proveedor", data.id_proveedor)

    compra = Compra(
        id_proveedor=data.id_proveedor,
        id_usuario=id_usuario,
        id_sucursal=data.id_sucursal,
        observacion=data.observacion,
    )
    db.add(compra)
    await db.flush()

    total = Decimal("0")
    for det in data.detalles:
        producto = await db.get(Producto, det.id_producto)
        if not producto:
            raise NotFoundError("Producto", det.id_producto)

        subtotal = det.cantidad * det.costo_unitario
        total += subtotal

        detalle = CompraDetalle(
            id_compra=compra.id_compra,
            id_producto=det.id_producto,
            cantidad=det.cantidad,
            costo_unitario=det.costo_unitario,
            subtotal=float(subtotal),
        )
        db.add(detalle)

        stock_actual = Decimal(str(producto.stock_actual))
        costo_actual = Decimal(str(producto.costo_compra))
        nueva_cantidad = stock_actual + det.cantidad
        nuevo_costo = Decimal("0")
        if nueva_cantidad > 0:
            nuevo_costo = (stock_actual * costo_actual + subtotal) / nueva_cantidad

        producto.stock_actual = float(nueva_cantidad)
        producto.costo_compra = float(nuevo_costo)

        mov = MovimientoStock(
            id_producto=det.id_producto,
            tipo="entrada",
            cantidad=det.cantidad,
            costo_unitario=det.costo_unitario,
            id_referencia=compra.id_compra,
            tabla_referencia="compras",
            id_usuario=id_usuario,
            id_sucursal=producto.id_sucursal,
            observacion=f"Compra a proveedor {proveedor.nombre}",
        )
        db.add(mov)

    compra.total = float(total)
    return compra