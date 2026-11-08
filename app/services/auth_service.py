from datetime import datetime, timedelta
from hashlib import sha256

import bcrypt
from fastapi import Header
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.exceptions import AuthenticationError, AuthorizationError
from app.models.usuario import Permiso, RolPermiso, Usuario
from app.schemas.usuario import UsuarioCreate

settings = get_settings()


def _bytes_contrasena(password: str) -> bytes:
    # bcrypt solo considera los primeros 72 bytes del secreto.
    return password.encode("utf-8")[:72]


def hash_contrasena(password: str) -> str:
    return bcrypt.hashpw(_bytes_contrasena(password), bcrypt.gensalt()).decode("utf-8")


def verify_contrasena(password: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(_bytes_contrasena(password), hashed.encode("utf-8"))
    except ValueError:
        return False


def hash_token(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def create_access_token(user_id: int, rol: str, expires_at: datetime) -> str:
    payload = {
        "sub": str(user_id),
        "rol": rol,
        "exp": expires_at,
        "type": "access",
        "iss": "pos-system",
        "aud": "pos-api",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int, expires_at: datetime) -> str:
    payload = {
        "sub": str(user_id),
        "exp": expires_at,
        "type": "refresh",
        "iss": "pos-system",
        "aud": "pos-api",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer="pos-system",
            audience="pos-api",
        )
    except JWTError:
        raise AuthenticationError("Token inválido o expirado")


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Token de autenticación requerido")
    return authorization.split(" ", 1)[1]


async def _load_user_from_token(token: str) -> Usuario:
    from app.database import async_session_factory

    payload = decode_token(token)
    async with async_session_factory() as db:
        result = await db.execute(select(Usuario).where(Usuario.id_usuario == int(payload["sub"])))
        user = result.scalar_one_or_none()
        if not user:
            raise AuthenticationError("Usuario no encontrado")
        if not user.activo:
            raise AuthenticationError("Usuario desactivado")
        return user


async def get_current_user(authorization: str | None = Header(None)) -> Usuario:
    token = _extract_bearer_token(authorization)
    return await _load_user_from_token(token)


async def get_current_admin(authorization: str | None = Header(None)) -> Usuario:
    from app.models.usuario import RolEnum

    user = await get_current_user(authorization)
    if user.rol != RolEnum.administrador:
        raise AuthorizationError("Se requiere rol de administrador")
    return user


async def get_current_cajero(authorization: str | None = Header(None)) -> Usuario:
    from app.models.usuario import RolEnum

    user = await get_current_user(authorization)
    if user.rol not in (RolEnum.cajero, RolEnum.administrador):
        raise AuthorizationError("Se requiere rol de caja")
    return user


async def get_current_empleado(authorization: str | None = Header(None)) -> Usuario:
    from app.models.usuario import RolEnum

    user = await get_current_user(authorization)
    if user.rol not in (RolEnum.empleado, RolEnum.administrador):
        raise AuthorizationError("Se requiere rol de empleado")
    return user


async def get_current_turnos_actor(authorization: str | None = Header(None)) -> Usuario:
    from app.models.usuario import RolEnum

    user = await get_current_user(authorization)
    if user.rol not in (RolEnum.cajero, RolEnum.empleado, RolEnum.administrador):
        raise AuthorizationError("No tiene permiso para acceder a turnos")
    return user


async def get_current_cajero(authorization: str | None = Header(None)) -> Usuario:
    from app.models.usuario import RolEnum

    user = await get_current_user(authorization)
    if user.rol not in (RolEnum.administrador, RolEnum.cajero):
        raise AuthorizationError("Se requiere rol de caja")
    return user


async def get_current_empleado(authorization: str | None = Header(None)) -> Usuario:
    from app.models.usuario import RolEnum

    user = await get_current_user(authorization)
    if user.rol not in (RolEnum.administrador, RolEnum.empleado):
        raise AuthorizationError("Se requiere rol de empleado")
    return user


async def get_current_user_optional(authorization: str | None = Header(None)) -> Usuario | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        token = _extract_bearer_token(authorization)
        return await _load_user_from_token(token)
    except AuthenticationError:
        return None


async def create_usuario(db: AsyncSession, data: UsuarioCreate) -> Usuario:
    usuario = Usuario(
        nombre_completo=data.nombre_completo,
        email=data.email,
        documento_identidad=data.documento_identidad,
        contrasena_hash=hash_contrasena(data.contrasena),
        rol=data.rol,
        telefono=data.telefono,
        banco_nombre=data.banco_nombre,
        banco_numero_cuenta=data.banco_numero_cuenta,
        id_sucursal=data.id_sucursal,
        id_punto_venta=data.id_punto_venta,
    )
    db.add(usuario)
    await db.flush()
    return usuario


def generar_codigo_verificacion() -> str:
    import secrets

    return f"{secrets.randbelow(1000000):06d}"


def hash_codigo(challenge_id: str, codigo: str) -> str:
    from hashlib import sha256

    return sha256(f"{challenge_id}:{codigo}".encode()).hexdigest()


def hash_codigo(challenge_id: str, codigo: str) -> str:
    return sha256(f"{challenge_id}:{codigo}".encode()).hexdigest()


def enmascarar_email(email: str) -> str:
    if "@" not in email:
        return "***"
    local, dominio = email.split("@", 1)
    if len(local) <= 1:
        return f"*@{dominio}"
    return f"{local[0]}{'*' * (len(local) - 1)}@{dominio}"
