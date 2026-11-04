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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TipoMovimiento(str, enum.Enum):
    entrada = "entrada"
    salida = "salida"
    ajuste = "ajuste"
    merma = "merma"
    devolucion = "devolucion"


class Producto(Base):
    __tablename__ = "productos"

    id_producto: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre_producto: Mapped[str] = mapped_column(String(200))
    precio_venta: Mapped[float] = mapped_column(Numeric(12, 2))
    costo_compra: Mapped[float] = mapped_column(Numeric(12, 2))
    stock_actual: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    stock_minimo_alerta: Mapped[float] = mapped_column(Numeric(12, 2), default=5)
    porcentaje_ganancia: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    iva_porcentaje: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    activo: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    id_sucursal: Mapped[int] = mapped_column(Integer, ForeignKey("sucursales.id_sucursal"), index=True)

    codigos_barras: Mapped[list[CodigoBarras]] = relationship(back_populates="producto", cascade="all, delete-orphan")
    movimientos: Mapped[list[MovimientoStock]] = relationship(back_populates="producto")


class CodigoBarras(Base):
    __tablename__ = "codigos_barras"
    __table_args__ = (UniqueConstraint("codigo_barras", name="uq_codigo_barras_codigo"),)

    id_codigo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_producto: Mapped[int] = mapped_column(Integer, ForeignKey("productos.id_producto"), index=True)
    codigo_barras: Mapped[str] = mapped_column(String(100))

    producto: Mapped[Producto] = relationship(back_populates="codigos_barras")


class MovimientoStock(Base):
    __tablename__ = "movimientos_stock"

    id_movimiento: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_producto: Mapped[int] = mapped_column(Integer, ForeignKey("productos.id_producto"), index=True)
    tipo: Mapped[TipoMovimiento] = mapped_column(Enum(TipoMovimiento, name="tipo_movimiento_enum"))
    cantidad: Mapped[float] = mapped_column(Numeric(12, 2))
    costo_unitario: Mapped[float | None] = mapped_column(Numeric(12, 2))
    id_referencia: Mapped[int | None] = mapped_column(Integer)
    tabla_referencia: Mapped[str | None] = mapped_column(String(50))
    observacion: Mapped[str | None] = mapped_column(Text)
    id_usuario: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id_usuario"))
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    id_sucursal: Mapped[int] = mapped_column(Integer, ForeignKey("sucursales.id_sucursal"), index=True)

    producto: Mapped[Producto] = relationship(back_populates="movimientos")
