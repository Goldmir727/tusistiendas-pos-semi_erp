from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.exceptions import ConflictError, HourLimitExceededError, NotFoundError, ValidationError
from app.models.sucursal import Sucursal
from app.models.turno import (
    EstadoTurno,
    Festivo,
    TarifaTurno,
    TurnoCalendario,
    TurnoPlantilla,
)
from app.models.usuario import RolEnum, Usuario
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.turno import (
    AprobacionReemplazo,
    CalendarioTurnosRead,
    FestivoRead,
    GeneracionTurnosRequest,
    GeneracionTurnosResponse,
    SolicitudReemplazo,
    TarifaSugeridaRead,
    TarifaTurnoCreate,
    TarifaTurnoRead,
    TarifaTurnoUpdate,
    TurnoBulkCreate,
    TurnoBulkDelete,
    TurnoBulkResultado,
    TurnoCreate,
    TurnoPlantillaCreate,
    TurnoPlantillaRead,
    TurnoPlantillaUpdate,
    TurnoRead,
)
from app.services.auth_service import get_current_admin, get_current_turnos_actor as get_current_user
from app.services.turno_service import (
    buscar_solapamiento,
    calcular_horas_semana_empleado,
    cargar_tarifas_activas,
    duracion_horas,
    generar_turnos_masivo,
    hoy_local,
    procesar_solicitud_reemplazo,
    resolver_tarifa,
    resolver_tarifa_en_lista,
    resolver_valor_turno,
)

router = APIRouter()

WEEKLY_HOUR_LIMIT = 44.0


async def _mapa_sucursales(db: AsyncSession) -> dict[int, Sucursal]:
    result = await db.execute(select(Sucursal))
    return {s.id_sucursal: s for s in result.scalars().all()}


def _filtros_rol(
    current: Usuario,
    id_sucursal: int | None,
    id_usuario: int | None,
) -> tuple[list, int | None]:
    from app.models.usuario import RolEnum as _Rol

    filtros = []
    if current.rol == _Rol.empleado:
        filtros.append(
            or_(
                TurnoCalendario.id_usuario_titular == current.id_usuario,
                TurnoCalendario.id_usuario_reemplazo == current.id_usuario,
            )
        )
    elif current.rol == _Rol.cajero:
        sucursal = id_sucursal or current.id_sucursal
        if sucursal is not None:
            filtros.append(TurnoCalendario.id_sucursal == sucursal)
        id_sucursal = sucursal
    else:
        if id_usuario:
            filtros.append(
                or_(
                    TurnoCalendario.id_usuario_titular == id_usuario,
                    TurnoCalendario.id_usuario_reemplazo == id_usuario,
                )
            )
        if id_sucursal:
            filtros.append(TurnoCalendario.id_sucursal == id_sucursal)
    return filtros, id_sucursal


def _turno_read(turno: TurnoCalendario, sucursales: dict[int, Sucursal]) -> TurnoRead:
    data = TurnoRead.model_validate(turno)
    data.nombre_titular = turno.titular.nombre_completo if turno.titular else None
    data.nombre_reemplazo = turno.reemplazo.nombre_completo if turno.reemplazo else None
    sucursal = sucursales.get(turno.id_sucursal)
    data.nombre_sucursal = sucursal.nombre if sucursal else None
    return data


async def _validar_usuario_sucursal(
    db: AsyncSession,
    id_usuario: int,
    id_sucursal: int | None,
) -> tuple[Usuario, int]:
    usuario = (
        await db.execute(select(Usuario).where(Usuario.id_usuario == id_usuario))
    ).scalar_one_or_none()
    if usuario is None:
        raise NotFoundError("Usuario", id_usuario)
    if not usuario.activo:
        raise ValidationError("El empleado está inactivo")

    sucursal_id = id_sucursal or usuario.id_sucursal
    if sucursal_id is None:
        raise ValidationError("Debe indicar la sucursal del turno")

    sucursal = (
        await db.execute(select(Sucursal).where(Sucursal.id_sucursal == sucursal_id))
    ).scalar_one_or_none()
    if sucursal is None:
        raise NotFoundError("Sucursal", sucursal_id)
    return usuario, sucursal_id


