from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class CodigoBarrasCreate(BaseModel):
    codigo_barras: str


class CodigoBarrasRead(BaseModel):
    id_codigo: int
    codigo_barras: str

    model_config = {"from_attributes": True}


class ProductoBase(BaseModel):
    nombre_producto: str
    precio_venta: Decimal
    costo_compra: Decimal
    stock_actual: Decimal = Decimal("0")
    stock_minimo_alerta: Decimal = Decimal("5")
    porcentaje_ganancia: Decimal | None = None
    iva_porcentaje: Decimal = Decimal("0")
    id_sucursal: int


class ProductoCreate(ProductoBase):
    codigos_barras: list[CodigoBarrasCreate] = []


class ProductoUpdate(BaseModel):
    nombre_producto: str | None = None
    precio_venta: Decimal | None = None
    costo_compra: Decimal | None = None
    stock_minimo_alerta: Decimal | None = None
    porcentaje_ganancia: Decimal | None = None
    iva_porcentaje: Decimal | None = None
    activo: bool | None = None


class ProductoRead(ProductoBase):
    id_producto: int
    activo: bool
    codigos_barras: list[CodigoBarrasRead] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class MovimientoStockCreate(BaseModel):
    id_producto: int
    tipo: str
    cantidad: Decimal
    costo_unitario: Decimal | None = None
    observacion: str | None = None
    id_sucursal: int
