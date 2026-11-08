from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VentaTemporal(Base):
    __tablename__ = "ventas_temporales"

    id_venta_temporal: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_sesion_caja: Mapped[int] = mapped_column(Integer, ForeignKey("sesiones_caja.id_sesion_caja"), index=True)
    id_usuario_creador: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id_usuario"), index=True)
    nombre: Mapped[str] = mapped_column(String(200))
    id_cliente: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cliente_nombre: Mapped[str | None] = mapped_column(String(200))
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    descripcion: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)