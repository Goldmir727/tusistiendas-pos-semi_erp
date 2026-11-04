from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ProveedorCreate(BaseModel):
    nombre: str
    nit: str
    telefono: str | None = None
    email: str | None = None
    direccion: str | None = None


class ProveedorRead(BaseModel):
    id_proveedor: int
    nombre: str
    nit: str
    telefono: str | None = None
    email: str | None = None
    direccion: str | None = None
    activo: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CompraDetalleCreate(BaseModel):
    id_producto: int
    cantidad: Decimal
    costo_unitario: Decimal


class CompraCreate(BaseModel):
    id_proveedor: int
    id_sucursal: int
    detalles: list[CompraDetalleCreate]
    observacion: str | None = None


class CompraDetalleRead(BaseModel):
    id_detalle: int
    id_producto: int
    cantidad: Decimal
    costo_unitario: Decimal
    subtotal: Decimal

    model_config = {"from_attributes": True}


class CompraRead(BaseModel):
    id_compra: int
    id_proveedor: int
    fecha_compra: datetime
    total: Decimal
    observacion: str | None = None
    detalles: list[CompraDetalleRead] = []

    model_config = {"from_attributes": True}