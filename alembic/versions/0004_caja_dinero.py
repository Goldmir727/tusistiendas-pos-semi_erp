"""Caja v1: abonos y devoluciones en efectivo dentro del efectivo esperado.

RF-53 / RN-03: el efectivo esperado al cierre es
base inicial + ventas en efectivo + abonos en efectivo
- devoluciones en efectivo - egresos.

Revision ID: 0004
Revises: 0003
"""

from __future__ import annotations

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

SENTENCIAS_UPGRADE = [
    "ALTER TABLE sesiones_caja ADD COLUMN IF NOT EXISTS abonos_efectivo NUMERIC(12, 2) NOT NULL DEFAULT 0",
    "ALTER TABLE sesiones_caja ADD COLUMN IF NOT EXISTS devoluciones_efectivo NUMERIC(12, 2) NOT NULL DEFAULT 0",
    "ALTER TABLE sesiones_caja ADD COLUMN IF NOT EXISTS total_egresos NUMERIC(12, 2) NOT NULL DEFAULT 0",
    "ALTER TABLE abonos_cliente ADD COLUMN IF NOT EXISTS metodo VARCHAR(20) NOT NULL DEFAULT 'efectivo'",
    "ALTER TABLE abonos_cliente ADD COLUMN IF NOT EXISTS id_sesion_caja INTEGER REFERENCES sesiones_caja (id_sesion_caja)",
    "ALTER TABLE abonos_cliente ADD COLUMN IF NOT EXISTS id_sucursal INTEGER REFERENCES sucursales (id_sucursal)",
    "ALTER TABLE devoluciones ADD COLUMN IF NOT EXISTS metodo_reembolso VARCHAR(20) NOT NULL DEFAULT 'efectivo'",
    "CREATE INDEX IF NOT EXISTS ix_abonos_cliente_id_sesion_caja ON abonos_cliente (id_sesion_caja)",
]


def upgrade() -> None:
    bind = op.get_bind()
    for sentencia in SENTENCIAS_UPGRADE:
        bind.exec_driver_sql(sentencia)


def downgrade() -> None:
    bind = op.get_bind()
    for sentencia in (
        "DROP INDEX IF EXISTS ix_abonos_cliente_id_sesion_caja",
        "ALTER TABLE devoluciones DROP COLUMN IF EXISTS metodo_reembolso",
        "ALTER TABLE abonos_cliente DROP COLUMN IF EXISTS id_sucursal",
        "ALTER TABLE abonos_cliente DROP COLUMN IF EXISTS id_sesion_caja",
        "ALTER TABLE abonos_cliente DROP COLUMN IF EXISTS metodo",
        "ALTER TABLE sesiones_caja DROP COLUMN IF EXISTS total_egresos",
        "ALTER TABLE sesiones_caja DROP COLUMN IF EXISTS devoluciones_efectivo",
        "ALTER TABLE sesiones_caja DROP COLUMN IF EXISTS abonos_efectivo",
    ):
        bind.exec_driver_sql(sentencia)
