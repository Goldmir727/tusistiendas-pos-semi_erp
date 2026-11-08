from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.exceptions import NotFoundError
from app.models.pago import PagoSueldo, PagoTurnoDetalle
from app.models.turno import EstadoTurno, TurnoCalendario
from app.models.usuario import Usuario
from app.schemas.common import PaginatedResponse, MessageResponse
from app.schemas.pago import PagoCreate, PagoRead
from app.services.auth_service import get_current_user, get_current_admin, get_current_empleado
from app.services.pago_service import procesar_pago_sueldo, marcar_pago_recibido

router = APIRouter()


@router.get("/turnos-pendientes")
async def get_turnos_pendientes_pago(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
    id_usuario: int | None = None,
) -> list[dict]:
    from app.models.usuario import RolEnum
    from app.services.turno_service import beneficiario_turno

    query = select(TurnoCalendario).where(
        TurnoCalendario.estado_turno == EstadoTurno.finalizado,
    )

    if current_user.rol == RolEnum.administrador:
        if id_usuario is not None:
            query = query.where(
                (TurnoCalendario.id_usuario_titular == id_usuario)
                | (TurnoCalendario.id_usuario_reemplazo == id_usuario)
            )
    else:
        query = query.where(
            (TurnoCalendario.id_usuario_titular == current_user.id_usuario)
            | (TurnoCalendario.id_usuario_reemplazo == current_user.id_usuario)
        )

    query = query.order_by(TurnoCalendario.fecha)
    result = await db.execute(query)
    turnos = result.scalars().all()

    salida = []
    for t in turnos:
        if beneficiario_turno(t) != (id_usuario if (current_user.rol == RolEnum.administrador and id_usuario) else current_user.id_usuario):
            continue
        # Excluir turnos ya pagados (defensivo)
        from sqlalchemy import exists, select as _select
        from app.models.pago import PagoTurnoDetalle

        ya_pagado = await db.execute(
            _select(PagoTurnoDetalle).where(PagoTurnoDetalle.id_turno == t.id_turno)
        )
        if ya_pagado.scalar_one_or_none() is not None:
            continue
        salida.append(
            {
                "id_turno": t.id_turno,
                "id_usuario": beneficiario_turno(t),
                "fecha": t.fecha.isoformat(),
                "hora_inicio": t.hora_inicio.isoformat(),
                "hora_fin": t.hora_fin.isoformat(),
                "valor_total_turno": float(t.valor_total_turno),
            }
        )
    return salida


@router.post("/", response_model=None, status_code=201)
async def create_pago(
    body: PagoCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[Usuario, Depends(get_current_admin)],
) -> PagoRead:
    pago = await procesar_pago_sueldo(db, body, current_admin.id_usuario)
    await db.commit()
    result = await db.execute(
        select(PagoSueldo)
        .options(selectinload(PagoSueldo.detalles))
        .where(PagoSueldo.id_pago == pago.id_pago)
    )
    pago = result.scalar_one()
    return PagoRead.model_validate(pago)


@router.get("/", response_model=None)
async def list_pagos(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_admin)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[PagoRead]:
    query = select(PagoSueldo).options(selectinload(PagoSueldo.detalles))
    count_query = select(func.count()).select_from(PagoSueldo)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size).order_by(PagoSueldo.fecha_pago.desc()))
    items = result.scalars().unique().all()

    return PaginatedResponse(
        items=[PagoRead.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/mis-pagos", response_model=None)
async def list_mis_pagos(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> list[PagoRead]:
    result = await db.execute(
        select(PagoSueldo)
        .options(selectinload(PagoSueldo.detalles))
        .where(PagoSueldo.id_usuario_receptor == current_user.id_usuario)
        .order_by(PagoSueldo.fecha_pago.desc())
    )
    return [PagoRead.model_validate(p) for p in result.scalars().unique().all()]


@router.patch("/{id_pago}/marcar-recibido", response_model=None)
async def marcar_pago_recibido_endpoint(
    id_pago: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> PagoRead:
    es_admin = current_user.rol.value == "administrador"
    pago = await marcar_pago_recibido(db, id_pago, current_user.id_usuario, es_admin)
    await db.commit()
    result = await db.execute(
        select(PagoSueldo)
        .options(selectinload(PagoSueldo.detalles))
        .where(PagoSueldo.id_pago == pago.id_pago)
    )
    pago = result.scalar_one()
    return PagoRead.model_validate(pago)
