from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.database import Base
from app.models import *  # noqa: F401, F403

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
target_metadata = Base.metadata


def _database_url() -> str:
    # Se ignora sqlalchemy.url del ini: la app ya resuelve la URL real
    # (DATABASE_URL o POSTGRES_*) y el driver es asyncpg.
    return settings.resolved_database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connect_args = {"ssl": "require"} if settings.database_ssl_required else {}
    engine = create_async_engine(_database_url(), poolclass=pool.NullPool, connect_args=connect_args)

    async def _run() -> None:
        async with engine.connect() as connection:
            await connection.run_sync(_run_migrations)
        await engine.dispose()

    asyncio.run(_run())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
