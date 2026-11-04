from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Consecutivo(Base):
    """Contador por sucursal para números legibles de documentos (ventas, etc.)."""

    __tablename__ = "consecutivos"
    __table_args__ = (UniqueConstraint("nombre", "id_sucursal", name="uq_consecutivos_nombre_sucursal"),)

    id_consecutivo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(50))
    id_sucursal: Mapped[int] = mapped_column(Integer, ForeignKey("sucursales.id_sucursal"), index=True)
    ultimo: Mapped[int] = mapped_column(Integer, default=0)
