from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ClienteCreate(BaseModel):
    tipo_doc: str = "CC"
    numero_doc: str
    nombre: str
    email: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    regimen_fiscal: str | None = None


class ClienteUpdate(BaseModel):
    nombre: str | None = None
    email: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    regimen_fiscal: str | None = None
    activo: bool | None = None


class ClienteRead(BaseModel):
    id_cliente: int
    tipo_doc: str
    numero_doc: str
    nombre: str
    email: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    regimen_fiscal: str | None = None
    activo: bool
    created_at: datetime
    saldo_deudor: float = 0

    model_config = {"from_attributes": True}


class AbonoCreate(BaseModel):
    id_cliente: int
    id_venta: int | None = None
    monto: float
    metodo: Literal["efectivo", "transferencia"] = "efectivo"
    id_sesion_caja: int | None = None
    observacion: str | None = None


class AbonoRead(BaseModel):
    id_abono: int
    id_cliente: int
    id_venta: int | None = None
    monto: float
    tipo: str
    metodo: str = "efectivo"
    id_sesion_caja: int | None = None
    fecha: datetime
    observacion: str | None = None

    model_config = {"from_attributes": True}


class CuentaCliente(BaseModel):
    id_cliente: int
    nombre: str
    saldo_deudor: float
    ventas_pendientes: list[dict]
    abonos: list[AbonoRead]