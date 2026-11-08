from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.turno import EstadoTurno


def _normalizar_dias(dias: list[int]) -> list[int]:
    normalizados = sorted({int(d) for d in dias})
    if not normalizados:
        raise ValueError("Debe indicar al menos un día de la semana")
    if any(d < 0 or d > 6 for d in normalizados):
        raise ValueError("Los días deben estar entre 0 (lunes) y 6 (domingo)")
    return normalizados


class TurnoCreate(BaseModel):
    id_usuario_titular: int
    fecha: date
    hora_inicio: time
    hora_fin: time
    valor_total_turno: Decimal | None = None
    usar_tarifa: bool = True
    id_sucursal: int | None = None


class TurnoRead(BaseModel):
    id_turno: int
    id_usuario_titular: int
    id_usuario_reemplazo: int | None = None
    fecha: date
    hora_inicio: time
    hora_fin: time
    valor_total_turno: Decimal
    id_sucursal: int
    horas_reemplazadas_parcial: int = 0
    estado_turno: EstadoTurno
    hora_apertura_real: datetime | None = None
    hora_cierre_real: datetime | None = None
    id_sesion_caja: int | None = None
    nombre_titular: str | None = None
    nombre_reemplazo: str | None = None
    nombre_sucursal: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TurnoPlantillaCreate(BaseModel):
    nombre: str
    dia_semana: int | None = None
    dias_semana: list[int] | None = None
    hora_inicio: time
    hora_fin: time
    valor_total_turno: Decimal | None = None
    usar_tarifa: bool = True
    id_usuario_titular: int
    id_sucursal: int
    activa: bool = True

    @model_validator(mode="after")
    def _completar_dias(self) -> "TurnoPlantillaCreate":
        dias = self.dias_semana or ([self.dia_semana] if self.dia_semana is not None else [])
        self.dias_semana = _normalizar_dias(dias)
        self.dia_semana = self.dias_semana[0]
        return self


class TurnoPlantillaUpdate(BaseModel):
    nombre: str | None = None
    dia_semana: int | None = None
    dias_semana: list[int] | None = None
    hora_inicio: time | None = None
    hora_fin: time | None = None
    valor_total_turno: Decimal | None = None
    usar_tarifa: bool | None = None
    id_usuario_titular: int | None = None
    id_sucursal: int | None = None
    activa: bool | None = None

    @field_validator("dias_semana")
    @classmethod
    def _validar_dias(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        return _normalizar_dias(value)


class TurnoPlantillaRead(BaseModel):
    id_plantilla: int
    nombre: str
    dia_semana: int | None = None
    dias_semana: list[int] = Field(default_factory=list)
    hora_inicio: time
    hora_fin: time
    valor_total_turno: Decimal
    usar_tarifa: bool = True
    id_usuario_titular: int
    id_sucursal: int
    activa: bool
    nombre_titular: str | None = None
    nombre_sucursal: str | None = None

    model_config = {"from_attributes": True}


class TarifaTurnoBase(BaseModel):
    nombre: str
    hora_inicio: time
    hora_fin: time
    dias_semana: list[int] = Field(default_factory=lambda: list(range(7)))
    valor: Decimal
    id_sucursal: int | None = None
    prioridad: int = 0
    activa: bool = True

    @field_validator("dias_semana")
    @classmethod
    def _validar_dias(cls, value: list[int]) -> list[int]:
        return _normalizar_dias(value)


class TarifaTurnoCreate(TarifaTurnoBase):
    pass


class TarifaTurnoUpdate(BaseModel):
    nombre: str | None = None
    hora_inicio: time | None = None
    hora_fin: time | None = None
    dias_semana: list[int] | None = None
    valor: Decimal | None = None
    id_sucursal: int | None = None
    prioridad: int | None = None
    activa: bool | None = None

    @field_validator("dias_semana")
    @classmethod
    def _validar_dias(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        return _normalizar_dias(value)


class TarifaTurnoRead(TarifaTurnoBase):
    id_tarifa: int
    created_at: datetime
    updated_at: datetime
    nombre_sucursal: str | None = None

    model_config = {"from_attributes": True}


class TarifaSugeridaRead(BaseModel):
    id_tarifa: int | None = None
    nombre: str | None = None
    valor: Decimal | None = None


class FestivoRead(BaseModel):
    id_festivo: int
    fecha: date
    nombre: str
    recurrente_anual: bool

    model_config = {"from_attributes": True}


class CalendarioTurnosRead(BaseModel):
    fecha_desde: date
    fecha_hasta: date
    turnos: list[TurnoRead]
    festivos: list[FestivoRead]


class GeneracionTurnosRequest(BaseModel):
    fecha_desde: date
    fecha_hasta: date
    id_usuarios: list[int] | None = None
    id_sucursal: int | None = None
    id_plantillas: list[int] | None = None
    modo: Literal["omitir", "reemplazar"] = "omitir"
    dry_run: bool = True
    recalcular_tarifa: bool = True

    @model_validator(mode="after")
    def _validar_rango(self) -> "GeneracionTurnosRequest":
        if self.fecha_hasta < self.fecha_desde:
            raise ValueError("La fecha final no puede ser anterior a la inicial")
        if (self.fecha_hasta - self.fecha_desde).days > 366:
            raise ValueError("El rango de generación no puede superar 366 días")
        return self


class GeneracionTurnoItem(BaseModel):
    fecha: date
    id_usuario_titular: int
    nombre_titular: str | None = None
    id_sucursal: int
    nombre_sucursal: str | None = None
    hora_inicio: time
    hora_fin: time
    valor_total_turno: Decimal
    accion: str
    motivo: str | None = None
    id_plantilla: int | None = None
    id_turno_existente: int | None = None
    es_festivo: bool = False
    horas_semana: float = 0
    advertencia_horas: bool = False


class GeneracionTurnosResponse(BaseModel):
    dry_run: bool
    total_previstos: int
    total_creados: int
    total_existentes: int
    total_conflictos: int
    total_reemplazados: int
    items: list[GeneracionTurnoItem]


class TurnoBulkCreate(BaseModel):
    turnos: list[TurnoCreate] = Field(min_length=1)


class TurnoBulkResultado(BaseModel):
    creados: int
    omitidos: int
    errores: list[str] = Field(default_factory=list)
    turnos: list[TurnoRead] = Field(default_factory=list)


class TurnoBulkDelete(BaseModel):
    ids: list[int] = Field(min_length=1)


class SolicitudReemplazo(BaseModel):
    id_turno: int


class AprobacionReemplazo(BaseModel):
    id_turno: int
    id_usuario_reemplazo: int
    aprobar: bool
