from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    contrasena: str
    device_token: str | None = None
    recordar_dispositivo: bool = False


class TwoFactorChallenge(BaseModel):
    requires_2fa: bool = True
    challenge_id: str
    email_masked: str
    expires_in: int
    dev_code: str | None = None


class Verify2FARequest(BaseModel):
    challenge_id: str
    codigo: str
    recordar_dispositivo: bool = False
    nombre_dispositivo: str | None = None


class DispositivoConfiableRead(BaseModel):
    id_dispositivo: int
    nombre: str | None = None
    user_agent: str | None = None
    ip: str | None = None
    creado_en: datetime
    ultimo_uso: datetime | None = None
    expira_en: datetime
    actual: bool = False

    model_config = {"from_attributes": True}


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    device_token: str | None = None
    device_trusted: bool = False


class TokenPayload(BaseModel):
    sub: int
    rol: str
    exp: datetime
    type: str = "access"


class RefreshTokenRequest(BaseModel):
    refresh_token: str