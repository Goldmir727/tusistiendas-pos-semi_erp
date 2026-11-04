from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EstadoVenta(str, enum.Enum):
    pendiente = "pendiente"
    pagada = "pagada"
    anulada = "anulada"
    contingencia = "contingencia"


class MetodoPago(str, enum.Enum):
    efectivo = "efectivo"
    transferencia = "transferencia"
    datafono = "datafono"
    fiado = "fiado"
    # Valores heredados: se conservan para poder leer filas antiguas.
    # No se ofrecen en la interfaz ni se aceptan en ventas nuevas.
    tarjeta = "tarjeta"
    nequi = "nequi"
    daviplata = "daviplata"
    pse = "pse"


MEDIOS_PAGO_VIGENTES = (
    MetodoPago.efectivo,
    MetodoPago.transferencia,
    MetodoPago.datafono,
    MetodoPago.fiado,
)


class MedioPago(Base):
    __tablename__ = "medios_pago"

    id_medio_pago: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(50))
    tipo: Mapped[MetodoPago] = mapped_column(Enum(MetodoPago, name="metodo_pago_enum"), unique=True)
    comision_porcentaje: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    requiere_qr: Mapped[bool] = mapped_column(default=False)
    requiere_referencia: Mapped[bool] = mapped_column(default=False)
    activo: Mapped[bool] = mapped_column(default=True)


class Venta(Base):
    __tablename__ = "ventas"
    __table_args__ = (
        UniqueConstraint("id_sucursal", "consecutivo", name="uq_ventas_sucursal_consecutivo"),
    )

    id_venta: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), default=uuid4, unique=True, index=True)
    consecutivo: Mapped[int] = mapped_column(Integer)
    id_sesion_caja: Mapped[int] = mapped_column(Integer, ForeignKey("sesiones_caja.id_sesion_caja"), index=True)
    id_usuario: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id_usuario"))
    id_cliente: Mapped[int | None] = mapped_column(Integer, ForeignKey("clientes.id_cliente"))
    fecha_venta: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    impuestos: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    descuento_total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    estado: Mapped[EstadoVenta] = mapped_column(Enum(EstadoVenta, name="estado_venta_enum"), default=EstadoVenta.pendiente)
    observacion: Mapped[str | None] = mapped_column(Text)
    es_fiado: Mapped[bool] = mapped_column(default=False)
    monto_abonado: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    monto_devuelto: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    origen: Mapped[str] = mapped_column(String(20), default="online")
    creado_offline_en: Mapped[datetime | None] = mapped_column(DateTime)

    id_sucursal: Mapped[int] = mapped_column(Integer, ForeignKey("sucursales.id_sucursal"), index=True)
    id_punto_venta: Mapped[int | None] = mapped_column(Integer, ForeignKey("puntos_venta.id_punto_venta"))

    detalles: Mapped[list[VentaDetalle]] = relationship(back_populates="venta", cascade="all, delete-orphan")
    pagos: Mapped[list[VentaPago]] = relationship(back_populates="venta", cascade="all, delete-orphan")
    comprobantes: Mapped[list["Comprobante"]] = relationship(back_populates="venta")


class VentaDetalle(Base):
    __tablename__ = "venta_detalle"

    id_detalle: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_venta: Mapped[int] = mapped_column(Integer, ForeignKey("ventas.id_venta"), index=True)
    id_producto: Mapped[int] = mapped_column(Integer, ForeignKey("productos.id_producto"))
    cantidad: Mapped[float] = mapped_column(Numeric(12, 2))
    precio_unitario: Mapped[float] = mapped_column(Numeric(12, 2))
    descuento: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    iva_porcentaje: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2))

    venta: Mapped[Venta] = relationship(back_populates="detalles")
    producto: Mapped["Producto"] = relationship()


class VentaPago(Base):
    __tablename__ = "venta_pago"

    id_pago_venta: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_venta: Mapped[int] = mapped_column(Integer, ForeignKey("ventas.id_venta"), index=True)
    id_medio_pago: Mapped[int] = mapped_column(Integer, ForeignKey("medios_pago.id_medio_pago"))
    monto: Mapped[float] = mapped_column(Numeric(12, 2))
    vuelto: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    referencia_manual: Mapped[str | None] = mapped_column(String(100))
    fecha_pago: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    venta: Mapped[Venta] = relationship(back_populates="pagos")
    medio_pago: Mapped[MedioPago] = relationship()
