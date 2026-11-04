from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import CashDrawerError, NotFoundError
from app.models.caja import CajaArqueo, SesionCaja
from app.models.egreso import Egreso
from app.schemas.caja import CajaArqueoItem, CierreCaja, SesionCajaCreate


async def abrir_sesion_caja(
    db: AsyncSession,
    id_usuario: int,
    data: SesionCajaCreate,
) -> SesionCaja:
    sesion = SesionCaja(
        id_usuario_creador=id_usuario,
        base_inicial=data.base_inicial,
        id_sucursal=data.id_sucursal,
        id_punto_venta=data.id_punto_venta,
    )
    db.add(sesion)
    await db.flush()
    return sesion


async def cerrar_sesion_caja(
    db: AsyncSession,
    sesion: SesionCaja,
    data: CierreCaja,
) -> SesionCaja:
    denominacion_values = {
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

    total_contado = Decimal("0")
    for item in data.arqueo:
        valor_denominacion = Decimal(str(denominacion_values[item.denominacion.value]))
        subtotal = valor_denominacion * item.cantidad
        total_contado += subtotal

        arqueo = CajaArqueo(
            id_sesion_caja=sesion.id_sesion_caja,
            denominacion=item.denominacion,
            cantidad=item.cantidad,
            subtotal=float(subtotal),
        )
        db.add(arqueo)

    total_egresos = Decimal("0")
    result_egresos = await db.execute(
        select(func.coalesce(func.sum(Egreso.monto), 0)).where(
            Egreso.id_sesion_caja == sesion.id_sesion_caja
        )
    )
    total_egresos = Decimal(str(result_egresos.scalar() or 0))

    efectivo_esperado = (Decimal(str(sesion.base_inicial)) + Decimal(str(sesion.ventas_efectivo))) - total_egresos
    # El descuadre sale del arqueo contado, no de un valor digitado aparte.
    descuadre = float(total_contado - efectivo_esperado)

    sesion.fecha_cierre = datetime.utcnow()
    sesion.efectivo_declarado_cierre = float(total_contado)
    sesion.descuadre = descuadre
    sesion.estado = "cerrada"

    return sesion
