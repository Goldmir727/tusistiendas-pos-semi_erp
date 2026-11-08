from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ValidationError
from app.models.caja import CajaArqueo, SesionCaja
from app.models.egreso import Egreso
from app.models.sucursal import PuntoVenta
from app.models.turno import EstadoTurno, TurnoCalendario
from app.schemas.caja import CierreCaja, SesionCajaCreate
from app.services.turno_service import beneficiario_turno, hoy_local

DENOMINACIONES = {
    "billete_50000": 50000,
    "billete_20000": 20000,
    "billete_10000": 10000,
    "billete_5000": 5000,
    "billete_2000": 2000,
    "billete_1000": 1000,
    "moneda_500": 500,
    "moneda_200": 200,
    "moneda_100": 100,
    "moneda_50": 50,
}


def _d(valor: object | None) -> Decimal:
    return Decimal(str(valor if valor is not None else 0))


async def abrir_sesion_caja(
    db: AsyncSession,
    id_usuario: int,
    data: SesionCajaCreate,
) -> SesionCaja:
    if _d(data.base_inicial) < 0:
        raise ValidationError("La base inicial no puede ser negativa")

    sesion = SesionCaja(
        id_usuario_creador=id_usuario,
        base_inicial=data.base_inicial,
        id_sucursal=data.id_sucursal,
        id_punto_venta=data.id_punto_venta,
        id_usuario_abre_caja=data.id_usuario_abre_caja,
    )
    db.add(sesion)
    await db.flush()

    if data.id_usuario_abre_caja is not None:
        hoy = hoy_local()
        result = await db.execute(
            select(TurnoCalendario).where(
                TurnoCalendario.id_sucursal == data.id_sucursal,
                TurnoCalendario.fecha == hoy,
                TurnoCalendario.estado_turno.in_(
                    [EstadoTurno.programado, EstadoTurno.activo]
                ),
                TurnoCalendario.id_sesion_caja.is_(None),
            )
        )
        turnos = result.scalars().all()
        turno = None
        for t in turnos:
            if beneficiario_turno(t) == data.id_usuario_abre_caja:
                turno = t
                break
        if turno is None:
            raise ValidationError(
                "El empleado seleccionado no tiene un turno programado para hoy"
            )
        turno.hora_apertura_real = datetime.utcnow()
        turno.id_sesion_caja = sesion.id_sesion_caja
        turno.estado_turno = EstadoTurno.activo

    return sesion


async def total_egresos_sesion(db: AsyncSession, id_sesion_caja: int) -> Decimal:
    result = await db.execute(
        select(func.coalesce(func.sum(Egreso.monto), 0)).where(
            Egreso.id_sesion_caja == id_sesion_caja
        )
    )
    return _d(result.scalar())


def efectivo_esperado(sesion: SesionCaja, egresos: Decimal) -> Decimal:
    """RN-03: base + ventas efectivo + abonos efectivo - devoluciones efectivo - egresos."""
    return (
        _d(sesion.base_inicial)
        + _d(sesion.ventas_efectivo)
        + _d(sesion.abonos_efectivo)
        - _d(sesion.devoluciones_efectivo)
        - _d(egresos)
    )


async def cerrar_sesion_caja(
    db: AsyncSession,
    sesion: SesionCaja,
    data: CierreCaja,
) -> SesionCaja:
    total_contado = Decimal("0")
    for item in data.arqueo:
        if item.cantidad < 0:
            raise ValidationError("Las cantidades del arqueo no pueden ser negativas")
        valor_denominacion = Decimal(str(DENOMINACIONES[item.denominacion.value]))
        subtotal = valor_denominacion * item.cantidad
        total_contado += subtotal

        db.add(
            CajaArqueo(
                id_sesion_caja=sesion.id_sesion_caja,
                denominacion=item.denominacion,
                cantidad=item.cantidad,
                subtotal=float(subtotal),
            )
        )

    total_egresos = await total_egresos_sesion(db, sesion.id_sesion_caja)
    esperado = efectivo_esperado(sesion, total_egresos)

    sesion.total_egresos = float(total_egresos)
    sesion.fecha_cierre = datetime.utcnow()
    sesion.efectivo_declarado_cierre = float(total_contado)
    # El descuadre sale del arqueo contado, nunca de un valor digitado aparte.
    sesion.descuadre = float(total_contado - esperado)
    sesion.estado = "cerrada"

    result = await db.execute(
        select(TurnoCalendario).where(
            TurnoCalendario.id_sesion_caja == sesion.id_sesion_caja
        )
    )
    turno = result.scalar_one_or_none()
    if turno is not None:
        turno.hora_cierre_real = datetime.utcnow()
        turno.estado_turno = EstadoTurno.finalizado

    return sesion
