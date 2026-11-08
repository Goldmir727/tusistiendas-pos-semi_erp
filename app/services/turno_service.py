from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime as _dt, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.sucursal import Sucursal
from app.models.turno import (
    EstadoTurno,
    Festivo,
    TarifaTurno,
    TurnoCalendario,
    TurnoPlantilla,
)
from app.models.usuario import Usuario
from app.schemas.turno import (
    GeneracionTurnoItem,
    GeneracionTurnosRequest,
    GeneracionTurnosResponse,
)

WEEKLY_HOUR_LIMIT = 44.0


def duracion_horas(hora_inicio, hora_fin) -> float:
    inicio = hora_inicio.hour + hora_inicio.minute / 60
    fin = hora_fin.hour + hora_fin.minute / 60
    if fin <= inicio:
        fin += 24
    return fin - inicio


def minutos_hora(valor) -> int:
    return valor.hour * 60 + valor.minute


def intervalo_absoluto(fecha: date, hora_inicio, hora_fin) -> tuple[int, int]:
    inicio = fecha.toordinal() * 1440 + minutos_hora(hora_inicio)
    fin = inicio + int(round(duracion_horas(hora_inicio, hora_fin) * 60))
    return inicio, fin


def se_solapan(
    fecha_a: date,
    inicio_a,
    fin_a,
    fecha_b: date,
    inicio_b,
    fin_b,
) -> bool:
    a_ini, a_fin = intervalo_absoluto(fecha_a, inicio_a, fin_a)
    b_ini, b_fin = intervalo_absoluto(fecha_b, inicio_b, fin_b)
    return a_ini < b_fin and b_ini < a_fin


def beneficiario_turno(turno: TurnoCalendario) -> int:
    if turno.id_usuario_reemplazo and (turno.horas_reemplazadas_parcial or 0) == 0:
        return turno.id_usuario_reemplazo
    return turno.id_usuario_titular


def ahora_local() -> _dt:
    return _dt.now(ZoneInfo(get_settings().TIMEZONE))


def hoy_local():
    return ahora_local().date()


def semana_inicio(fecha: date) -> date:
    return fecha - timedelta(days=fecha.weekday())


def rango_fechas(desde: date, hasta: date):
    actual = desde
    while actual <= hasta:
        yield actual
        actual += timedelta(days=1)


async def calcular_horas_semana_empleado(
    db: AsyncSession,
    id_usuario: int,
    fecha: date,
) -> float:
    year, week, _ = fecha.isocalendar()
    start_week = date.fromisocalendar(year, week, 1)
    end_week = start_week + timedelta(days=6)

    result = await db.execute(
        select(TurnoCalendario).where(
            and_(
                TurnoCalendario.fecha >= start_week,
                TurnoCalendario.fecha <= end_week,
                (TurnoCalendario.id_usuario_titular == id_usuario)
                | (TurnoCalendario.id_usuario_reemplazo == id_usuario),
                TurnoCalendario.estado_turno.in_(["activo", "finalizado", "pagado"]),
            )
        )
    )
    turnos = result.scalars().all()

    total_horas = 0.0
    for t in turnos:
        if t.id_usuario_reemplazo and (t.horas_reemplazadas_parcial or 0) > 0:
            if id_usuario == t.id_usuario_reemplazo:
                total_horas += float(t.horas_reemplazadas_parcial)
            elif id_usuario == t.id_usuario_titular:
                total_horas += max(
                    0.0,
                    duracion_horas(t.hora_inicio, t.hora_fin)
                    - float(t.horas_reemplazadas_parcial),
                )
            continue
        if beneficiario_turno(t) == id_usuario:
            total_horas += duracion_horas(t.hora_inicio, t.hora_fin)

    return total_horas


