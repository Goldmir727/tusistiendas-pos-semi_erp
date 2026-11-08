from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.models.devolucion import EstadoDevolucion


class DevolucionDetalleCreate(BaseModel):
    # El precio y el IVA se toman de la venta original, no del cliente.
    id_producto: int
    cantidad: Decimal = Field(gt=0)


class DevolucionCreate(BaseModel):
    id_venta: int
    motivo: str | None = None
    metodo_reembolso: Literal["efectivo", "transferencia", "nota_credito"] = "efectivo"
    detalles: list[DevolucionDetalleCreate] = Field(min_length=1)


class DevolucionRead(BaseModel):
    id_devolucion: int
    id_venta: int
    id_usuario_solicita: int
    id_usuario_aprueba: int | None = None
    motivo: str | None = None
    monto: Decimal
    metodo_reembolso: str = "efectivo"
    estado: EstadoDevolucion
    fecha: datetime
    detalles: list[dict] = []

    model_config = {"from_attributes": True}
