from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.models.caja import EstadoCaja, SesionCaja
from app.models.venta_temporal import VentaTemporal


async def _sesion_abierta(db: AsyncSession, id_sesion_caja: int) -> SesionCaja:
    result = await db.execute(
        select(SesionCaja).where(SesionCaja.id_sesion_caja == id_sesion_caja)
    )
    sesion = result.scalar_one_or_none()
    if sesion is None:
        raise NotFoundError("SesionCaja", id_sesion_caja)
    if sesion.estado != EstadoCaja.abierta:
        raise ValidationError("La caja no está abierta")
    return sesion


async def listar_temporales(db: AsyncSession, id_sesion_caja: int) -> list[VentaTemporal]:
    result = await db.execute(
        select(VentaTemporal)
        .where(VentaTemporal.id_sesion_caja == id_sesion_caja)
        .order_by(VentaTemporal.updated_at.desc())
    )
    return list(result.scalars().all())


async def crear_temporal(
    db: AsyncSession,
    id_sesion_caja: int,
    id_usuario: int,
    nombre: str,
    items: list[dict],
    descripcion: str | None,
    id_cliente: int | None = None,
    cliente_nombre: str | None = None,
) -> VentaTemporal:
    sesion = await _sesion_abierta(db, id_sesion_caja)
    temporal = VentaTemporal(
        id_venta_temporal=str(uuid4()),
        id_sesion_caja=id_sesion_caja,
        id_usuario_creador=id_usuario,
        nombre=nombre,
        id_cliente=id_cliente,
        cliente_nombre=cliente_nombre,
        items=items,
        descripcion=descripcion,
    )
    db.add(temporal)
    await db.flush()
    return temporal


async def actualizar_temporal(
    db: AsyncSession,
    id_venta_temporal: str,
    id_usuario: int,
    es_admin: bool,
    puede_editar: bool,
    nombre: str | None,
    items: list[dict] | None,
    descripcion: str | None,
) -> VentaTemporal:
    result = await db.execute(
        select(VentaTemporal).where(VentaTemporal.id_venta_temporal == id_venta_temporal)
    )
    temporal = result.scalar_one_or_none()
    if temporal is None:
        raise NotFoundError("VentaTemporal", id_venta_temporal)

    sesion_result = await db.execute(
        select(SesionCaja).where(SesionCaja.id_sesion_caja == temporal.id_sesion_caja)
    )
    sesion = sesion_result.scalar_one_or_none()
    if sesion is None or sesion.estado != EstadoCaja.abierta:
        raise ValidationError("La caja no está abierta")

    if not (es_admin or puede_editar):
        raise AuthorizationError("No tiene permiso para editar esta venta temporal")

    if nombre is not None:
        temporal.nombre = nombre
    if items is not None:
        temporal.items = items
    if descripcion is not None:
        temporal.descripcion = descripcion
    await db.flush()
    return temporal


async def eliminar_temporal(db: AsyncSession, id_venta_temporal: str) -> None:
    result = await db.execute(
        select(VentaTemporal).where(VentaTemporal.id_venta_temporal == id_venta_temporal)
    )
    temporal = result.scalar_one_or_none()
    if temporal is None:
        raise NotFoundError("VentaTemporal", id_venta_temporal)
    await db.delete(temporal)
    await db.flush()