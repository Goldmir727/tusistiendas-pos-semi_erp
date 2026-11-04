from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auditoria import LogAuditoria


async def registrar_auditoria(
    db: AsyncSession,
    tipo_evento: str,
    descripcion: str,
    *,
    id_usuario: int | None = None,
    id_sucursal: int | None = None,
    datos: dict[str, Any] | None = None,
    ip: str | None = None,
) -> LogAuditoria:
    """Registra una acción crítica (RNF-11). No hace commit: lo hace la petición."""
    log = LogAuditoria(
        tipo_evento=tipo_evento[:50],
        descripcion=descripcion[:1000],
        datos_extra=json.dumps(datos, default=str, ensure_ascii=False) if datos else None,
        id_usuario_afectado=id_usuario,
        id_sucursal=id_sucursal,
        ip_address=ip[:45] if ip else None,
    )
    db.add(log)
    return log
