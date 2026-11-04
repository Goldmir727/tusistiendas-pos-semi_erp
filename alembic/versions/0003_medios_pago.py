"""Medios de pago reales: transferencia y datáfono.

Los valores heredados (tarjeta, nequi, daviplata, pse) se conservan en el tipo
para no romper filas antiguas, pero sus filas de medios_pago quedan inactivas.

Revision ID: 0003
Revises: 0002
"""

from __future__ import annotations

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ADD VALUE no puede usarse en la misma transacción en que se lee el valor.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE metodo_pago_enum ADD VALUE IF NOT EXISTS 'transferencia'")
        op.execute("ALTER TYPE metodo_pago_enum ADD VALUE IF NOT EXISTS 'datafono'")

    op.execute(
        "UPDATE medios_pago SET activo = false "
        "WHERE tipo::text IN ('tarjeta', 'nequi', 'daviplata', 'pse')"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE medios_pago SET activo = true "
        "WHERE tipo::text IN ('tarjeta', 'nequi', 'daviplata', 'pse')"
    )
