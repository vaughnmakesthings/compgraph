import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from compgraph.db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Get migration connection URL. Uses session mode pooler (IPv4-safe).
    Direct connection (IPv6-only) is available via database_url_direct if your
    network supports IPv6."""
    try:
        from compgraph.config import settings

        return settings.database_url
    except Exception:
        return os.environ.get("DATABASE_URL", config.get_main_option("sqlalchemy.url", ""))


def include_name(name: str, type_: str, parent_names: dict) -> bool:
    """Only manage the public schema. Exclude Supabase-managed schemas
    (auth, storage, realtime, extensions) to prevent the April 2025 lockout."""
    if type_ == "schema":
        return name in ("public",)
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generates SQL without connecting."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_name=include_name,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_name=include_name,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using an async engine."""
    connectable = create_async_engine(
        get_url(), poolclass=pool.NullPool, connect_args={"ssl": "require"}
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
