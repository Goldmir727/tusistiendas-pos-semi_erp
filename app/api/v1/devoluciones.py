from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.exceptions import NotFoundError
from app.models.devolucion import Devolucion, DevolucionDetalle, EstadoDevolucion
from app.models.usuario import Usuario
from app.schemas.common import MessageResponse
from app.schemas.devolucion import DevolucionCreate, DevolucionRead
from app.services.auth_service import get_current_admin, get_current_user
from app.services.devolucion_service import aprobar_devolucion, crear_devolucion, rechazar_devolucion

router = APIRouter()


@router.get("/", response_model=None)
async def list_devoluciones(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
) -> list[DevolucionRead]:
    result = await db.execute(
        select(Devolucion)
        .options(selectinload(Devolucion.detalles))
        .order_by(Devolucion.fecha.desc())
    )
    devoluciones = result.scalars().unique().all()
    items = []
    for d in devoluciones:
        data = DevolucionRead.model_validate(d)
        data.detalles = [
            {
                "id_producto": de.id_producto,
                "cantidad": float(de.cantidad),
                "precio_unitario": float(de.precio_unitario),
            }
            for de in d.detalles
        ]
        items.append(data)
    return items


@router.post("/", response_model=None, status_code=201)
async def create_devolucion(
    body: DevolucionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> DevolucionRead:
    devolucion = await crear_devolucion(db, body, current_user)
    result = await db.execute(
        select(Devolucion)
        .where(Devolucion.id_devolucion == devolucion.id_devolucion)
        .options(selectinload(Devolucion.detalles))
    )
    devolucion = result.scalar_one()
    data = DevolucionRead.model_validate(devolucion)
    data.detalles = [
        {
            "id_producto": de.id_producto,
            "cantidad": float(de.cantidad),
            "precio_unitario": float(de.precio_unitario),
        }
        for de in devolucion.detalles
    ]
    return data


@router.post("/{id_devolucion}/aprobar", response_model=None)
async def aprobar(
    id_devolucion: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[Usuario, Depends(get_current_admin)],
) -> DevolucionRead:
    devolucion = await aprobar_devolucion(db, id_devolucion, admin)
    return DevolucionRead.model_validate(devolucion)


@router.post("/{id_devolucion}/rechazar", response_model=None)
async def rechazar(
    id_devolucion: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[Usuario, Depends(get_current_admin)],
) -> MessageResponse:
    devolucion = await rechazar_devolucion(db, id_devolucion, admin)
    return MessageResponse(message=f"Devolución {devolucion.id_devolucion} rechazada")