async def _mapa_horas_semanales(
    db: AsyncSession,
    ids_usuarios: list[int],
    fecha_desde: date,
    fecha_hasta: date,
) -> dict[tuple[int, date], float]:
    """Horas ya asignadas por empleado/semana, incluyendo turnos programados."""
    if not ids_usuarios:
        return {}

    inicio = semana_inicio(fecha_desde)
    fin = semana_inicio(fecha_hasta) + timedelta(days=6)
    result = await db.execute(
        select(TurnoCalendario).where(
            TurnoCalendario.fecha >= inicio,
            TurnoCalendario.fecha <= fin,
            or_(
                TurnoCalendario.id_usuario_titular.in_(ids_usuarios),
                TurnoCalendario.id_usuario_reemplazo.in_(ids_usuarios),
            ),
        )
    )

    horas: dict[tuple[int, date], float] = defaultdict(float)
    ids = set(ids_usuarios)
    for turno in result.scalars().all():
        duracion = duracion_horas(turno.hora_inicio, turno.hora_fin)
        parcial = float(turno.horas_reemplazadas_parcial or 0)
        clave = semana_inicio(turno.fecha)

        if turno.id_usuario_reemplazo and parcial > 0:
            if turno.id_usuario_reemplazo in ids:
                horas[(turno.id_usuario_reemplazo, clave)] += parcial
            if turno.id_usuario_titular in ids:
                horas[(turno.id_usuario_titular, clave)] += max(0.0, duracion - parcial)
        elif turno.id_usuario_reemplazo:
            if turno.id_usuario_reemplazo in ids:
                horas[(turno.id_usuario_reemplazo, clave)] += duracion
        elif turno.id_usuario_titular in ids:
            horas[(turno.id_usuario_titular, clave)] += duracion

    return horas


async def buscar_solapamiento(
    db: AsyncSession,
    id_usuario: int,
    fecha: date,
    hora_inicio,
    hora_fin,
    excluir_id: int | None = None,
) -> TurnoCalendario | None:
    result = await db.execute(
        select(TurnoCalendario).where(
            TurnoCalendario.fecha >= fecha - timedelta(days=1),
            TurnoCalendario.fecha <= fecha + timedelta(days=1),
            or_(
                TurnoCalendario.id_usuario_titular == id_usuario,
                TurnoCalendario.id_usuario_reemplazo == id_usuario,
            ),
        )
    )
    for turno in result.scalars().all():
        if excluir_id is not None and turno.id_turno == excluir_id:
            continue
        if se_solapan(
            fecha,
            hora_inicio,
            hora_fin,
            turno.fecha,
            turno.hora_inicio,
            turno.hora_fin,
        ):
            return turno
    return None


async def cargar_tarifas_activas(db: AsyncSession) -> list[TarifaTurno]:
    result = await db.execute(
        select(TarifaTurno)
        .where(TarifaTurno.activa == True)  # noqa: E712
        .order_by(TarifaTurno.id_tarifa)
    )
    return list(result.scalars().all())


def _tarifa_contiene(tarifa: TarifaTurno, dia_semana: int, hora_inicio, hora_fin) -> bool:
    dias = tarifa.dias_semana or []
    if dia_semana not in dias:
        return False

    tarifa_ini = minutos_hora(tarifa.hora_inicio)
    tarifa_fin = tarifa_ini + int(
        round(duracion_horas(tarifa.hora_inicio, tarifa.hora_fin) * 60)
    )
    turno_ini = minutos_hora(hora_inicio)
    turno_fin = turno_ini + int(round(duracion_horas(hora_inicio, hora_fin) * 60))
    return turno_ini >= tarifa_ini and turno_fin <= tarifa_fin


def _orden_tarifa(tarifa: TarifaTurno) -> tuple:
    duracion = int(
        round(duracion_horas(tarifa.hora_inicio, tarifa.hora_fin) * 60)
    )
    # Primero la regla de la sucursal, luego la más específica (rango más
    # corto), luego la prioridad manual y finalmente la hora de inicio.
    return (
        0 if tarifa.id_sucursal is not None else 1,
        duracion,
        -int(tarifa.prioridad or 0),
        minutos_hora(tarifa.hora_inicio),
        int(tarifa.id_tarifa or 0),
    )


def resolver_tarifa_en_lista(
    tarifas: list[TarifaTurno],
    fecha: date,
    hora_inicio,
    hora_fin,
    id_sucursal: int | None,
) -> TarifaTurno | None:
    dia = fecha.weekday()
    candidatas = [
        t
        for t in tarifas
        if (t.id_sucursal is None or t.id_sucursal == id_sucursal)
        and _tarifa_contiene(t, dia, hora_inicio, hora_fin)
    ]
    if not candidatas:
        return None
    candidatas.sort(key=_orden_tarifa)
    return candidatas[0]


