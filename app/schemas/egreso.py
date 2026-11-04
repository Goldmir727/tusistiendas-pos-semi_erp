from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class EgresoCreate(BaseModel):
    id_sesion_caja: int
    id_sucursal: int
    categoria: str = "general"
    descripcion: str
    monto: float


class EgresoRead(BaseModel):
    id_egreso: int
    id_sesion_caja: int
    id_usuario: int
    categoria: str
    descripcion: str
    monto: float
    fecha: datetime

    model_config = {"from_attributes": True}