from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.devolucion import Devolucion
from app.models.usuario import Usuario
from app.schemas.common import MessageResponse
from app.schemas.devolucion import DevolucionCreate, DevolucionRead
from app.services.auth_service import get_current_admin, get_current_user
from app.services.devolucion_service import aprobar_devolucion, crear_devolucion, rechazar_devolucion

router = APIRouter()


def _a_read(devolucion: Devolucion) -> DevolucionRead:
    return DevolucionRead(
        id_devolucion=devolucion.id_devolucion,
        id_venta=devolucion.id_venta,
        id_usuario_solicita=devolucion.id_usuario_solicita,
        id_usuario_aprueba=devolucion.id_usuario_aprueba,
        motivo=devolucion.motivo,
        monto=devolucion.monto,
        metodo_reembolso=devolucion.metodo_reembolso,
        estado=devolucion.estado,
        fecha=devolucion.fecha,
        detalles=[
            {
                "id_producto": det.id_producto,
                "cantidad": float(det.cantidad),
                "precio_unitario": float(det.precio_unitario),
                "iva_porcentaje": float(det.iva_porcentaje),
                "subtotal": float(det.subtotal),
            }
            for det in devolucion.detalles
        ],
    )


async def _cargar(db: AsyncSession, id_devolucion: int) -> Devolucion:
    result = await db.execute(
        select(Devolucion)
        .options(selectinload(Devolucion.detalles))
        .where(Devolucion.id_devolucion == id_devolucion)
    )
    return result.scalar_one()


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
    return [_a_read(d) for d in result.scalars().unique().all()]


@router.post("/", response_model=None, status_code=201)
async def create_devolucion(
    body: DevolucionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> DevolucionRead:
    devolucion = await crear_devolucion(db, body, current_user)
    return _a_read(await _cargar(db, devolucion.id_devolucion))


@router.post("/{id_devolucion}/aprobar", response_model=None)
async def aprobar(
    id_devolucion: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[Usuario, Depends(get_current_admin)],
) -> DevolucionRead:
    devolucion = await aprobar_devolucion(db, id_devolucion, admin)
    return _a_read(await _cargar(db, devolucion.id_devolucion))


@router.post("/{id_devolucion}/rechazar", response_model=None)
async def rechazar(
    id_devolucion: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[Usuario, Depends(get_current_admin)],
) -> MessageResponse:
    devolucion = await rechazar_devolucion(db, id_devolucion, admin)
    return MessageResponse(message=f"Devolución {devolucion.id_devolucion} rechazada")
