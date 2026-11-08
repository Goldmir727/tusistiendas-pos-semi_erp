"""Cajas asignadas a usuarios, 2FA por email y dispositivos confiables.

Revision ID: 0006
Revises: 0005
"""

from __future__ import annotations

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

SENTENCIAS_UPGRADE = [
    "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS id_punto_venta INTEGER REFERENCES puntos_venta (id_punto_venta)",
    "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS auth_2fa_habilitado BOOLEAN NOT NULL DEFAULT FALSE",
    "CREATE INDEX IF NOT EXISTS ix_usuarios_id_punto_venta ON usuarios (id_punto_venta)",
    """
    CREATE TABLE IF NOT EXISTS dispositivos_confiables (
        id_dispositivo SERIAL PRIMARY KEY,
        id_usuario INTEGER NOT NULL REFERENCES usuarios (id_usuario) ON DELETE CASCADE,
        token_hash VARCHAR(128) NOT NULL UNIQUE,
        nombre VARCHAR(120),
        user_agent TEXT,
        ip VARCHAR(45),
        creado_en TIMESTAMP NOT NULL DEFAULT NOW(),
        ultimo_uso TIMESTAMP,
        expira_en TIMESTAMP NOT NULL,
        revocado_en TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_dispositivos_confiables_id_usuario ON dispositivos_confiables (id_usuario)",
    """
    CREATE TABLE IF NOT EXISTS codigos_verificacion (
        id_codigo SERIAL PRIMARY KEY,
        id_usuario INTEGER NOT NULL REFERENCES usuarios (id_usuario) ON DELETE CASCADE,
        codigo_hash VARCHAR(128) NOT NULL,
        challenge_hash VARCHAR(128) NOT NULL UNIQUE,
        expira_en TIMESTAMP NOT NULL,
        usado BOOLEAN NOT NULL DEFAULT FALSE,
        intentos INTEGER NOT NULL DEFAULT 0,
        reenvios INTEGER NOT NULL DEFAULT 0,
        creado_en TIMESTAMP NOT NULL DEFAULT NOW(),
        ultimo_envio TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_codigos_verificacion_id_usuario ON codigos_verificacion (id_usuario)",
]

SENTENCIAS_DOWNGRADE = [
    "DROP INDEX IF EXISTS ix_codigos_verificacion_id_usuario",
    "DROP TABLE IF EXISTS codigos_verificacion",
    "DROP INDEX IF EXISTS ix_dispositivos_confiables_id_usuario",
    "DROP TABLE IF EXISTS dispositivos_confiables",
    "DROP INDEX IF EXISTS ix_usuarios_id_punto_venta",
    "ALTER TABLE usuarios DROP COLUMN IF EXISTS auth_2fa_habilitado",
    "ALTER TABLE usuarios DROP COLUMN IF EXISTS id_punto_venta",
]


def upgrade() -> None:
    bind = op.get_bind()
    for sentencia in SENTENCIAS_UPGRADE:
        bind.exec_driver_sql(sentencia)


def downgrade() -> None:
    bind = op.get_bind()
    for sentencia in SENTENCIAS_DOWNGRADE:
        bind.exec_driver_sql(sentencia)