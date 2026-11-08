from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EstadoCaja(str, enum.Enum):
    abierta = "abierta"
    cerrada = "cerrada"


class CajaArqueoDenominacion(str, enum.Enum):
    billete_50000 = "billete_50000"
    billete_20000 = "billete_20000"
    billete_10000 = "billete_10000"
    billete_5000 = "billete_5000"
    billete_2000 = "billete_2000"
    billete_1000 = "billete_1000"
    moneda_500 = "moneda_500"
    moneda_200 = "moneda_200"
    moneda_100 = "moneda_100"
    moneda_50 = "moneda_50"


class SesionCaja(Base):
    __tablename__ = "sesiones_caja"

    id_sesion_caja: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_usuario_creador: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id_usuario"), index=True)
    id_usuario_reemplazo: Mapped[int | None] = mapped_column(Integer, ForeignKey("usuarios.id_usuario"))
    id_usuario_abre_caja: Mapped[int | None] = mapped_column(Integer, ForeignKey("usuarios.id_usuario"), index=True)
    fecha_apertura: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fecha_cierre: Mapped[datetime | None] = mapped_column(DateTime)
    base_inicial: Mapped[float] = mapped_column(Numeric(12, 2))
    ventas_efectivo: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    ventas_digitales: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_tarjeta: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    # Movimientos que afectan el efectivo esperado además de las ventas (RN-03).
    abonos_efectivo: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    devoluciones_efectivo: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_egresos: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    efectivo_declarado_cierre: Mapped[float | None] = mapped_column(Numeric(12, 2))
    descuadre: Mapped[float | None] = mapped_column(Numeric(12, 2))
    estado: Mapped[EstadoCaja] = mapped_column(Enum(EstadoCaja, name="estado_caja_enum"), default=EstadoCaja.abierta)

    id_sucursal: Mapped[int] = mapped_column(Integer, ForeignKey("sucursales.id_sucursal"), index=True)
    id_punto_venta: Mapped[int] = mapped_column(Integer, ForeignKey("puntos_venta.id_punto_venta"))

    arqueo_detalles: Mapped[list[CajaArqueo]] = relationship(back_populates="sesion_caja", cascade="all, delete-orphan")


class CajaArqueo(Base):
    __tablename__ = "caja_arqueo"

    id_arqueo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_sesion_caja: Mapped[int] = mapped_column(Integer, ForeignKey("sesiones_caja.id_sesion_caja"), index=True)
    denominacion: Mapped[CajaArqueoDenominacion] = mapped_column(
        Enum(CajaArqueoDenominacion, name="denominacion_enum")
    )
    cantidad: Mapped[int] = mapped_column(Integer, default=0)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0)

    sesion_caja: Mapped[SesionCaja] = relationship(back_populates="arqueo_detalles")


class CorteDiario(Base):
    __tablename__ = "cortes_diarios"

    id_corte: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    id_usuario_cierre: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id_usuario"))
    total_ventas: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_efectivo: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_digital: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_tarjeta: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    descuadre_global: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    estado: Mapped[str] = mapped_column(String(20), default="abierto")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    id_sucursal: Mapped[int] = mapped_column(Integer, ForeignKey("sucursales.id_sucursal"), index=True)
