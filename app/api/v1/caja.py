from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import CashDrawerError, NotFoundError
from app.models.caja import CajaArqueo, SesionCaja
from app.models.configuracion import Configuracion
from app.models.turno import EstadoTurno, TurnoCalendario
from app.models.usuario import Usuario
from app.schemas.caja import CajaDoblePanel, CajaArqueoItem, CierreCaja, SesionCajaCreate, SesionCajaRead
from app.schemas.common import MessageResponse
from app.services.auth_service import get_current_user
from app.services.caja_service import abrir_sesion_caja, cerrar_sesion_caja

router = APIRouter()


@router.get("/abierta", response_model=None)
async def get_sesion_abierta(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> SesionCajaRead | None:
    result = await db.execute(
        select(SesionCaja).where(
            SesionCaja.id_usuario_creador == current_user.id_usuario,
            SesionCaja.estado == "abierta",
        )
    )
    sesion = result.scalar_one_or_none()
    if sesion:
        return SesionCajaRead.model_validate(sesion)
    return None


@router.post("/abrir", response_model=None, status_code=201)
async def abrir_caja(
    body: SesionCajaCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> SesionCajaRead:
    config_turno = await db.execute(
        select(Configuracion).where(Configuracion.clave == "caja.requiere_turno_activo")
    )
    requiere_turno = (config_turno.scalar_one_or_none() or None)
    if requiere_turno is not None and requiere_turno.valor == "1":
        turno_result = await db.execute(
            select(TurnoCalendario).where(
                TurnoCalendario.id_usuario_titular == current_user.id_usuario,
                TurnoCalendario.estado_turno == EstadoTurno.activo,
            )
        )
        if not turno_result.scalar_one_or_none():
            raise CashDrawerError("No tiene un turno activo para abrir caja")

    existing = await db.execute(
        select(SesionCaja).where(
            SesionCaja.id_usuario_creador == current_user.id_usuario,
            SesionCaja.estado == "abierta",
        )
    )
    if existing.scalar_one_or_none():
        raise CashDrawerError("Ya tiene una sesión de caja abierta")

    sesion = await abrir_sesion_caja(db, current_user.id_usuario, body)
    return SesionCajaRead.model_validate(sesion)


@router.get("/panel", response_model=None)
async def get_panel_caja(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> CajaDoblePanel:
    result = await db.execute(
        select(SesionCaja).where(
            SesionCaja.id_usuario_creador == current_user.id_usuario,
            SesionCaja.estado == "abierta",
        )
    )
    sesion = result.scalar_one_or_none()
    if not sesion:
        raise CashDrawerError("No tiene caja abierta")

    return CajaDoblePanel(
        ventas_brutas_turno=sesion.ventas_efectivo + sesion.ventas_digitales + sesion.total_tarjeta,
        efectivo_real_esperado=sesion.base_inicial + sesion.ventas_efectivo,
        base_inicial=sesion.base_inicial,
        ventas_efectivo_acumulado=sesion.ventas_efectivo,
    )


@router.post("/cerrar", response_model=None)
async def cerrar_caja(
    body: CierreCaja,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> SesionCajaRead:
    result = await db.execute(
        select(SesionCaja).where(
            SesionCaja.id_usuario_creador == current_user.id_usuario,
            SesionCaja.estado == "abierta",
        )
    )
    sesion = result.scalar_one_or_none()
    if not sesion:
        raise CashDrawerError("No tiene caja abierta")

    sesion = await cerrar_sesion_caja(db, sesion, body)
    return SesionCajaRead.model_validate(sesion)
