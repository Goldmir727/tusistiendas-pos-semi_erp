from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import CashDrawerError
from app.models.caja import EstadoCaja, SesionCaja
from app.models.sucursal import PuntoVenta, Sucursal
from app.models.turno import EstadoTurno, TurnoCalendario
from app.services.turno_service import beneficiario_turno, hoy_local
from app.models.usuario import RolEnum, Usuario
from app.schemas.caja import CajaDoblePanel, CierreCaja, SesionCajaCreate, SesionCajaRead
from app.services.auth_service import get_current_cajero as get_current_user
from app.services.caja_service import (
    abrir_sesion_caja,
    cerrar_sesion_caja,
    efectivo_esperado,
    total_egresos_sesion,
)

router = APIRouter()


async def _sesion_abierta(db: AsyncSession, current_user: Usuario) -> SesionCaja | None:
    """Devuelve la sesión abierta que corresponde al usuario.

    - Cajero: la sesión abierta de su caja asignada (sin importar quién la abrió),
      para que pueda operar el POS y cerrarla aunque la haya abierto un admin.
    - Administrador: su propia sesión abierta más reciente.
    """
    if current_user.rol == RolEnum.cajero and current_user.id_punto_venta is not None:
        query = (
            select(SesionCaja)
            .where(
                SesionCaja.id_punto_venta == current_user.id_punto_venta,
                SesionCaja.estado == EstadoCaja.abierta,
            )
            .order_by(SesionCaja.fecha_apertura.desc())
            .limit(1)
        )
        return (await db.execute(query)).scalars().first()

    query = (
        select(SesionCaja)
        .where(
            SesionCaja.id_usuario_creador == current_user.id_usuario,
            SesionCaja.estado == EstadoCaja.abierta,
        )
        .order_by(SesionCaja.fecha_apertura.desc())
        .limit(1)
    )
    return (await db.execute(query)).scalars().first()


