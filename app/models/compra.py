from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Proveedor(Base):
    __tablename__ = "proveedores"

    id_proveedor: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(200))
    nit: Mapped[str] = mapped_column(String(20), unique=True)
    telefono: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(200))
    direccion: Mapped[str | None] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Compra(Base):
    __tablename__ = "compras"

    id_compra: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_proveedor: Mapped[int] = mapped_column(Integer, ForeignKey("proveedores.id_proveedor"), index=True)
    id_usuario: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id_usuario"))
    fecha_compra: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    observacion: Mapped[str | None] = mapped_column(String(500))

    id_sucursal: Mapped[int] = mapped_column(Integer, ForeignKey("sucursales.id_sucursal"), index=True)

    detalles: Mapped[list[CompraDetalle]] = relationship(back_populates="compra", cascade="all, delete-orphan")
    proveedor: Mapped[Proveedor] = relationship()


class CompraDetalle(Base):
    __tablename__ = "compra_detalle"

    id_detalle: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_compra: Mapped[int] = mapped_column(Integer, ForeignKey("compras.id_compra"), index=True)
    id_producto: Mapped[int] = mapped_column(Integer, ForeignKey("productos.id_producto"))
    cantidad: Mapped[float] = mapped_column(Numeric(12, 2))
    costo_unitario: Mapped[float] = mapped_column(Numeric(12, 2))
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2))

    compra: Mapped[Compra] = relationship(back_populates="detalles")
    producto: Mapped["Producto"] = relationship()