async def resolver_tarifa(
    db: AsyncSession,
    fecha: date,
    hora_inicio,
    hora_fin,
    id_sucursal: int | None,
) -> TarifaTurno | None:
    tarifas = await cargar_tarifas_activas(db)
    return resolver_tarifa_en_lista(tarifas, fecha, hora_inicio, hora_fin, id_sucursal)


async def resolver_valor_turno(
    db: AsyncSession,
    fecha: date,
    hora_inicio,
    hora_fin,
    id_sucursal: int | None,
    valor_manual: Decimal | float | None = None,
    usar_tarifa: bool = True,
) -> tuple[Decimal, TarifaTurno | None]:
    if not usar_tarifa and valor_manual is not None:
        return Decimal(str(valor_manual)), None

    tarifa = await resolver_tarifa(db, fecha, hora_inicio, hora_fin, id_sucursal)
    if tarifa is not None:
        return Decimal(str(tarifa.valor)), tarifa

    if valor_manual is not None:
        return Decimal(str(valor_manual)), None
    return Decimal("0"), None


def _dias_plantilla(plantilla: TurnoPlantilla) -> list[int]:
    if plantilla.dias_semana:
        return sorted({int(d) for d in plantilla.dias_semana if 0 <= int(d) <= 6})
    if plantilla.dia_semana is not None:
        return [int(plantilla.dia_semana)]
    return []


