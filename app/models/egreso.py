from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Egreso(Base):
    __tablename__ = "egresos"

    id_egreso: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_sesion_caja: Mapped[int] = mapped_column(Integer, ForeignKey("sesiones_caja.id_sesion_caja"), index=True)
    id_usuario: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id_usuario"))
    categoria: Mapped[str] = mapped_column(String(50), default="general")
    descripcion: Mapped[str] = mapped_column(String(300))
    monto: Mapped[float] = mapped_column(Numeric(12, 2))
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    id_sucursal: Mapped[int] = mapped_column(Integer, ForeignKey("sucursales.id_sucursal"), index=True)