async def _crear_turno(
    db: AsyncSession,
    body: TurnoCreate,
    sucursales: dict[int, Sucursal],
) -> TurnoRead:
    usuario, sucursal_id = await _validar_usuario_sucursal(
        db, body.id_usuario_titular, body.id_sucursal
    )
    if duracion_horas(body.hora_inicio, body.hora_fin) <= 0:
        raise ValidationError("El horario del turno no es válido")

    solapado = await buscar_solapamiento(
        db,
        body.id_usuario_titular,
        body.fecha,
        body.hora_inicio,
        body.hora_fin,
    )
    if solapado is not None:
        raise ConflictError(
            "El empleado ya tiene un turno que se cruza: "
            f"{solapado.fecha} {solapado.hora_inicio:%H:%M}-{solapado.hora_fin:%H:%M}"
        )

    valor, _tarifa = await resolver_valor_turno(
        db,
        body.fecha,
        body.hora_inicio,
        body.hora_fin,
        sucursal_id,
        body.valor_total_turno,
        body.usar_tarifa,
    )

    turno = TurnoCalendario(
        id_usuario_titular=usuario.id_usuario,
        fecha=body.fecha,
        hora_inicio=body.hora_inicio,
        hora_fin=body.hora_fin,
        valor_total_turno=valor,
        id_sucursal=sucursal_id,
        estado_turno=EstadoTurno.programado,
    )
    db.add(turno)
    await db.flush()

    data = TurnoRead.model_validate(turno)
    data.nombre_titular = usuario.nombre_completo
    data.nombre_sucursal = sucursales.get(sucursal_id).nombre if sucursal_id in sucursales else None
    return data


def _dias_plantilla(plantilla: TurnoPlantilla) -> list[int]:
    if plantilla.dias_semana:
        return sorted({int(d) for d in plantilla.dias_semana if 0 <= int(d) <= 6})
    if plantilla.dia_semana is not None:
        return [int(plantilla.dia_semana)]
    return []


def _fecha_referencia_para_dia(dia_semana: int) -> date:
    base = hoy_local()
    return base + timedelta(days=(dia_semana - base.weekday()) % 7)


async def _valor_para_plantilla(
    db: AsyncSession,
    dias: list[int],
    hora_inicio,
    hora_fin,
    id_sucursal: int,
    valor_manual: Decimal | None,
    usar_tarifa: bool,
) -> Decimal:
    if not usar_tarifa and valor_manual is not None:
        return Decimal(str(valor_manual))

    fecha_ref = _fecha_referencia_para_dia(dias[0] if dias else 0)
    tarifa = await resolver_tarifa(db, fecha_ref, hora_inicio, hora_fin, id_sucursal)
    if tarifa is not None:
        return Decimal(str(tarifa.valor))
    if valor_manual is not None:
        return Decimal(str(valor_manual))
    return Decimal("0")


def _plantilla_read(
    plantilla: TurnoPlantilla,
    usuarios: dict[int, Usuario],
    sucursales: dict[int, Sucursal],
) -> TurnoPlantillaRead:
    dias = _dias_plantilla(plantilla)
    data = TurnoPlantillaRead.model_validate(plantilla)
    data.dias_semana = dias
    data.nombre_titular = (
        usuarios.get(plantilla.id_usuario_titular).nombre_completo
        if plantilla.id_usuario_titular in usuarios
        else None
    )
    data.nombre_sucursal = (
        sucursales.get(plantilla.id_sucursal).nombre
        if plantilla.id_sucursal in sucursales
        else None
    )
    return data


def _tarifa_read(tarifa: TarifaTurno, sucursales: dict[int, Sucursal]) -> TarifaTurnoRead:
    data = TarifaTurnoRead.model_validate(tarifa)
    data.nombre_sucursal = (
        sucursales.get(tarifa.id_sucursal).nombre
        if tarifa.id_sucursal in sucursales
        else None
    )
    return data


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------


