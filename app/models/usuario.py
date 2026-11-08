from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    and_,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RolEnum(str, enum.Enum):
    administrador = "administrador"
    cajero = "cajero"
    empleado = "empleado"


class Usuario(Base):
    __tablename__ = "usuarios"

    id_usuario: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre_completo: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    documento_identidad: Mapped[str] = mapped_column(String(20), unique=True)
    contrasena_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[RolEnum] = mapped_column(Enum(RolEnum, name="rol_enum"))
    telefono: Mapped[str | None] = mapped_column(String(20))
    banco_nombre: Mapped[str | None] = mapped_column(String(50))
    banco_numero_cuenta: Mapped[str | None] = mapped_column(String(30))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    auth_2fa_habilitado: Mapped[bool] = mapped_column(Boolean, default=False)
    id_punto_venta: Mapped[int | None] = mapped_column(Integer, ForeignKey("puntos_venta.id_punto_venta"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    id_sucursal: Mapped[int | None] = mapped_column(Integer, ForeignKey("sucursales.id_sucursal"))

    permisos: Mapped[list["Permiso"]] = relationship(
        secondary="rol_permisos",
        primaryjoin="Usuario.rol == RolPermiso.rol",
        secondaryjoin="RolPermiso.id_permiso == Permiso.id_permiso",
        viewonly=True,
        back_populates="usuarios",
    )
    sesiones: Mapped[list["SesionUsuario"]] = relationship(back_populates="usuario")
    dispositivos_confiables: Mapped[list["DispositivoConfiable"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )
    turnos_titular: Mapped[list["TurnoCalendario"]] = relationship(
        foreign_keys="[TurnoCalendario.id_usuario_titular]", back_populates="titular"
    )
    turnos_reemplazo: Mapped[list["TurnoCalendario"]] = relationship(
        foreign_keys="[TurnoCalendario.id_usuario_reemplazo]", back_populates="reemplazo"
    )


class Permiso(Base):
    __tablename__ = "permisos"

    id_permiso: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True)
    descripcion: Mapped[str] = mapped_column(String(200))

    usuarios: Mapped[list[Usuario]] = relationship(
        secondary="rol_permisos",
        primaryjoin="Permiso.id_permiso == RolPermiso.id_permiso",
        secondaryjoin="RolPermiso.rol == Usuario.rol",
        viewonly=True,
        back_populates="permisos",
    )


class RolPermiso(Base):
    __tablename__ = "rol_permisos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rol: Mapped[RolEnum] = mapped_column(Enum(RolEnum, name="rol_enum"), index=True)
    id_permiso: Mapped[int] = mapped_column(Integer, ForeignKey("permisos.id_permiso"))

    permiso: Mapped[Permiso] = relationship()


class SesionUsuario(Base):
    __tablename__ = "sesiones_usuario"

    id_sesion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id_usuario"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expira_en: Mapped[datetime] = mapped_column(DateTime)
    revocado_en: Mapped[datetime | None] = mapped_column(DateTime)

    usuario: Mapped[Usuario] = relationship(back_populates="sesiones")


class DispositivoConfiable(Base):
    __tablename__ = "dispositivos_confiables"

    id_dispositivo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id_usuario"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    nombre: Mapped[str | None] = mapped_column(String(120))
    user_agent: Mapped[str | None] = mapped_column(Text)
    ip: Mapped[str | None] = mapped_column(String(45))
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ultimo_uso: Mapped[datetime | None] = mapped_column(DateTime)
    expira_en: Mapped[datetime] = mapped_column(DateTime)
    revocado_en: Mapped[datetime | None] = mapped_column(DateTime)

    usuario: Mapped["Usuario"] = relationship(back_populates="dispositivos_confiables")


class CodigoVerificacion(Base):
    __tablename__ = "codigos_verificacion"

    id_codigo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id_usuario"), index=True)
    codigo_hash: Mapped[str] = mapped_column(String(128))
    challenge_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expira_en: Mapped[datetime] = mapped_column(DateTime)
    usado: Mapped[bool] = mapped_column(Boolean, default=False)
    intentos: Mapped[int] = mapped_column(Integer, default=0)
    reenvios: Mapped[int] = mapped_column(Integer, default=0)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ultimo_envio: Mapped[datetime | None] = mapped_column(DateTime)