@router.get("/abierta", response_model=None)
async def get_sesion_abierta(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> SesionCajaRead | None:
    sesion = await _sesion_abierta(db, current_user)
    if sesion is None:
        return None
    return SesionCajaRead.model_validate(sesion)


@router.get("/panel", response_model=None)
async def get_panel_caja(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> CajaDoblePanel:
    sesion = await _sesion_abierta(db, current_user)
    if sesion is None:
        raise CashDrawerError("No tiene caja abierta")

    egresos = await total_egresos_sesion(db, sesion.id_sesion_caja)
    return CajaDoblePanel(
        ventas_brutas_turno=float(sesion.ventas_efectivo + sesion.ventas_digitales + sesion.total_tarjeta),
        efectivo_real_esperado=float(efectivo_esperado(sesion, egresos)),
        base_inicial=sesion.base_inicial,
        ventas_efectivo_acumulado=sesion.ventas_efectivo,
        abonos_efectivo=sesion.abonos_efectivo,
        devoluciones_efectivo=sesion.devoluciones_efectivo,
        egresos=float(egresos),
    )


@router.get("/puntos", response_model=None)
async def list_puntos_venta(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> list[dict]:
    from app.models.usuario import RolEnum

    query = (
        select(PuntoVenta, Sucursal)
        .join(Sucursal, Sucursal.id_sucursal == PuntoVenta.id_sucursal)
        .where(PuntoVenta.activa.is_(True))
    )
    if current_user.rol == RolEnum.cajero:
        if current_user.id_punto_venta is None:
            raise CashDrawerError("No tiene una caja asignada")
        query = query.where(PuntoVenta.id_punto_venta == current_user.id_punto_venta)
    query = query.order_by(PuntoVenta.id_sucursal, PuntoVenta.nombre)
    result = await db.execute(query)
    return [
        {
            "id_punto_venta": punto.id_punto_venta,
            "nombre": punto.nombre,
            "id_sucursal": punto.id_sucursal,
            "sucursal": sucursal.nombre,
        }
        for punto, sucursal in result.all()
    ]


@router.get("/empleados-disponibles", response_model=None)
async def empleados_disponibles(
    id_punto_venta: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> list[dict]:
    from app.models.usuario import RolEnum

    punto_result = await db.execute(
        select(PuntoVenta, Sucursal).join(
            Sucursal, Sucursal.id_sucursal == PuntoVenta.id_sucursal
        ).where(PuntoVenta.id_punto_venta == id_punto_venta)
    )
    row = punto_result.first()
    if not row:
        raise CashDrawerError("Caja no encontrada")
    punto, sucursal = row

    if current_user.rol == RolEnum.cajero:
        if current_user.id_punto_venta != id_punto_venta:
            raise CashDrawerError("No tiene permiso sobre esta caja")
    elif current_user.rol != RolEnum.administrador:
        raise CashDrawerError("No tiene permiso")

    hoy = hoy_local()
    result = await db.execute(
        select(TurnoCalendario, Usuario).join(
            Usuario, Usuario.id_usuario == TurnoCalendario.id_usuario_titular
        ).where(
            TurnoCalendario.id_sucursal == punto.id_sucursal,
            TurnoCalendario.fecha == hoy,
            TurnoCalendario.estado_turno.in_(
                [EstadoTurno.programado, EstadoTurno.activo]
            ),
            TurnoCalendario.id_sesion_caja.is_(None),
        )
    )
    salida = []
    for turno, titular in result.all():
        if turno.id_usuario_reemplazo:
            rep_result = await db.execute(
                select(Usuario).where(Usuario.id_usuario == turno.id_usuario_reemplazo)
            )
            rep = rep_result.scalar_one_or_none()
            if rep is not None:
                salida.append(
                    {
                        "id_usuario": rep.id_usuario,
                        "nombre_completo": rep.nombre_completo,
                        "id_turno": turno.id_turno,
                        "hora_inicio": turno.hora_inicio.isoformat(),
                        "hora_fin": turno.hora_fin.isoformat(),
                    }
                )
            continue
        salida.append(
            {
                "id_usuario": titular.id_usuario,
                "nombre_completo": titular.nombre_completo,
                "id_turno": turno.id_turno,
                "hora_inicio": turno.hora_inicio.isoformat(),
                "hora_fin": turno.hora_fin.isoformat(),
            }
        )
    return salida


@router.get("/historial", response_model=None)
async def get_historial_cierres(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
    limit: int = Query(20, ge=1, le=100),
) -> list[SesionCajaRead]:
    query = select(SesionCaja).where(SesionCaja.estado == EstadoCaja.cerrada)
    if current_user.rol != RolEnum.administrador:
        query = query.where(SesionCaja.id_usuario_creador == current_user.id_usuario)
    result = await db.execute(query.order_by(SesionCaja.fecha_cierre.desc()).limit(limit))
    return [SesionCajaRead.model_validate(s) for s in result.scalars().all()]


@router.post("/abrir", response_model=None, status_code=201)
async def abrir_caja(
    body: SesionCajaCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> SesionCajaRead:
    # Validar punto de venta
    punto_result = await db.execute(
        select(PuntoVenta, Sucursal).join(
            Sucursal, Sucursal.id_sucursal == PuntoVenta.id_sucursal
        ).where(PuntoVenta.id_punto_venta == body.id_punto_venta)
    )
    punto_row = punto_result.first()
    if not punto_row:
        raise CashDrawerError("Caja no encontrada")
    punto, sucursal = punto_row
    if not punto.activa:
        raise CashDrawerError("La caja está inactiva")
    if punto.id_sucursal != body.id_sucursal:
        raise CashDrawerError("La caja no pertenece a la sucursal indicada")

    from app.models.usuario import RolEnum

    if current_user.rol == RolEnum.cajero:
        if current_user.id_punto_venta != body.id_punto_venta:
            raise CashDrawerError("No puede abrir una caja distinta a la asignada")
        if current_user.id_sucursal != body.id_sucursal:
            raise CashDrawerError("No puede abrir caja en otra sucursal")

    # Verificar que la caja no esté ya abierta
    abierta_result = await db.execute(
        select(SesionCaja).where(
            SesionCaja.id_punto_venta == body.id_punto_venta,
            SesionCaja.estado == EstadoCaja.abierta,
        )
    )
    if abierta_result.scalar_one_or_none() is not None:
        raise CashDrawerError("La caja ya está abierta")

    if body.id_usuario_abre_caja is None:
        raise CashDrawerError("Debe seleccionar el empleado que abre la caja")

    result = await db.execute(
        select(Usuario).where(Usuario.id_usuario == body.id_usuario_abre_caja)
    )
    empleado = result.scalar_one_or_none()
    if empleado is None or empleado.rol != RolEnum.empleado:
        raise CashDrawerError("El usuario seleccionado no es un empleado válido")
    if not empleado.activo:
        raise CashDrawerError("El empleado seleccionado está inactivo")
    if empleado.id_sucursal != body.id_sucursal:
        raise CashDrawerError("El empleado no pertenece a esta sucursal")

    # El turno del empleado se valida en abrir_sesion_caja (debe existir para hoy).
    if await _sesion_abierta(db, current_user):
        raise CashDrawerError("Ya tiene una sesión de caja abierta")

    sesion = await abrir_sesion_caja(db, current_user.id_usuario, body)
    return SesionCajaRead.model_validate(sesion)


@router.post("/cerrar", response_model=None)
async def cerrar_caja(
    body: CierreCaja,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> SesionCajaRead:
    sesion = await _sesion_abierta(db, current_user)
    if sesion is None:
        raise CashDrawerError("No tiene caja abierta")

    sesion = await cerrar_sesion_caja(db, sesion, body)
    return SesionCajaRead.model_validate(sesion)
