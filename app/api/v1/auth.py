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
from app.models.usuario import CodigoVerificacion, DispositivoConfiable, SesionUsuario, Usuario
from app.schemas.auth import (
    DispositivoConfiableRead,
    LoginRequest,
    RefreshTokenRequest,
    TokenPair,
    TwoFactorChallenge,
    Verify2FARequest,
)
from app.services.auditoria_service import registrar_auditoria
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    enmascarar_email,
    get_current_user,
    hash_token,
    verify_contrasena,
)
from app.services.dispositivo_service import (
    crear_codigo_verificacion,
    crear_dispositivo_confiable,
    listar_dispositivos,
    reenviar_codigo,
    revocar_dispositivo,
    validar_dispositivo_confiable,
    verificar_codigo,
)
from app.services.email_service import enviar_codigo_verificacion

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


@router.post("/login", response_model=None)
async def login(
    body: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
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

    dispositivo = await validar_dispositivo_confiable(
        db, user.id_usuario, body.device_token
    )

    if not settings.AUTH_2FA_ENABLED or not user.auth_2fa_habilitado or dispositivo is not None:
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

        device_token_out = body.device_token if dispositivo is not None else None
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            device_token=device_token_out,
            device_trusted=dispositivo is not None,
        )

    # Requiere 2FA
    registro, challenge_id, codigo = await crear_codigo_verificacion(
        db, user.id_usuario, settings.AUTH_2FA_CODE_MINUTES
    )
    await enviar_codigo_verificacion(user.email, codigo, settings.AUTH_2FA_CODE_MINUTES)

    await registrar_auditoria(
        db,
        "auth.2fa_required",
        f"2FA requerido para {user.email}",
        id_usuario=user.id_usuario,
        id_sucursal=user.id_sucursal,
        ip=ip,
    )

    from fastapi.responses import JSONResponse

    payload = {
        "requires_2fa": True,
        "challenge_id": challenge_id,
        "email_masked": enmascarar_email(user.email),
        "expires_in": settings.AUTH_2FA_CODE_MINUTES * 60,
    }
    if settings.AUTH_2FA_DEV_MODE or not settings.SMTP_HOST:
        payload["dev_code"] = codigo
    return JSONResponse(status_code=202, content=payload)


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


@router.post("/verificar-2fa", response_model=TokenPair)
async def verificar_2fa(
    body: Verify2FARequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPair:
    ip = request.client.host if request.client else "unknown"
    id_usuario = await verificar_codigo(db, body.challenge_id, body.codigo)

    result = await db.execute(select(Usuario).where(Usuario.id_usuario == id_usuario))
    user = result.scalar_one_or_none()
    if not user or not user.activo:
        raise AuthenticationError("Usuario no valido")

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

    device_token_out: str | None = None
    if body.recordar_dispositivo:
        dispositivo, raw_token = await crear_dispositivo_confiable(
            db,
            user.id_usuario,
            body.nombre_dispositivo,
            request.headers.get("user-agent"),
            ip,
        )
        device_token_out = raw_token

    await registrar_auditoria(
        db,
        "auth.2fa_ok",
        f"2FA verificado para {user.email}",
        id_usuario=user.id_usuario,
        id_sucursal=user.id_sucursal,
        ip=ip,
    )

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        device_token=device_token_out,
        device_trusted=body.recordar_dispositivo,
    )


@router.post("/reenviar-codigo", response_model=None)
async def reenviar_codigo_endpoint(
    body: dict,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from fastapi.responses import JSONResponse

    challenge_id = body.get("challenge_id")
    if not challenge_id:
        raise AuthenticationError("challenge_id requerido")
    nuevo_codigo = await reenviar_codigo(db, challenge_id)

    # Obtener el usuario asociado al challenge para enmascarar email
    from sqlalchemy import select as _select

    challenge_hash = hash_token(challenge_id)
    result = await db.execute(
        _select(CodigoVerificacion).where(CodigoVerificacion.challenge_hash == challenge_hash)
    )
    registro = result.scalar_one_or_none()
    email_masked = ""
    if registro:
        u = await db.execute(select(Usuario).where(Usuario.id_usuario == registro.id_usuario))
        usr = u.scalar_one_or_none()
        if usr:
            email_masked = enmascarar_email(usr.email)

    payload = {
        "requires_2fa": True,
        "challenge_id": challenge_id,
        "email_masked": email_masked,
        "expires_in": settings.AUTH_2FA_CODE_MINUTES * 60,
    }
    if settings.AUTH_2FA_DEV_MODE or not settings.SMTP_HOST:
        payload["dev_code"] = nuevo_codigo
    return JSONResponse(status_code=202, content=payload)


@router.get("/dispositivos", response_model=None)
async def list_dispositivos(
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    dispositivos = await listar_dispositivos(db, current_user.id_usuario)
    return [
        DispositivoConfiableRead.model_validate(d).model_copy(
            update={"actual": False}
        )
        for d in dispositivos
    ]


@router.delete("/dispositivos/{id_dispositivo}", response_model=None)
async def revoke_dispositivo(
    id_dispositivo: int,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    es_admin = current_user.rol.value == "administrador"
    await revocar_dispositivo(db, current_user.id_usuario, id_dispositivo, es_admin)
    await db.commit()
    return {"message": "Dispositivo revocado"}


@router.patch("/2fa", response_model=None)
async def toggle_2fa(
    body: dict,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    habilitado = bool(body.get("habilitado", False))
    current_user.auth_2fa_habilitado = habilitado
    # Si se desactiva, revocar todos los dispositivos confiables
    if not habilitado:
        result = await db.execute(
            select(DispositivoConfiable).where(
                DispositivoConfiable.id_usuario == current_user.id_usuario,
                DispositivoConfiable.revocado_en.is_(None),
            )
        )
        for d in result.scalars().all():
            d.revocado_en = datetime.utcnow()
    await db.commit()
    await registrar_auditoria(
        db,
        "auth.2fa_toggle",
        f"2FA {'activado' if habilitado else 'desactivado'} para {current_user.email}",
        id_usuario=current_user.id_usuario,
        id_sucursal=current_user.id_sucursal,
    )
    return {"habilitado": habilitado, "message": "2FA actualizado"}


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
