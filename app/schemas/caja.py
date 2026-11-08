from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.caja import CajaArqueoDenominacion, EstadoCaja


class SesionCajaCreate(BaseModel):
    base_inicial: Decimal
    id_sucursal: int
    id_punto_venta: int
    id_usuario_abre_caja: int | None = None


class CajaArqueoItem(BaseModel):
    denominacion: CajaArqueoDenominacion
    cantidad: int


class CierreCaja(BaseModel):
    # El valor contado sale del arqueo; el campo se acepta por compatibilidad.
    efectivo_declarado: Decimal | None = None
    arqueo: list[CajaArqueoItem]


class SesionCajaRead(BaseModel):
    id_sesion_caja: int
    id_usuario_creador: int
    id_usuario_reemplazo: int | None = None
    id_usuario_abre_caja: int | None = None
    fecha_apertura: datetime
    fecha_cierre: datetime | None = None
    base_inicial: Decimal
    ventas_efectivo: Decimal
    ventas_digitales: Decimal
    total_tarjeta: Decimal
    abonos_efectivo: Decimal = Decimal("0")
    devoluciones_efectivo: Decimal = Decimal("0")
    total_egresos: Decimal = Decimal("0")
    efectivo_declarado_cierre: Decimal | None = None
    descuadre: Decimal | None = None
    estado: EstadoCaja
    id_sucursal: int
    id_punto_venta: int

    model_config = {"from_attributes": True}


class CajaDoblePanel(BaseModel):
    ventas_brutas_turno: Decimal
    efectivo_real_esperado: Decimal
    base_inicial: Decimal
    ventas_efectivo_acumulado: Decimal
    abonos_efectivo: Decimal = Decimal("0")
    devoluciones_efectivo: Decimal = Decimal("0")
    egresos: Decimal = Decimal("0")


class CorteDiarioRead(BaseModel):
    id_corte: int
    fecha: date
    total_ventas: Decimal
    total_efectivo: Decimal
    total_digital: Decimal
    total_tarjeta: Decimal
    descuadre_global: Decimal
    estado: str

    model_config = {"from_attributes": True}