@router.get("/", response_model=None)
async def list_turnos(
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[Usuario, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    id_usuario: int | None = None,
    id_sucursal: int | None = None,
    estado: str | None = None,
) -> PaginatedResponse[TurnoRead]:
    query = select(TurnoCalendario)
    count_query = select(func.count()).select_from(TurnoCalendario)

    filters, _ = _filtros_rol(current, id_sucursal, id_usuario)
    if fecha_desde:
        filters.append(TurnoCalendario.fecha >= fecha_desde)
    if fecha_hasta:
        filters.append(TurnoCalendario.fecha <= fecha_hasta)
    if estado:
        filters.append(TurnoCalendario.estado_turno == estado)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(
        query.options(
            selectinload(TurnoCalendario.titular),
            selectinload(TurnoCalendario.reemplazo),
        )
        .offset(offset)
        .limit(page_size)
        .order_by(TurnoCalendario.fecha, TurnoCalendario.hora_inicio)
    )
    items = result.scalars().all()
    sucursales = await _mapa_sucursales(db)

    return PaginatedResponse(
        items=[_turno_read(t, sucursales) for t in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/calendario", response_model=None)
async def get_calendario(
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[Usuario, Depends(get_current_user)],
    fecha_desde: date = Query(...),
    fecha_hasta: date = Query(...),
    id_sucursal: int | None = None,
    id_usuario: int | None = None,
) -> CalendarioTurnosRead:
    if fecha_hasta < fecha_desde:
        raise ValidationError("La fecha final no puede ser anterior a la inicial")
    if (fecha_hasta - fecha_desde).days > 93:
        raise ValidationError("El calendario no puede abarcar más de 93 días")

    filters, _ = _filtros_rol(current, id_sucursal, id_usuario)
    filters.extend(
        [
            TurnoCalendario.fecha >= fecha_desde,
            TurnoCalendario.fecha <= fecha_hasta,
        ]
    )

    result = await db.execute(
        select(TurnoCalendario)
        .options(
            selectinload(TurnoCalendario.titular),
            selectinload(TurnoCalendario.reemplazo),
        )
        .where(and_(*filters))
        .order_by(TurnoCalendario.fecha, TurnoCalendario.hora_inicio)
    )
    items = result.scalars().all()
    sucursales = await _mapa_sucursales(db)

    festivos_db = list((await db.execute(select(Festivo))).scalars().all())
    festivos: list[FestivoRead] = []
    for festivo in festivos_db:
        if festivo.recurrente_anual:
            if any(
                f.month == festivo.fecha.month and f.day == festivo.fecha.day
                for f in (
                    fecha_desde + timedelta(days=i)
                    for i in range((fecha_hasta - fecha_desde).days + 1)
                )
            ):
                festivos.append(FestivoRead.model_validate(festivo))
        elif fecha_desde <= festivo.fecha <= fecha_hasta:
            festivos.append(FestivoRead.model_validate(festivo))

    return CalendarioTurnosRead(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        turnos=[_turno_read(t, sucursales) for t in items],
        festivos=festivos,
    )


@router.get("/sucursales", response_model=None)
async def list_sucursales(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
) -> list[dict]:
    result = await db.execute(select(Sucursal).where(Sucursal.activa == True))  # noqa: E712
    return [
        {"id_sucursal": s.id_sucursal, "nombre": s.nombre}
        for s in result.scalars().all()
    ]


@router.get("/tarifa-sugerida", response_model=None)
async def get_tarifa_sugerida(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_user)],
    fecha: date = Query(...),
    hora_inicio: str = Query(...),
    hora_fin: str = Query(...),
    id_sucursal: int | None = None,
) -> TarifaSugeridaRead:
    from datetime import time as _time

    try:
        hi = _time.fromisoformat(hora_inicio)
        hf = _time.fromisoformat(hora_fin)
    except ValueError as exc:
        raise ValidationError("Las horas deben tener formato HH:MM") from exc

    tarifa = await resolver_tarifa(db, fecha, hi, hf, id_sucursal)
    if tarifa is None:
        return TarifaSugeridaRead()
    return TarifaSugeridaRead(
        id_tarifa=tarifa.id_tarifa,
        nombre=tarifa.nombre,
        valor=Decimal(str(tarifa.valor)),
    )


# ---------------------------------------------------------------------------
# Turnos
# ---------------------------------------------------------------------------


@router.post("/", response_model=None, status_code=201)
async def create_turno(
    body: TurnoCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_admin)],
) -> TurnoRead:
    sucursales = await _mapa_sucursales(db)
    return await _crear_turno(db, body, sucursales)


