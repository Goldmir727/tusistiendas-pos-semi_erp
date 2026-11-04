from datetime import datetime, timedelta
from hashlib import sha256

from fastapi import Header
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.exceptions import AuthenticationError, AuthorizationError
from app.models.usuario import Permiso, RolPermiso, Usuario
from app.schemas.usuario import UsuarioCreate

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_contrasena(password: str) -> str:
    return pwd_context.hash(password)


def verify_contrasena(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


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
    )
    db.add(usuario)
    await db.flush()
    return usuario
