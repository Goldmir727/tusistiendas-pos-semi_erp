from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AuthorizationError, NotFoundError
from app.models.usuario import Usuario
from app.schemas.common import PaginatedResponse
from app.schemas.usuario import UsuarioCreate, UsuarioRead, UsuarioUpdate
from app.services.auth_service import (
    create_usuario,
    get_current_user,
    get_current_admin,
    get_current_cajero,
)

router = APIRouter()


@router.get("/me", response_model=None)
async def get_me(
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> UsuarioRead:
    return UsuarioRead.model_validate(current_user)


@router.get("/", response_model=None)
async def list_usuarios(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    rol: str | None = None,
    id_sucursal: int | None = None,
) -> PaginatedResponse[UsuarioRead]:
    from app.models.usuario import RolEnum

    if current_user.rol != RolEnum.administrador:
        if not (current_user.rol == RolEnum.cajero and rol == "empleado"):
            raise AuthorizationError("No tiene permisos para listar usuarios")
    query = select(Usuario)
    count_query = select(func.count()).select_from(Usuario)

    if rol:
        query = query.where(Usuario.rol == rol)
        count_query = count_query.where(Usuario.rol == rol)
    if id_sucursal:
        query = query.where(Usuario.id_sucursal == id_sucursal)
        count_query = count_query.where(Usuario.id_sucursal == id_sucursal)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size).order_by(Usuario.id_usuario))
    items = result.scalars().all()

    return PaginatedResponse(
        items=[UsuarioRead.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.post("/", response_model=None, status_code=201)
async def create_usuario_endpoint(
    body: UsuarioCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[object, Depends(get_current_admin)],
) -> UsuarioRead:
    user = await create_usuario(db, body)
    return UsuarioRead.model_validate(user)


@router.get("/{user_id}", response_model=None)
async def get_usuario(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[object, Depends(get_current_user)],
) -> UsuarioRead:
    result = await db.execute(select(Usuario).where(Usuario.id_usuario == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("Usuario", user_id)
    return UsuarioRead.model_validate(user)


@router.patch("/{user_id}", response_model=None)
async def update_usuario(
    user_id: int,
    body: UsuarioUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[object, Depends(get_current_admin)],
) -> UsuarioRead:
    result = await db.execute(select(Usuario).where(Usuario.id_usuario == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("Usuario", user_id)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    return UsuarioRead.model_validate(user)
