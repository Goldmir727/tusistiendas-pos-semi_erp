from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class VentaTemporalItem(BaseModel):
    id_producto: int | None = None
    nombre: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal


class VentaTemporalCreate(BaseModel):
    id_sesion_caja: int
    nombre: str
    id_cliente: int | None = None
    cliente_nombre: str | None = None
    items: list[dict[str, Any]] = []
    descripcion: str | None = None


class VentaTemporalUpdate(BaseModel):
    nombre: str | None = None
    items: list[dict[str, Any]] | None = None
    descripcion: str | None = None


class VentaTemporalRead(BaseModel):
    id_venta_temporal: str
    id_sesion_caja: int
    id_usuario_creador: int
    nombre: str
    id_cliente: int | None = None
    cliente_nombre: str | None = None
    items: list[dict[str, Any]] = []
    descripcion: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}