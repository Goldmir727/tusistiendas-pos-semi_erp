from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.caja import SesionCaja
from app.models.usuario import Usuario
from app.models.venta import Venta
from app.services.auth_service import get_current_admin, get_current_user

router = APIRouter()


@router.get("/ventas-por-dia")
async def ventas_por_dia(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_admin)],
    fecha_desde: date = Query(...),
    fecha_hasta: date = Query(...),
    id_sucursal: int | None = None,
) -> list[dict]:
    query = (
        select(
            Venta.fecha_venta,
            func.sum(Venta.total).label("total_ventas"),
            func.count(Venta.id_venta).label("cantidad_ventas"),
        )
        .where(Venta.fecha_venta.between(fecha_desde, fecha_hasta))
        .group_by(Venta.fecha_venta)
        .order_by(Venta.fecha_venta)
    )
    if id_sucursal:
        query = query.where(Venta.id_sucursal == id_sucursal)

    result = await db.execute(query)
    rows = result.all()
    return [
        {"fecha": r.fecha_venta.isoformat(), "total": float(r.total_ventas), "cantidad": r.cantidad_ventas}
        for r in rows
    ]


@router.get("/stock-critico")
async def stock_critico(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
    id_sucursal: int | None = None,
) -> list[dict]:
    from app.models.producto import Producto

    query = select(Producto).where(Producto.stock_actual <= Producto.stock_minimo_alerta)
    if id_sucursal:
        query = query.where(Producto.id_sucursal == id_sucursal)

    result = await db.execute(query)
    productos = result.scalars().all()
    return [
        {
            "id_producto": p.id_producto,
            "nombre": p.nombre_producto,
            "stock_actual": float(p.stock_actual),
            "stock_minimo": float(p.stock_minimo_alerta),
        }
        for p in productos
    ]


@router.get("/descuadres-caja")
async def descuadres_caja(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_admin)],
    id_sucursal: int | None = None,
) -> list[dict]:
    query = select(SesionCaja).where(SesionCaja.descuadre.isnot(None), SesionCaja.descuadre != 0)
    if id_sucursal:
        query = query.where(SesionCaja.id_sucursal == id_sucursal)

    result = await db.execute(query)
    sesiones = result.scalars().all()
    return [
        {
            "id_sesion": s.id_sesion_caja,
            "fecha": s.fecha_apertura.isoformat(),
            "usuario": s.id_usuario_creador,
            "descuadre": float(s.descuadre),
        }
        for s in sesiones
    ]


@router.get("/cartera")
async def cartera_clientes(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_admin)],
) -> list[dict]:
    from app.models.sucursal import Cliente
    from app.services.cliente_service import calcular_saldo

    result = await db.execute(select(Cliente).where(Cliente.activo.is_(True)))
    clientes = result.scalars().all()
    cartera = []
    for c in clientes:
        saldo = float(await calcular_saldo(db, c.id_cliente))
        if saldo > 0:
            cartera.append({"id_cliente": c.id_cliente, "nombre": c.nombre, "telefono": c.telefono, "saldo": saldo})
    cartera.sort(key=lambda x: x["saldo"], reverse=True)
    return cartera


@router.get("/corte")
async def corte_diario(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_admin)],
    fecha: date = Query(...),
    id_sucursal: int | None = None,
) -> list[dict]:
    from datetime import datetime, time

    from app.models.venta import MetodoPago
    from sqlalchemy.orm import selectinload

    desde = datetime.combine(fecha, time.min)
    hasta = datetime.combine(fecha, time.max)

    query = (
        select(Venta)
        .options(selectinload(Venta.pagos))
    ).where(Venta.fecha_venta.between(desde, hasta))
    if id_sucursal:
        query = query.where(Venta.id_sucursal == id_sucursal)
    result = await db.execute(query)
    ventas = result.scalars().unique().all()

    total_efectivo = 0.0
    total_digital = 0.0
    total_tarjeta = 0.0
    total_fiado = 0.0
    for v in ventas:
        if v.es_fiado:
            total_fiado += float(v.total)
            continue
        for p in v.pagos:
            medio = await db.get(MedioPago, p.id_medio_pago)
            if medio:
                if medio.tipo.value == "efectivo":
                    total_efectivo += float(p.monto)
                elif medio.tipo.value == "datafono":
                    total_tarjeta += float(p.monto)
                elif medio.tipo.value == "transferencia":
                    total_digital += float(p.monto)

    from app.models.devolucion import Devolucion
    from app.models.egreso import Egreso

    result_dev = await db.execute(
        select(func.coalesce(func.sum(Devolucion.monto), 0)).where(
            Devolucion.fecha.between(desde, hasta), Devolucion.estado == "aprobada"
        )
    )
    total_devoluciones = float(result_dev.scalar() or 0)

    result_egr = await db.execute(
        select(func.coalesce(func.sum(Egreso.monto), 0)).where(Egreso.fecha.between(desde, hasta))
    )
    total_egresos = float(result_egr.scalar() or 0)

    return [
        {
            "fecha": fecha.isoformat(),
            "ventas_total": sum(float(v.total) for v in ventas),
            "efectivo": total_efectivo,
            "digital": total_digital,
            "tarjeta": total_tarjeta,
            "fiado": total_fiado,
            "devoluciones": total_devoluciones,
            "egresos": total_egresos,
            "cantidad_ventas": len(ventas),
        }
    ]
