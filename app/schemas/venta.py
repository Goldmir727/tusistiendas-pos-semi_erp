from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.venta import EstadoVenta


class VentaDetalleCreate(BaseModel):
    id_producto: int
    cantidad: Decimal = Field(gt=0)
    precio_unitario: Decimal | None = Field(default=None, ge=0)
    descuento: Decimal = Field(default=Decimal("0"), ge=0)
    iva_porcentaje: Decimal | None = Field(default=None, ge=0)


class VentaPagoCreate(BaseModel):
    id_medio_pago: int
    monto: Decimal = Field(gt=0)
    monto_recibido: Decimal | None = Field(default=None, ge=0)
    referencia_manual: str | None = None


class VentaCreate(BaseModel):
    uuid: UUID | None = None
    id_sesion_caja: int
    id_punto_venta: int | None = None
    id_cliente: int | None = None
    detalles: list[VentaDetalleCreate] = Field(min_length=1)
    pagos: list[VentaPagoCreate] = Field(default_factory=list)
    observacion: str | None = None
    origen: Literal["online", "offline"] = "online"
    creado_offline_en: datetime | None = None


class VentaDetalleRead(BaseModel):
    id_detalle: int
    id_producto: int
    cantidad: Decimal
    precio_unitario: Decimal
    descuento: Decimal
    iva_porcentaje: Decimal
    subtotal: Decimal

    model_config = {"from_attributes": True}


class VentaPagoRead(BaseModel):
    id_pago_venta: int
    id_medio_pago: int
    monto: Decimal
    vuelto: Decimal = Decimal("0")
    referencia_manual: str | None = None
    fecha_pago: datetime

    model_config = {"from_attributes": True}


class VentaRead(BaseModel):
    id_venta: int
    uuid: UUID
    consecutivo: int
    id_sesion_caja: int
    id_usuario: int
    id_cliente: int | None = None
    id_punto_venta: int | None = None
    fecha_venta: datetime
    subtotal: Decimal
    impuestos: Decimal
    descuento_total: Decimal
    total: Decimal
    estado: EstadoVenta
    es_fiado: bool = False
    monto_abonado: Decimal = Decimal("0")
    monto_devuelto: Decimal = Decimal("0")
    origen: str = "online"
    detalles: list[VentaDetalleRead] = []
    pagos: list[VentaPagoRead] = []

    model_config = {"from_attributes": True}
