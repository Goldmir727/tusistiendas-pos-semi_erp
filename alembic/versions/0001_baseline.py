"""Esquema base de TuSisTiendas.

Crea todas las tablas definidas en los modelos. Es idempotente (checkfirst),
así que también sirve como línea base de una base que ya tenía tablas creadas
manualmente por el seed.

Revision ID: 0001
Revises:
"""

from __future__ import annotations

from alembic import op

from app.database import Base
import app.models  # noqa: F401  (registra todas las tablas en Base.metadata)

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), checkfirst=True)
