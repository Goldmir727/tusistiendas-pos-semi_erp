from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MetodoPagoSueldo(str, enum.Enum):
    efectivo = "efectivo"
    transferencia = "transferencia"


class PagoSueldo(Base):
    __tablename__ = "pagos_sueldos"

    id_pago: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_usuario_receptor: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id_usuario"), index=True)
    id_administrador_pagador: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id_usuario"))
    fecha_pago: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    metodo_pago: Mapped[MetodoPagoSueldo] = mapped_column(
        Enum(MetodoPagoSueldo, name="metodo_pago_sueldo_enum")
    )
    monto_total: Mapped[float] = mapped_column(Numeric(12, 2))
    observacion: Mapped[str | None] = mapped_column(String(500))
    recibido_empleado: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_recibido: Mapped[datetime | None] = mapped_column(DateTime)

    detalles: Mapped[list[PagoTurnoDetalle]] = relationship(back_populates="pago", cascade="all, delete-orphan")
    receptor: Mapped["Usuario"] = relationship(foreign_keys=[id_usuario_receptor])
    pagador: Mapped["Usuario"] = relationship(foreign_keys=[id_administrador_pagador])


class PagoTurnoDetalle(Base):
    __tablename__ = "pago_turno_detalle"

    id_detalle: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_pago: Mapped[int] = mapped_column(Integer, ForeignKey("pagos_sueldos.id_pago"), index=True)
    id_turno: Mapped[int] = mapped_column(Integer, ForeignKey("turnos_calendario.id_turno"))
    monto_liquidado_turno: Mapped[float] = mapped_column(Numeric(12, 2))

    pago: Mapped[PagoSueldo] = relationship(back_populates="detalles")
    turno: Mapped["TurnoCalendario"] = relationship()
