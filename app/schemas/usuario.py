from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.usuario import RolEnum


class UsuarioBase(BaseModel):
    nombre_completo: str
    email: str
    documento_identidad: str
    rol: RolEnum
    telefono: str | None = None
    banco_nombre: str | None = None
    banco_numero_cuenta: str | None = None
    id_sucursal: int | None = None


class UsuarioCreate(UsuarioBase):
    contrasena: str


class UsuarioUpdate(BaseModel):
    nombre_completo: str | None = None
    email: str | None = None
    telefono: str | None = None
    banco_nombre: str | None = None
    banco_numero_cuenta: str | None = None
    activo: bool | None = None
    id_sucursal: int | None = None


class UsuarioRead(UsuarioBase):
    id_usuario: int
    activo: bool
    created_at: datetime

    model_config = {"from_attributes": True}
