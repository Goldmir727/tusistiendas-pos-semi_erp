from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AbonoCliente(Base):
    __tablename__ = "abonos_cliente"

    id_abono: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_cliente: Mapped[int] = mapped_column(Integer, ForeignKey("clientes.id_cliente"), index=True)
    id_venta: Mapped[int | None] = mapped_column(Integer, ForeignKey("ventas.id_venta"))
    id_usuario: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id_usuario"))
    monto: Mapped[float] = mapped_column(Numeric(12, 2))
    tipo: Mapped[str] = mapped_column(String(20), default="abono")
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    observacion: Mapped[str | None] = mapped_column(String(300))

    venta: Mapped["Venta | None"] = relationship()