async def generar_turnos_masivo(
    db: AsyncSession,
    body: GeneracionTurnosRequest,
) -> GeneracionTurnosResponse:
    query = select(TurnoPlantilla).where(TurnoPlantilla.activa == True)  # noqa: E712
    if body.id_plantillas:
        query = query.where(TurnoPlantilla.id_plantilla.in_(body.id_plantillas))
    if body.id_usuarios:
        query = query.where(TurnoPlantilla.id_usuario_titular.in_(body.id_usuarios))
    if body.id_sucursal:
        query = query.where(TurnoPlantilla.id_sucursal == body.id_sucursal)

    plantillas = list(
        (await db.execute(query.order_by(TurnoPlantilla.id_usuario_titular, TurnoPlantilla.id_plantilla)))
        .scalars()
        .all()
    )

    if not plantillas:
        return GeneracionTurnosResponse(
            dry_run=body.dry_run,
            total_previstos=0,
            total_creados=0,
            total_existentes=0,
            total_conflictos=0,
            total_reemplazados=0,
            items=[],
        )

    ids_usuarios = sorted({p.id_usuario_titular for p in plantillas})

    usuarios = {
        u.id_usuario: u
        for u in (
            await db.execute(select(Usuario).where(Usuario.id_usuario.in_(ids_usuarios)))
        )
        .scalars()
        .all()
    }
    sucursales = {
        s.id_sucursal: s
        for s in (
            await db.execute(
                select(Sucursal).where(
                    Sucursal.id_sucursal.in_(
                        sorted({p.id_sucursal for p in plantillas if p.id_sucursal})
                    )
                )
            )
        )
        .scalars()
        .all()
    }
    tarifas = await cargar_tarifas_activas(db)
    horas_semana = await _mapa_horas_semanales(
        db, ids_usuarios, body.fecha_desde, body.fecha_hasta
    )

    festivos_db = list((await db.execute(select(Festivo))).scalars().all())
    festivos_fijos = {f.fecha for f in festivos_db if not f.recurrente_anual}
    festivos_anuales = {
        (f.fecha.month, f.fecha.day) for f in festivos_db if f.recurrente_anual
    }

    result = await db.execute(
        select(TurnoCalendario).where(
            TurnoCalendario.fecha >= body.fecha_desde - timedelta(days=1),
            TurnoCalendario.fecha <= body.fecha_hasta + timedelta(days=1),
            or_(
                TurnoCalendario.id_usuario_titular.in_(ids_usuarios),
                TurnoCalendario.id_usuario_reemplazo.in_(ids_usuarios),
            ),
        )
    )
    existentes: dict[tuple[int, date], list[TurnoCalendario]] = defaultdict(list)
    for turno in result.scalars().all():
        existentes[(turno.id_usuario_titular, turno.fecha)].append(turno)
        if turno.id_usuario_reemplazo:
            existentes[(turno.id_usuario_reemplazo, turno.fecha)].append(turno)

    planificados: dict[tuple[int, date], list[TurnoCalendario]] = defaultdict(list)
    turnos_reemplazar: dict[int, TurnoCalendario] = {}
    items: list[GeneracionTurnoItem] = []

    for plantilla in plantillas:
        usuario = usuarios.get(plantilla.id_usuario_titular)
        if usuario is None or not usuario.activo:
            continue

        dias = _dias_plantilla(plantilla)
        if not dias:
            continue

        for fecha in rango_fechas(body.fecha_desde, body.fecha_hasta):
            if fecha.weekday() not in dias:
                continue

            valor = Decimal(str(plantilla.valor_total_turno or 0))
            if body.recalcular_tarifa and plantilla.usar_tarifa:
                tarifa = resolver_tarifa_en_lista(
                    tarifas,
                    fecha,
                    plantilla.hora_inicio,
                    plantilla.hora_fin,
                    plantilla.id_sucursal,
                )
                if tarifa is not None:
                    valor = Decimal(str(tarifa.valor))

            clave = (plantilla.id_usuario_titular, fecha)
            es_festivo = fecha in festivos_fijos or (
                (fecha.month, fecha.day) in festivos_anuales
            )

            existentes_dia = existentes.get(clave, [])
            planificados_dia = planificados.get(clave, [])

            exacto = next(
                (
                    t
                    for t in existentes_dia
                    if t.hora_inicio == plantilla.hora_inicio
                    and t.hora_fin == plantilla.hora_fin
                ),
                None,
            )
            if exacto is not None:
                items.append(
                    GeneracionTurnoItem(
                        fecha=fecha,
                        id_usuario_titular=usuario.id_usuario,
                        nombre_titular=usuario.nombre_completo,
                        id_sucursal=plantilla.id_sucursal,
                        nombre_sucursal=sucursales.get(plantilla.id_sucursal).nombre
                        if plantilla.id_sucursal in sucursales
                        else None,
                        hora_inicio=plantilla.hora_inicio,
                        hora_fin=plantilla.hora_fin,
                        valor_total_turno=valor,
                        accion="existente",
                        motivo="Ya existe un turno con el mismo horario",
                        id_plantilla=plantilla.id_plantilla,
                        id_turno_existente=exacto.id_turno,
                        es_festivo=es_festivo,
                    )
                )
                continue

            exacto_plan = next(
                (
                    t
                    for t in planificados_dia
                    if t.hora_inicio == plantilla.hora_inicio
                    and t.hora_fin == plantilla.hora_fin
                ),
                None,
            )
            if exacto_plan is not None:
                items.append(
                    GeneracionTurnoItem(
                        fecha=fecha,
                        id_usuario_titular=usuario.id_usuario,
                        nombre_titular=usuario.nombre_completo,
                        id_sucursal=plantilla.id_sucursal,
                        nombre_sucursal=sucursales.get(plantilla.id_sucursal).nombre
                        if plantilla.id_sucursal in sucursales
                        else None,
                        hora_inicio=plantilla.hora_inicio,
                        hora_fin=plantilla.hora_fin,
                        valor_total_turno=valor,
                        accion="conflicto",
                        motivo="Dos patrones generan el mismo horario",
                        id_plantilla=plantilla.id_plantilla,
                        es_festivo=es_festivo,
                    )
                )
                continue

            solapados = [
                t
                for t in [*existentes_dia, *planificados_dia]
                if se_solapan(
                    fecha,
                    plantilla.hora_inicio,
                    plantilla.hora_fin,
                    t.fecha,
                    t.hora_inicio,
                    t.hora_fin,
                )
            ]

            accion = "crear"
            motivo: str | None = None
            ids_reemplazo_dia: list[TurnoCalendario] = []

            if solapados:
                solapados_existentes = [
                    t for t in solapados if t.id_turno is not None
                ]
                solapados_planificados = [
                    t for t in solapados if t.id_turno is None
                ]
                if (
                    body.modo == "reemplazar"
                    and solapados_existentes
                    and not solapados_planificados
                    and all(
                        t.estado_turno == EstadoTurno.programado
                        for t in solapados_existentes
                    )
                ):
                    accion = "reemplazar"
                    ids_reemplazo_dia = solapados_existentes
                    motivo = "Se reemplaza un turno programado que se cruza"
                else:
                    accion = "conflicto"
                    motivo = "Se cruza con otro turno del empleado"

            clave_horas = (usuario.id_usuario, semana_inicio(fecha))
            horas_actuales = horas_semana.get(clave_horas, 0.0)
            if accion == "reemplazar":
                for turno in ids_reemplazo_dia:
                    horas_actuales -= duracion_horas(turno.hora_inicio, turno.hora_fin)
            horas_totales = horas_actuales + duracion_horas(
                plantilla.hora_inicio, plantilla.hora_fin
            )
            advertencia_horas = horas_totales > WEEKLY_HOUR_LIMIT

            if accion in ("crear", "reemplazar"):
                horas_semana[clave_horas] = horas_totales
                turno_plan = TurnoCalendario(
                    id_usuario_titular=usuario.id_usuario,
                    fecha=fecha,
                    hora_inicio=plantilla.hora_inicio,
                    hora_fin=plantilla.hora_fin,
                    valor_total_turno=valor,
                    id_sucursal=plantilla.id_sucursal,
                    estado_turno=EstadoTurno.programado,
                )
                planificados[clave].append(turno_plan)
                for turno in ids_reemplazo_dia:
                    if turno.id_turno is not None:
                        turnos_reemplazar[turno.id_turno] = turno

            if advertencia_horas:
                detalle = f"Quedaría con {horas_totales:.1f}h en la semana (límite {WEEKLY_HOUR_LIMIT:.0f}h)"
                motivo = f"{motivo}. {detalle}" if motivo else detalle

            if (
                accion in ("crear", "reemplazar")
                and usuario.id_sucursal is not None
                and usuario.id_sucursal != plantilla.id_sucursal
            ):
                detalle = "La sucursal del patrón no coincide con la del empleado"
                motivo = f"{motivo}. {detalle}" if motivo else detalle

            items.append(
                GeneracionTurnoItem(
                    fecha=fecha,
                    id_usuario_titular=usuario.id_usuario,
                    nombre_titular=usuario.nombre_completo,
                    id_sucursal=plantilla.id_sucursal,
                    nombre_sucursal=sucursales.get(plantilla.id_sucursal).nombre
                    if plantilla.id_sucursal in sucursales
                    else None,
                    hora_inicio=plantilla.hora_inicio,
                    hora_fin=plantilla.hora_fin,
                    valor_total_turno=valor,
                    accion=accion,
                    motivo=motivo,
                    id_plantilla=plantilla.id_plantilla,
                    id_turno_existente=ids_reemplazo_dia[0].id_turno
                    if ids_reemplazo_dia
                    else None,
                    es_festivo=es_festivo,
                    horas_semana=round(horas_totales, 1),
                    advertencia_horas=advertencia_horas,
                )
            )

    if not body.dry_run:
        for turno in turnos_reemplazar.values():
            await db.delete(turno)
        for lista in planificados.values():
            for turno in lista:
                db.add(turno)
        await db.flush()

    total_creados = sum(1 for i in items if i.accion == "crear")
    total_reemplazados = sum(1 for i in items if i.accion == "reemplazar")
    total_existentes = sum(1 for i in items if i.accion == "existente")
    total_conflictos = sum(1 for i in items if i.accion == "conflicto")

    return GeneracionTurnosResponse(
        dry_run=body.dry_run,
        total_previstos=len(items),
        total_creados=total_creados,
        total_existentes=total_existentes,
        total_conflictos=total_conflictos,
        total_reemplazados=total_reemplazados,
        items=items,
    )


async def generar_turnos_desde_plantilla(
    db: AsyncSession,
    fecha_desde: date,
    fecha_hasta: date,
) -> int:
    respuesta = await generar_turnos_masivo(
        db,
        GeneracionTurnosRequest(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            modo="omitir",
            dry_run=False,
        ),
    )
    return respuesta.total_creados + respuesta.total_reemplazados


async def procesar_solicitud_reemplazo(
    db: AsyncSession,
    id_turno: int,
    id_usuario_solicitante: int,
) -> None:
    result = await db.execute(
        select(TurnoCalendario).where(TurnoCalendario.id_turno == id_turno)
    )
    turno = result.scalar_one_or_none()
    if not turno:
        from app.exceptions import NotFoundError

        raise NotFoundError("Turno", id_turno)

    if turno.id_usuario_titular != id_usuario_solicitante:
        from app.exceptions import AuthorizationError

        raise AuthorizationError("Solo el titular puede solicitar reemplazo")

    turno.estado_turno = EstadoTurno.solicitud_reemplazo
