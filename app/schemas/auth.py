from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    contrasena: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    sub: int
    rol: str
    exp: datetime
    type: str = "access"


class RefreshTokenRequest(BaseModel):
    refresh_token: str