@router.post("/bulk", response_model=None, status_code=201)
async def create_turnos_bulk(
    body: TurnoBulkCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_admin)],
) -> TurnoBulkResultado:
    sucursales = await _mapa_sucursales(db)
    creados: list[TurnoRead] = []
    errores: list[str] = []
    for item in body.turnos:
        try:
            creados.append(await _crear_turno(db, item, sucursales))
        except Exception as exc:  # cada turno se informa por separado
            mensaje = getattr(exc, "message", str(exc))
            errores.append(f"{item.fecha} {item.hora_inicio:%H:%M}: {mensaje}")
    return TurnoBulkResultado(
        creados=len(creados),
        omitidos=len(errores),
        errores=errores,
        turnos=creados,
    )


@router.post("/bulk-delete", response_model=None)
async def delete_turnos_bulk(
    body: TurnoBulkDelete,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_admin)],
) -> MessageResponse:
    result = await db.execute(
        select(TurnoCalendario).where(TurnoCalendario.id_turno.in_(body.ids))
    )
    turnos = result.scalars().all()
    eliminados = 0
    protegidos = 0
    for turno in turnos:
        if turno.estado_turno == EstadoTurno.pagado:
            protegidos += 1
            continue
        await db.delete(turno)
        eliminados += 1

    detalle = {"eliminados": eliminados}
    if protegidos:
        detalle["protegidos"] = protegidos
    return MessageResponse(
        message=f"Se eliminaron {eliminados} turnos"
        + (f" y se conservaron {protegidos} pagados" if protegidos else ""),
        detail=detalle,
    )


@router.post("/generar", response_model=None)
async def generar_turnos(
    body: GeneracionTurnosRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_admin)],
) -> GeneracionTurnosResponse:
    return await generar_turnos_masivo(db, body)


# ---------------------------------------------------------------------------
# Tarifas
# ---------------------------------------------------------------------------


@router.get("/tarifas", response_model=None)
async def list_tarifas(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_admin)],
    activa: bool | None = None,
) -> list[TarifaTurnoRead]:
    query = select(TarifaTurno)
    if activa is not None:
        query = query.where(TarifaTurno.activa == activa)
    result = await db.execute(
        query.order_by(TarifaTurno.prioridad.desc(), TarifaTurno.id_tarifa)
    )
    sucursales = await _mapa_sucursales(db)
    return [_tarifa_read(t, sucursales) for t in result.scalars().all()]


@router.post("/tarifas", response_model=None, status_code=201)
async def create_tarifa(
    body: TarifaTurnoCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_admin)],
) -> TarifaTurnoRead:
    if body.id_sucursal is not None:
        sucursal = (
            await db.execute(
                select(Sucursal).where(Sucursal.id_sucursal == body.id_sucursal)
            )
        ).scalar_one_or_none()
        if sucursal is None:
            raise NotFoundError("Sucursal", body.id_sucursal)

    tarifa = TarifaTurno(**body.model_dump())
    db.add(tarifa)
    await db.flush()
    sucursales = await _mapa_sucursales(db)
    return _tarifa_read(tarifa, sucursales)


@router.patch("/tarifas/{tarifa_id}", response_model=None)
async def update_tarifa(
    tarifa_id: int,
    body: TarifaTurnoUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_admin)],
) -> TarifaTurnoRead:
    tarifa = (
        await db.execute(select(TarifaTurno).where(TarifaTurno.id_tarifa == tarifa_id))
    ).scalar_one_or_none()
    if tarifa is None:
        raise NotFoundError("Tarifa", tarifa_id)

    cambios = body.model_dump(exclude_unset=True)
    if cambios.get("id_sucursal") is not None:
        sucursal = (
            await db.execute(
                select(Sucursal).where(
                    Sucursal.id_sucursal == cambios["id_sucursal"]
                )
            )
        ).scalar_one_or_none()
        if sucursal is None:
            raise NotFoundError("Sucursal", cambios["id_sucursal"])

    for campo, valor in cambios.items():
        setattr(tarifa, campo, valor)

    await db.flush()
    sucursales = await _mapa_sucursales(db)
    return _tarifa_read(tarifa, sucursales)


