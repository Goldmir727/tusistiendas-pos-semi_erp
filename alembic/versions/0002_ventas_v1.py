"""Ventas v1: UUID, consecutivo legible, punto de venta, origen offline y vuelto.

Todo con guardas IF NOT EXISTS para poder aplicarse también sobre bases que ya
tenían tablas creadas por el seed anterior.

Revision ID: 0002
Revises: 0001
"""

from __future__ import annotations

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SENTENCIAS_UPGRADE = [
    "ALTER TABLE productos ADD COLUMN IF NOT EXISTS iva_porcentaje NUMERIC(5, 2) NOT NULL DEFAULT 0",
    "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS uuid UUID",
    "UPDATE ventas SET uuid = gen_random_uuid() WHERE uuid IS NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_ventas_uuid ON ventas (uuid)",
    "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS consecutivo INTEGER",
    (
        "UPDATE ventas v SET consecutivo = sub.rn FROM "
        "(SELECT id_venta, row_number() OVER (PARTITION BY id_sucursal ORDER BY id_venta) AS rn FROM ventas) sub "
        "WHERE v.id_venta = sub.id_venta AND v.consecutivo IS NULL"
    ),
    "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS id_punto_venta INTEGER REFERENCES puntos_venta (id_punto_venta)",
    "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS origen VARCHAR(20) NOT NULL DEFAULT 'online'",
    "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS creado_offline_en TIMESTAMP",
    "ALTER TABLE venta_pago ADD COLUMN IF NOT EXISTS vuelto NUMERIC(12, 2) NOT NULL DEFAULT 0",
    (
        "CREATE TABLE IF NOT EXISTS consecutivos ("
        "id_consecutivo SERIAL PRIMARY KEY, "
        "nombre VARCHAR(50) NOT NULL, "
        "id_sucursal INTEGER NOT NULL REFERENCES sucursales (id_sucursal), "
        "ultimo INTEGER NOT NULL DEFAULT 0, "
        "CONSTRAINT uq_consecutivos_nombre_sucursal UNIQUE (nombre, id_sucursal))"
    ),
    "CREATE INDEX IF NOT EXISTS ix_consecutivos_id_sucursal ON consecutivos (id_sucursal)",
    (
        "INSERT INTO consecutivos (nombre, id_sucursal, ultimo) "
        "SELECT 'venta', id_sucursal, COALESCE(MAX(consecutivo), 0) FROM ventas "
        "GROUP BY id_sucursal ON CONFLICT DO NOTHING"
    ),
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_ventas_sucursal_consecutivo ON ventas (id_sucursal, consecutivo)",
]


def upgrade() -> None:
    bind = op.get_bind()
    for sentencia in SENTENCIAS_UPGRADE:
        bind.exec_driver_sql(sentencia)

    # Solo se vuelven obligatorios cuando ya hay valores en todas las filas.
    bind.exec_driver_sql("ALTER TABLE ventas ALTER COLUMN uuid SET NOT NULL")
    bind.exec_driver_sql("ALTER TABLE ventas ALTER COLUMN consecutivo SET NOT NULL")


def downgrade() -> None:
    bind = op.get_bind()
    for sentencia in (
        "DROP INDEX IF EXISTS uq_ventas_sucursal_consecutivo",
        "DROP INDEX IF EXISTS ix_ventas_uuid",
        "ALTER TABLE venta_pago DROP COLUMN IF EXISTS vuelto",
        "ALTER TABLE ventas DROP COLUMN IF EXISTS creado_offline_en",
        "ALTER TABLE ventas DROP COLUMN IF EXISTS origen",
        "ALTER TABLE ventas DROP COLUMN IF EXISTS id_punto_venta",
        "ALTER TABLE ventas DROP COLUMN IF EXISTS consecutivo",
        "ALTER TABLE ventas DROP COLUMN IF EXISTS uuid",
        "ALTER TABLE productos DROP COLUMN IF EXISTS iva_porcentaje",
        "DROP TABLE IF EXISTS consecutivos",
    ):
        bind.exec_driver_sql(sentencia)
