from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import NotFoundError
from app.models.caja import SesionCaja
from app.models.usuario import Usuario
from app.schemas.venta_temporal import (
    VentaTemporalCreate,
    VentaTemporalRead,
    VentaTemporalUpdate,
)
from app.services.auth_service import get_current_cajero
from app.services.venta_temporal_service import (
    crear_temporal,
    eliminar_temporal,
    listar_temporales,
    actualizar_temporal,
)

router = APIRouter()


@router.get("/", response_model=None)
async def list_temporales(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_cajero)],
    id_sesion_caja: int = Query(..., ge=1),
) -> list[VentaTemporalRead]:
    items = await listar_temporales(db, id_sesion_caja)
    return [VentaTemporalRead.model_validate(i) for i in items]


@router.post("/", response_model=None, status_code=201)
async def create_temporal(
    body: VentaTemporalCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_cajero)],
) -> VentaTemporalRead:
    item = await crear_temporal(
        db,
        body.id_sesion_caja,
        current_user.id_usuario,
        body.nombre,
        body.items,
        body.descripcion,
        body.id_cliente,
        body.cliente_nombre,
    )
    return VentaTemporalRead.model_validate(item)


@router.patch("/{id_venta_temporal}", response_model=None)
async def update_temporal(
    id_venta_temporal: str,
    body: VentaTemporalUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_cajero)],
) -> VentaTemporalRead:
    from app.models.venta_temporal import VentaTemporal

    result = await db.execute(
        select(VentaTemporal).where(VentaTemporal.id_venta_temporal == id_venta_temporal)
    )
    temporal = result.scalar_one_or_none()
    if temporal is None:
        raise NotFoundError("VentaTemporal", id_venta_temporal)

    sesion = await db.get(SesionCaja, temporal.id_sesion_caja)
    puede_editar = (
        sesion is not None
        and (
            current_user.id_usuario == sesion.id_usuario_creador
            or current_user.id_usuario == sesion.id_usuario_abre_caja
        )
    )
    es_admin = current_user.rol.value == "administrador"

    item = await actualizar_temporal(
        db,
        id_venta_temporal,
        current_user.id_usuario,
        es_admin,
        puede_editar,
        body.nombre,
        body.items,
        body.descripcion,
    )
    return VentaTemporalRead.model_validate(item)


@router.delete("/{id_venta_temporal}", response_model=None, status_code=204)
async def delete_temporal(
    id_venta_temporal: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_cajero)],
) -> None:
    await eliminar_temporal(db, id_venta_temporal)