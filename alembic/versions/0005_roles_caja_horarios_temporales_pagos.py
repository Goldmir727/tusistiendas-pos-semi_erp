"""Roles diferenciales, caja por empleado, temporales y pago recibido.

Revision ID: 0005
Revises: 0004
"""

from __future__ import annotations

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

SENTENCIAS_UPGRADE = [
    "ALTER TYPE rol_enum ADD VALUE IF NOT EXISTS 'empleado'",
    "ALTER TABLE sesiones_caja ADD COLUMN IF NOT EXISTS id_usuario_abre_caja INTEGER REFERENCES usuarios (id_usuario)",
    "ALTER TABLE turnos_calendario ADD COLUMN IF NOT EXISTS hora_apertura_real TIMESTAMP",
    "ALTER TABLE turnos_calendario ADD COLUMN IF NOT EXISTS hora_cierre_real TIMESTAMP",
    "ALTER TABLE turnos_calendario ADD COLUMN IF NOT EXISTS id_sesion_caja INTEGER REFERENCES sesiones_caja (id_sesion_caja)",
    "ALTER TABLE pagos_sueldos ADD COLUMN IF NOT EXISTS recibido_empleado BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE pagos_sueldos ADD COLUMN IF NOT EXISTS fecha_recibido TIMESTAMP",
    """
    CREATE TABLE IF NOT EXISTS ventas_temporales (
        id_venta_temporal VARCHAR(36) PRIMARY KEY,
        id_sesion_caja INTEGER NOT NULL REFERENCES sesiones_caja (id_sesion_caja),
        id_usuario_creador INTEGER NOT NULL REFERENCES usuarios (id_usuario),
        nombre VARCHAR(200) NOT NULL,
        id_cliente INTEGER REFERENCES clientes (id_cliente),
        cliente_nombre VARCHAR(200),
        items JSONB NOT NULL DEFAULT '[]'::jsonb,
        descripcion TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_ventas_temporales_id_sesion_caja ON ventas_temporales (id_sesion_caja)",
]

SENTENCIAS_DOWNGRADE = [
    "DROP INDEX IF EXISTS ix_ventas_temporales_id_sesion_caja",
    "DROP TABLE IF EXISTS ventas_temporales",
    "ALTER TABLE pagos_sueldos DROP COLUMN IF EXISTS fecha_recibido",
    "ALTER TABLE pagos_sueldos DROP COLUMN IF EXISTS recibido_empleado",
    "ALTER TABLE turnos_calendario DROP COLUMN IF EXISTS id_sesion_caja",
    "ALTER TABLE turnos_calendario DROP COLUMN IF EXISTS hora_cierre_real",
    "ALTER TABLE turnos_calendario DROP COLUMN IF EXISTS hora_apertura_real",
    "ALTER TABLE sesiones_caja DROP COLUMN IF EXISTS id_usuario_abre_caja",
]


def upgrade() -> None:
    bind = op.get_bind()
    for sentencia in SENTENCIAS_UPGRADE:
        bind.exec_driver_sql(sentencia)


def downgrade() -> None:
    bind = op.get_bind()
    for sentencia in SENTENCIAS_DOWNGRADE:
        bind.exec_driver_sql(sentencia)