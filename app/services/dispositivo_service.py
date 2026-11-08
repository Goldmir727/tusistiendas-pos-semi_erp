from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.exceptions import AuthenticationError, AuthorizationError, NotFoundError
from app.models.usuario import CodigoVerificacion, DispositivoConfiable, Usuario
from app.services.auth_service import hash_token

settings = get_settings()


async def crear_dispositivo_confiable(
    db: AsyncSession,
    id_usuario: int,
    nombre: str | None,
    user_agent: str | None,
    ip: str | None,
) -> tuple[DispositivoConfiable, str]:
    raw_token = secrets.token_urlsafe(48)
    token_hash = hash_token(raw_token)
    ahora = datetime.utcnow()
    dispositivo = DispositivoConfiable(
        id_usuario=id_usuario,
        token_hash=token_hash,
        nombre=nombre or "Dispositivo",
        user_agent=user_agent,
        ip=ip,
        creado_en=ahora,
        ultimo_uso=ahora,
        expira_en=ahora + timedelta(days=settings.DEVICE_TRUST_DAYS),
    )
    db.add(dispositivo)
    await db.flush()
    return dispositivo, raw_token


async def validar_dispositivo_confiable(
    db: AsyncSession, id_usuario: int, raw_token: str | None
) -> DispositivoConfiable | None:
    if not raw_token:
        return None
    token_hash = hash_token(raw_token)
    result = await db.execute(
        select(DispositivoConfiable).where(
            DispositivoConfiable.token_hash == token_hash,
            DispositivoConfiable.id_usuario == id_usuario,
            DispositivoConfiable.revocado_en.is_(None),
        )
    )
    dispositivo = result.scalar_one_or_none()
    if dispositivo is None:
        return None
    ahora = datetime.utcnow()
    if dispositivo.expira_en < ahora:
        return None
    dispositivo.ultimo_uso = ahora
    dispositivo.expira_en = ahora + timedelta(days=settings.DEVICE_TRUST_DAYS)
    return dispositivo


async def listar_dispositivos(
    db: AsyncSession, id_usuario: int
) -> list[DispositivoConfiable]:
    result = await db.execute(
        select(DispositivoConfiable).where(
            DispositivoConfiable.id_usuario == id_usuario,
            DispositivoConfiable.revocado_en.is_(None),
        )
    )
    ahora = datetime.utcnow()
    return [d for d in result.scalars().all() if d.expira_en >= ahora]


async def revocar_dispositivo(
    db: AsyncSession, id_usuario: int, id_dispositivo: int, es_admin: bool
) -> None:
    result = await db.execute(
        select(DispositivoConfiable).where(
            DispositivoConfiable.id_dispositivo == id_dispositivo
        )
    )
    dispositivo = result.scalar_one_or_none()
    if dispositivo is None:
        raise NotFoundError("Dispositivo", id_dispositivo)
    if not es_admin and dispositivo.id_usuario != id_usuario:
        raise AuthorizationError("No tiene permiso para revocar este dispositivo")
    dispositivo.revocado_en = datetime.utcnow()


async def crear_codigo_verificacion(
    db: AsyncSession, id_usuario: int, minutos: int
) -> tuple[CodigoVerificacion, str, str]:
    import uuid

    import uuid

    challenge_id = uuid.uuid4().hex
    codigo = generar_codigo()
    challenge_hash = hash_token(challenge_id)
    from app.services.auth_service import hash_codigo

    codigo_hash = hash_codigo(challenge_id, codigo)
    ahora = datetime.utcnow()
    registro = CodigoVerificacion(
        id_usuario=id_usuario,
        codigo_hash=codigo_hash,
        challenge_hash=challenge_hash,
        expira_en=ahora + timedelta(minutes=minutos),
        creado_en=ahora,
        ultimo_envio=ahora,
    )
    db.add(registro)
    await db.flush()
    return registro, challenge_id, codigo


def generar_codigo() -> str:
    import secrets

    return f"{secrets.randbelow(1000000):06d}"


async def verificar_codigo(
    db: AsyncSession, challenge_id: str, codigo: str
) -> int:
    from app.services.auth_service import hash_codigo

    challenge_hash = hash_token(challenge_id)
    result = await db.execute(
        select(CodigoVerificacion).where(
            CodigoVerificacion.challenge_hash == challenge_hash
        )
    )
    registro = result.scalar_one_or_none()
    if registro is None:
        raise AuthenticationError("Desafio de verificacion invalido")
    ahora = datetime.utcnow()
    if registro.usado:
        raise AuthenticationError("El codigo ya fue usado")
    if registro.expira_en < ahora:
        raise AuthenticationError("El codigo ha expirado")
    if registro.intentos >= 5:
        raise AuthenticationError("Demasiados intentos fallidos")
    registro.intentos += 1
    if registro.codigo_hash != hash_codigo(challenge_id, codigo):
        raise AuthenticationError("Codigo incorrecto")
    registro.usado = True
    return registro.id_usuario


async def reenviar_codigo(db: AsyncSession, challenge_id: str) -> str:
    from app.services.auth_service import generar_codigo_verificacion, hash_codigo

    challenge_hash = hash_token(challenge_id)
    result = await db.execute(
        select(CodigoVerificacion).where(
            CodigoVerificacion.challenge_hash == challenge_hash
        )
    )
    registro = result.scalar_one_or_none()
    if registro is None:
        raise AuthenticationError("Desafio de verificacion invalido")
    ahora = datetime.utcnow()
    if registro.usado:
        raise AuthenticationError("El codigo ya fue usado")
    if registro.expira_en < ahora:
        raise AuthenticationError("El codigo ha expirado")
    if registro.reenvios >= 3:
        raise AuthenticationError("Demasiados reenvios")
    nuevo_codigo = generar_codigo_verificacion()
    registro.codigo_hash = hash_codigo(challenge_id, nuevo_codigo)
    registro.reenvios += 1
    registro.intentos = 0
    registro.ultimo_envio = ahora
    registro.expira_en = ahora + timedelta(minutes=settings.AUTH_2FA_CODE_MINUTES)
    return nuevo_codigo