@router.delete("/tarifas/{tarifa_id}", response_model=None)
async def delete_tarifa(
    tarifa_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_admin)],
) -> MessageResponse:
    tarifa = (
        await db.execute(select(TarifaTurno).where(TarifaTurno.id_tarifa == tarifa_id))
    ).scalar_one_or_none()
    if tarifa is None:
        raise NotFoundError("Tarifa", tarifa_id)
    tarifa.activa = False
    return MessageResponse(message="Tarifa desactivada")


# ---------------------------------------------------------------------------
# Patrones semanales
# ---------------------------------------------------------------------------


@router.get("/plantillas", response_model=None)
async def list_plantillas(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_admin)],
    id_usuario: int | None = None,
    id_sucursal: int | None = None,
    activa: bool | None = None,
) -> list[TurnoPlantillaRead]:
    query = select(TurnoPlantilla)
    if id_usuario:
        query = query.where(TurnoPlantilla.id_usuario_titular == id_usuario)
    if id_sucursal:
        query = query.where(TurnoPlantilla.id_sucursal == id_sucursal)
    if activa is not None:
        query = query.where(TurnoPlantilla.activa == activa)

    result = await db.execute(
        query.order_by(
            TurnoPlantilla.id_usuario_titular, TurnoPlantilla.hora_inicio
        )
    )
    plantillas = result.scalars().all()
    usuarios = {
        u.id_usuario: u
        for u in (await db.execute(select(Usuario))).scalars().all()
    }
    sucursales = await _mapa_sucursales(db)
    return [_plantilla_read(p, usuarios, sucursales) for p in plantillas]


@router.post("/plantillas", response_model=None, status_code=201)
async def create_plantilla(
    body: TurnoPlantillaCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_admin)],
) -> TurnoPlantillaRead:
    usuario, sucursal_id = await _validar_usuario_sucursal(
        db, body.id_usuario_titular, body.id_sucursal
    )
    dias = body.dias_semana or [body.dia_semana or 0]
    valor = await _valor_para_plantilla(
        db,
        dias,
        body.hora_inicio,
        body.hora_fin,
        sucursal_id,
        body.valor_total_turno,
        body.usar_tarifa,
    )

    plantilla = TurnoPlantilla(
        nombre=body.nombre,
        dia_semana=dias[0],
        dias_semana=dias,
        hora_inicio=body.hora_inicio,
        hora_fin=body.hora_fin,
        valor_total_turno=valor,
        usar_tarifa=body.usar_tarifa,
        id_usuario_titular=usuario.id_usuario,
        id_sucursal=sucursal_id,
        activa=body.activa,
    )
    db.add(plantilla)
    await db.flush()

    usuarios = {usuario.id_usuario: usuario}
    sucursales = await _mapa_sucursales(db)
    return _plantilla_read(plantilla, usuarios, sucursales)


