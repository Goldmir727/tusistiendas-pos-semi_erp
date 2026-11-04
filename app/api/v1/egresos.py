from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import CashDrawerError
from app.models.caja import SesionCaja
from app.models.egreso import Egreso
from app.models.usuario import Usuario
from app.schemas.egreso import EgresoCreate, EgresoRead
from app.services.auth_service import get_current_user

router = APIRouter()


@router.get("/", response_model=None)
async def list_egresos(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
    id_sesion_caja: int | None = None,
) -> list[EgresoRead]:
    query = select(Egreso).order_by(Egreso.fecha.desc())
    if id_sesion_caja:
        query = query.where(Egreso.id_sesion_caja == id_sesion_caja)
    result = await db.execute(query)
    return [EgresoRead.model_validate(e) for e in result.scalars().all()]


@router.post("/", response_model=None, status_code=201)
async def create_egreso(
    body: EgresoCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> EgresoRead:
    sesion = await db.get(SesionCaja, body.id_sesion_caja)
    if not sesion or sesion.estado.value != "abierta":
        raise CashDrawerError("No hay sesión de caja abierta para registrar el egreso")
    if body.monto <= 0:
        raise CashDrawerError("El monto del egreso debe ser mayor a cero")

    egreso = Egreso(
        id_sesion_caja=body.id_sesion_caja,
        id_usuario=current_user.id_usuario,
        categoria=body.categoria,
        descripcion=body.descripcion,
        monto=body.monto,
        id_sucursal=body.id_sucursal,
    )
    db.add(egreso)
    await db.flush()
    return EgresoRead.model_validate(egreso)