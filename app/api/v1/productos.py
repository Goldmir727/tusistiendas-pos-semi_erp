from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.exceptions import NotFoundError, StockInsufficientError
from app.models.configuracion import Configuracion
from app.models.producto import CodigoBarras, MovimientoStock, Producto
from app.models.usuario import Usuario
from app.schemas.common import PaginatedResponse
from app.schemas.producto import (
    CodigoBarrasCreate,
    MovimientoStockCreate,
    ProductoCreate,
    ProductoRead,
    ProductoUpdate,
)
from app.services.auth_service import get_current_user, get_current_admin

router = APIRouter()


def _sanitize_search(value: str) -> str:
    return value.replace("%", "").replace("_", "").strip()


async def _get_config_value(db: AsyncSession, clave: str, default: str = "") -> str:
    result = await db.execute(select(Configuracion).where(Configuracion.clave == clave))
    config = result.scalar_one_or_none()
    return config.valor if config else default


@router.get("/", response_model=None)
async def list_productos(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    buscar: str | None = None,
    id_sucursal: int | None = None,
    stock_bajo: bool = False,
) -> PaginatedResponse[ProductoRead]:
    query = select(Producto).options(selectinload(Producto.codigos_barras))
    count_query = select(func.count()).select_from(Producto)

    if buscar:
        safe_search = _sanitize_search(buscar)
        if safe_search:
            query = query.where(Producto.nombre_producto.ilike(f"%{safe_search}%"))
            count_query = count_query.where(Producto.nombre_producto.ilike(f"%{safe_search}%"))
    if id_sucursal:
        query = query.where(Producto.id_sucursal == id_sucursal)
        count_query = count_query.where(Producto.id_sucursal == id_sucursal)
    if stock_bajo:
        query = query.where(Producto.stock_actual <= Producto.stock_minimo_alerta)
        count_query = count_query.where(Producto.stock_actual <= Producto.stock_minimo_alerta)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size).order_by(Producto.nombre_producto))
    items = result.scalars().unique().all()

    return PaginatedResponse(
        items=[ProductoRead.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.post("/", response_model=None, status_code=201)
async def create_producto(
    body: ProductoCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_admin)],
) -> ProductoRead:
    precio_venta = body.precio_venta

    if body.porcentaje_ganancia is not None and body.porcentaje_ganancia > 0:
        precio_venta = float(body.costo_compra) * (1 + float(body.porcentaje_ganancia) / 100)
    else:
        margen_default = await _get_config_value(db, "productos.margen_ganancia_default", "0")
        if margen_default and float(margen_default) > 0:
            precio_venta = float(body.costo_compra) * (1 + float(margen_default) / 100)

    producto = Producto(
        nombre_producto=body.nombre_producto,
        precio_venta=precio_venta,
        costo_compra=body.costo_compra,
        stock_actual=body.stock_actual,
        stock_minimo_alerta=body.stock_minimo_alerta,
        porcentaje_ganancia=body.porcentaje_ganancia,
        iva_porcentaje=body.iva_porcentaje,
        id_sucursal=body.id_sucursal,
    )
    db.add(producto)
    await db.flush()

    for cb in body.codigos_barras:
        barcode = CodigoBarras(id_producto=producto.id_producto, codigo_barras=cb.codigo_barras)
        db.add(barcode)

    await db.flush()
    result = await db.execute(
        select(Producto).options(selectinload(Producto.codigos_barras)).where(Producto.id_producto == producto.id_producto)
    )
    return ProductoRead.model_validate(result.scalar_one())


@router.get("/{producto_id}", response_model=None)
async def get_producto(
    producto_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
) -> ProductoRead:
    result = await db.execute(
        select(Producto).options(selectinload(Producto.codigos_barras)).where(Producto.id_producto == producto_id)
    )
    producto = result.scalar_one_or_none()
    if not producto:
        raise NotFoundError("Producto", producto_id)
    return ProductoRead.model_validate(producto)


@router.get("/buscar/{codigo_barras}", response_model=None)
async def buscar_por_codigo_barras(
    codigo_barras: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
) -> ProductoRead:
    result = await db.execute(
        select(CodigoBarras).where(CodigoBarras.codigo_barras == codigo_barras)
    )
    cb = result.scalar_one_or_none()
    if not cb:
        raise NotFoundError("Codigo de barras", codigo_barras)

    result = await db.execute(
        select(Producto).options(selectinload(Producto.codigos_barras)).where(Producto.id_producto == cb.id_producto)
    )
    return ProductoRead.model_validate(result.scalar_one())


@router.patch("/{producto_id}", response_model=None)
async def update_producto(
    producto_id: int,
    body: ProductoUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_admin)],
) -> ProductoRead:
    result = await db.execute(
        select(Producto).options(selectinload(Producto.codigos_barras)).where(Producto.id_producto == producto_id)
    )
    producto = result.scalar_one_or_none()
    if not producto:
        raise NotFoundError("Producto", producto_id)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(producto, field, value)

    return ProductoRead.model_validate(producto)


@router.post("/{producto_id}/codigos-barras", response_model=None)
async def add_codigo_barras(
    producto_id: int,
    body: CodigoBarrasCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_admin)],
) -> ProductoRead:
    result = await db.execute(
        select(Producto).options(selectinload(Producto.codigos_barras)).where(Producto.id_producto == producto_id)
    )
    producto = result.scalar_one_or_none()
    if not producto:
        raise NotFoundError("Producto", producto_id)

    barcode = CodigoBarras(id_producto=producto_id, codigo_barras=body.codigo_barras)
    db.add(barcode)
    await db.flush()

    result = await db.execute(
        select(Producto).options(selectinload(Producto.codigos_barras)).where(Producto.id_producto == producto_id)
    )
    return ProductoRead.model_validate(result.scalar_one())
