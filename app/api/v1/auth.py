from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.exceptions import AuthenticationError
from app.models.usuario import SesionUsuario, Usuario
from app.schemas.auth import LoginRequest, RefreshTokenRequest, TokenPair
from app.services.auditoria_service import registrar_auditoria
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_token,
    verify_contrasena,
)

router = APIRouter()
settings = get_settings()

_login_attempts: dict[str, list[float]] = defaultdict(list)
_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 300


def _check_rate_limit(ip: str) -> None:
    now = time.time()
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < _LOCKOUT_SECONDS]
    if len(_login_attempts[ip]) >= _MAX_ATTEMPTS:
        raise AuthenticationError(
            f"Demasiados intentos fallidos. Intente de nuevo en {_LOCKOUT_SECONDS // 60} minutos"
        )


def _record_failed_attempt(ip: str) -> None:
    _login_attempts[ip].append(time.time())


def _clear_attempts(ip: str) -> None:
    _login_attempts.pop(ip, None)


@router.post("/login", response_model=TokenPair)
async def login(
    body: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPair:
    ip = request.client.host if request.client else "unknown"
    _check_rate_limit(ip)

    result = await db.execute(select(Usuario).where(Usuario.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_contrasena(body.contrasena, user.contrasena_hash):
        _record_failed_attempt(ip)
        raise AuthenticationError("Documento o contrasena invalidos")

    if not user.activo:
        raise AuthenticationError("Usuario desactivado")

    _clear_attempts(ip)

    now = datetime.utcnow()
    access_expires = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expires = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = create_access_token(user.id_usuario, user.rol.value, access_expires)
    refresh_token = create_refresh_token(user.id_usuario, refresh_expires)

    session = SesionUsuario(
        id_usuario=user.id_usuario,
        token_hash=hash_token(refresh_token),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        expira_en=refresh_expires,
    )
    db.add(session)

    await registrar_auditoria(
        db,
        "auth.login",
        f"Inicio de sesión de {user.email}",
        id_usuario=user.id_usuario,
        id_sucursal=user.id_sucursal,
        ip=ip,
    )

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(
    body: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPair:
    from jose import JWTError, jwt

    try:
        payload = jwt.decode(body.refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise AuthenticationError("Refresh token invalido")

    token_hash = hash_token(body.refresh_token)
    result = await db.execute(
        select(SesionUsuario).where(
            SesionUsuario.token_hash == token_hash,
            SesionUsuario.revocado_en.is_(None),
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise AuthenticationError("Sesion no encontrada o revocada")

    if session.expira_en < datetime.utcnow():
        raise AuthenticationError("Refresh token expirado")

    session.revocado_en = datetime.utcnow()

    result = await db.execute(select(Usuario).where(Usuario.id_usuario == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user or not user.activo:
        raise AuthenticationError("Usuario no valido")

    now = datetime.utcnow()
    access_expires = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expires = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    new_access = create_access_token(user.id_usuario, user.rol.value, access_expires)
    new_refresh = create_refresh_token(user.id_usuario, refresh_expires)

    new_session = SesionUsuario(
        id_usuario=user.id_usuario,
        token_hash=hash_token(new_refresh),
        ip_address=None,
        user_agent=None,
        expira_en=refresh_expires,
    )
    db.add(new_session)

    return TokenPair(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
async def logout(
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    result = await db.execute(
        select(SesionUsuario).where(
            SesionUsuario.id_usuario == current_user.id_usuario,
            SesionUsuario.revocado_en.is_(None),
        )
    )
    sessions = result.scalars().all()
    for s in sessions:
        s.revocado_en = datetime.utcnow()
    return {"message": "Sesiones cerradas"}
