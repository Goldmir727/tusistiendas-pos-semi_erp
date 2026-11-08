from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EstadoDevolucion(str, enum.Enum):
    pendiente_aprobacion = "pendiente_aprobacion"
    aprobada = "aprobada"
    rechazada = "rechazada"


class Devolucion(Base):
    __tablename__ = "devoluciones"

    id_devolucion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_venta: Mapped[int] = mapped_column(Integer, ForeignKey("ventas.id_venta"), index=True)
    id_usuario_solicita: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id_usuario"))
    id_usuario_aprueba: Mapped[int | None] = mapped_column(Integer, ForeignKey("usuarios.id_usuario"))
    motivo: Mapped[str | None] = mapped_column(String(500))
    monto: Mapped[float] = mapped_column(Numeric(12, 2))
    # efectivo | transferencia | nota_credito. Solo el efectivo sale de la caja.
    metodo_reembolso: Mapped[str] = mapped_column(String(20), default="efectivo")
    estado: Mapped[EstadoDevolucion] = mapped_column(
        Enum(EstadoDevolucion, name="estado_devolucion_enum"),
        default=EstadoDevolucion.pendiente_aprobacion,
    )
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    id_sucursal: Mapped[int] = mapped_column(Integer, ForeignKey("sucursales.id_sucursal"), index=True)

    detalles: Mapped[list[DevolucionDetalle]] = relationship(back_populates="devolucion", cascade="all, delete-orphan")
    venta: Mapped["Venta"] = relationship()


class DevolucionDetalle(Base):
    __tablename__ = "devolucion_detalle"

    id_detalle: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_devolucion: Mapped[int] = mapped_column(Integer, ForeignKey("devoluciones.id_devolucion"), index=True)
    id_producto: Mapped[int] = mapped_column(Integer, ForeignKey("productos.id_producto"))
    cantidad: Mapped[float] = mapped_column(Numeric(12, 2))
    precio_unitario: Mapped[float] = mapped_column(Numeric(12, 2))
    iva_porcentaje: Mapped[float] = mapped_column(Numeric(5, 2), default=19.0)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2))

    devolucion: Mapped[Devolucion] = relationship(back_populates="detalles")
    producto: Mapped["Producto"] = relationship()