@router.patch("/plantillas/{plantilla_id}", response_model=None)
async def update_plantilla(
    plantilla_id: int,
    body: TurnoPlantillaUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_admin)],
) -> TurnoPlantillaRead:
    plantilla = (
        await db.execute(
            select(TurnoPlantilla).where(TurnoPlantilla.id_plantilla == plantilla_id)
        )
    ).scalar_one_or_none()
    if plantilla is None:
        raise NotFoundError("Patrón", plantilla_id)

    cambios = body.model_dump(exclude_unset=True)

    if "id_usuario_titular" in cambios or "id_sucursal" in cambios:
        usuario, sucursal_id = await _validar_usuario_sucursal(
            db,
            cambios.get("id_usuario_titular", plantilla.id_usuario_titular),
            cambios.get("id_sucursal", plantilla.id_sucursal),
        )
        cambios["id_usuario_titular"] = usuario.id_usuario
        cambios["id_sucursal"] = sucursal_id

    if "dias_semana" in cambios and cambios["dias_semana"]:
        cambios["dias_semana"] = sorted(
            {int(d) for d in cambios["dias_semana"] if 0 <= int(d) <= 6}
        )
        if not cambios["dias_semana"]:
            raise ValidationError("Debe indicar al menos un día")
        cambios["dia_semana"] = cambios["dias_semana"][0]

    for campo, valor in cambios.items():
        setattr(plantilla, campo, valor)

    if plantilla.usar_tarifa and "valor_total_turno" not in cambios:
        plantilla.valor_total_turno = await _valor_para_plantilla(
            db,
            _dias_plantilla(plantilla),
            plantilla.hora_inicio,
            plantilla.hora_fin,
            plantilla.id_sucursal,
            plantilla.valor_total_turno,
            plantilla.usar_tarifa,
        )

    await db.flush()
    usuarios = {
        u.id_usuario: u
        for u in (
            await db.execute(
                select(Usuario).where(
                    Usuario.id_usuario == plantilla.id_usuario_titular
                )
            )
        )
        .scalars()
        .all()
    }
    sucursales = await _mapa_sucursales(db)
    return _plantilla_read(plantilla, usuarios, sucursales)


@router.delete("/plantillas/{plantilla_id}", response_model=None)
async def delete_plantilla(
    plantilla_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_admin)],
) -> MessageResponse:
    plantilla = (
        await db.execute(
            select(TurnoPlantilla).where(TurnoPlantilla.id_plantilla == plantilla_id)
        )
    ).scalar_one_or_none()
    if plantilla is None:
        raise NotFoundError("Patrón", plantilla_id)
    plantilla.activa = False
    return MessageResponse(message="Patrón desactivado")


# ---------------------------------------------------------------------------
# Reemplazos y eliminación individual
# ---------------------------------------------------------------------------


@router.post("/solicitud-reemplazo", response_model=None)
async def solicitud_reemplazo(
    body: SolicitudReemplazo,
    db: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[Usuario, Depends(get_current_user)],
) -> MessageResponse:
    await procesar_solicitud_reemplazo(db, body.id_turno, current.id_usuario)
    return MessageResponse(message="Solicitud de reemplazo enviada")


@router.post("/aprobar-reemplazo", response_model=None)
async def aprobar_reemplazo(
    body: AprobacionReemplazo,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_admin)],
) -> MessageResponse:
    result = await db.execute(
        select(TurnoCalendario).where(TurnoCalendario.id_turno == body.id_turno)
    )
    turno = result.scalar_one_or_none()
    if not turno:
        raise NotFoundError("Turno", body.id_turno)

    if body.aprobar:
        horas_empleado = await calcular_horas_semana_empleado(
            db, body.id_usuario_reemplazo, turno.fecha
        )
        turno_horas = duracion_horas(turno.hora_inicio, turno.hora_fin)

        if horas_empleado + turno_horas > WEEKLY_HOUR_LIMIT:
            raise HourLimitExceededError(
                f"Empleado {body.id_usuario_reemplazo}",
                horas_empleado + turno_horas,
                WEEKLY_HOUR_LIMIT,
            )

        turno.id_usuario_reemplazo = body.id_usuario_reemplazo
        turno.estado_turno = EstadoTurno.activo
    else:
        turno.estado_turno = EstadoTurno.programado

    return MessageResponse(
        message="Reemplazo aprobado" if body.aprobar else "Reemplazo rechazado"
    )


@router.delete("/{turno_id}", response_model=None)
async def delete_turno(
    turno_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current: Annotated[Usuario, Depends(get_current_admin)],
) -> MessageResponse:
    result = await db.execute(
        select(TurnoCalendario).where(TurnoCalendario.id_turno == turno_id)
    )
    turno = result.scalar_one_or_none()
    if not turno:
        raise NotFoundError("Turno", turno_id)
    if turno.estado_turno == EstadoTurno.pagado:
        raise ConflictError("No se puede eliminar un turno que ya fue pagado")

    await db.delete(turno)
    return MessageResponse(message="Turno eliminado")
