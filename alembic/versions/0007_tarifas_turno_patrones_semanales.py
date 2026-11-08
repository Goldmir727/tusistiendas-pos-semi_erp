"""Tarifas configurables y patrones semanales de turnos.

Revision ID: 0007
Revises: 0006
"""

from __future__ import annotations

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

SENTENCIAS_UPGRADE = [
    "ALTER TABLE turno_plantillas ADD COLUMN IF NOT EXISTS dias_semana JSONB",
    "ALTER TABLE turno_plantillas ADD COLUMN IF NOT EXISTS usar_tarifa BOOLEAN NOT NULL DEFAULT TRUE",
    "ALTER TABLE turno_plantillas ALTER COLUMN dia_semana DROP NOT NULL",
    # Backfill de patrones antiguos (un solo día) a la nueva lista de días.
    """
    UPDATE turno_plantillas
    SET dias_semana = jsonb_build_array(
        CASE dia_semana::text
            WHEN 'lunes' THEN 0
            WHEN 'martes' THEN 1
            WHEN 'miercoles' THEN 2
            WHEN 'jueves' THEN 3
            WHEN 'viernes' THEN 4
            WHEN 'sabado' THEN 5
            WHEN 'domingo' THEN 6
            ELSE 0
        END
    )
    WHERE dias_semana IS NULL AND dia_semana IS NOT NULL
    """,
    """
    CREATE TABLE IF NOT EXISTS tarifas_turno (
        id_tarifa SERIAL PRIMARY KEY,
        nombre VARCHAR(120) NOT NULL,
        hora_inicio TIME NOT NULL,
        hora_fin TIME NOT NULL,
        dias_semana JSONB NOT NULL DEFAULT '[0,1,2,3,4,5,6]'::jsonb,
        valor NUMERIC(12,2) NOT NULL,
        id_sucursal INTEGER REFERENCES sucursales (id_sucursal) ON DELETE CASCADE,
        prioridad INTEGER NOT NULL DEFAULT 0,
        activa BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_tarifas_turno_id_sucursal ON tarifas_turno (id_sucursal)",
    "CREATE INDEX IF NOT EXISTS ix_tarifas_turno_activa ON tarifas_turno (activa)",
]

SENTENCIAS_DOWNGRADE = [
    "DROP INDEX IF EXISTS ix_tarifas_turno_activa",
    "DROP INDEX IF EXISTS ix_tarifas_turno_id_sucursal",
    "DROP TABLE IF EXISTS tarifas_turno",
    "ALTER TABLE turno_plantillas DROP COLUMN IF EXISTS usar_tarifa",
    "ALTER TABLE turno_plantillas DROP COLUMN IF EXISTS dias_semana",
]


def upgrade() -> None:
    bind = op.get_bind()
    for sentencia in SENTENCIAS_UPGRADE:
        bind.exec_driver_sql(sentencia)


def downgrade() -> None:
    bind = op.get_bind()
    for sentencia in SENTENCIAS_DOWNGRADE:
        bind.exec_driver_sql(sentencia)
