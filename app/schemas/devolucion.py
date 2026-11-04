from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.devolucion import EstadoDevolucion


class DevolucionDetalleCreate(BaseModel):
    id_producto: int
    cantidad: Decimal
    precio_unitario: Decimal
    iva_porcentaje: Decimal = Decimal("19")


class DevolucionCreate(BaseModel):
    id_venta: int
    motivo: str | None = None
    detalles: list[DevolucionDetalleCreate]


class DevolucionRead(BaseModel):
    id_devolucion: int
    id_venta: int
    id_usuario_solicita: int
    motivo: str | None = None
    monto: Decimal
    estado: EstadoDevolucion
    fecha: datetime
    detalles: list[dict] = []

    model_config = {"from_attributes": True}