from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.exceptions import NotFoundError, ValidationError
from app.models.compra import Compra, Proveedor
from app.models.producto import Producto
from app.models.usuario import Usuario
from app.schemas.common import PaginatedResponse
from app.schemas.compra import CompraCreate, CompraRead, ProveedorCreate, ProveedorRead
from app.services.auth_service import get_current_user
from app.services.compra_service import registrar_compra

router = APIRouter()


def _sanitize(texto: str) -> str:
    return texto.replace("%", "").replace("_", "")


@router.get("/proveedores", response_model=None)
async def list_proveedores(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
    q: str | None = None,
) -> list[ProveedorRead]:
    query = select(Proveedor)
    if q:
        term = f"%{_sanitize(q)}%"
        query = query.where(or_(Proveedor.nombre.ilike(term), Proveedor.nit.ilike(term)))
    result = await db.execute(query.order_by(Proveedor.nombre))
    return [ProveedorRead.model_validate(p) for p in result.scalars().all()]


@router.post("/proveedores", response_model=None, status_code=201)
async def create_proveedor(
    body: ProveedorCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
) -> ProveedorRead:
    proveedor = Proveedor(
        nombre=body.nombre,
        nit=body.nit,
        telefono=body.telefono,
        email=body.email,
        direccion=body.direccion,
    )
    db.add(proveedor)
    await db.flush()
    return ProveedorRead.model_validate(proveedor)


@router.get("/reponer", response_model=None)
async def sugerir_reposicion(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
    id_sucursal: int | None = None,
) -> list[Producto]:
    query = select(Producto).where(Producto.stock_actual <= Producto.stock_minimo_alerta, Producto.activo.is_(True))
    if id_sucursal:
        query = query.where(Producto.id_sucursal == id_sucursal)
    result = await db.execute(query.order_by(Producto.stock_actual))
    return result.scalars().all()


@router.get("/", response_model=None)
async def list_compras(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[CompraRead]:
    count_query = select(func.count()).select_from(Compra)
    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Compra)
        .options(selectinload(Compra.detalles))
        .offset(offset)
        .limit(page_size)
        .order_by(Compra.fecha_compra.desc())
    )
    items = result.scalars().unique().all()
    return PaginatedResponse(
        items=[CompraRead.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.post("/", response_model=None, status_code=201)
async def create_compra(
    body: CompraCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> CompraRead:
    for det in body.detalles:
        if det.cantidad <= 0 or det.costo_unitario <= 0:
            raise ValidationError("Cantidad y costo deben ser mayores a cero")
    compra = await registrar_compra(db, body, current_user.id_usuario)
    return CompraRead.model_validate(compra)