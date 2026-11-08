from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.pago import MetodoPagoSueldo


class PagoTurnoDetalleRead(BaseModel):
    id_detalle: int
    id_turno: int
    monto_liquidado_turno: Decimal

    model_config = {"from_attributes": True}


class PagoCreate(BaseModel):
    id_usuario_receptor: int
    metodo_pago: MetodoPagoSueldo
    turnos_ids: list[int]


class PagoRead(BaseModel):
    id_pago: int
    id_usuario_receptor: int
    id_administrador_pagador: int
    fecha_pago: datetime
    metodo_pago: MetodoPagoSueldo
    monto_total: Decimal
    recibido_empleado: bool = False
    fecha_recibido: datetime | None = None
    detalles: list[PagoTurnoDetalleRead] = []

    model_config = {"from_attributes": True}
