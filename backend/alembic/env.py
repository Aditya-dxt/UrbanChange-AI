"""
Alembic environment configuration.

Reads DATABASE_URL from the environment so no credentials are ever
stored in version control.  Supports both online (async) and offline
modes.
"""
from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# ── Read alembic.ini logging config ──────────────────────────────────────────
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import ORM metadata ───────────────────────────────────────────────────────
# Phase 3 will replace this import with the real models.
# The import must succeed even when models.py is a stub.
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.session import Base  # noqa: E402
import app.db.models  # noqa: F401, E402  – registers models with Base.metadata

target_metadata = Base.metadata

# ── Get DATABASE_URL from environment (never from alembic.ini) ───────────────

def get_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Cannot run Alembic migrations."
        )
    # asyncpg driver is needed for SQLAlchemy async; alembic online mode uses
    # the sync psycopg2 driver via the synchronous engine wrapper.
    # We keep asyncpg for the async path and use psycopg2 for the sync path.
    return url


# ── Offline mode (generates SQL script without connecting) ────────────────────

def run_migrations_offline() -> None:
    url = get_url()
    # Replace asyncpg with psycopg2 for the offline SQL generation.
    sync_url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    context.configure(
        url=sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (connects and runs migrations) ────────────────────────────────

def do_run_migrations(connection: object) -> None:
    context.configure(
        connection=connection,  # type: ignore[arg-type]
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    url = get_url()
    connectable = create_async_engine(url, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


# ── Entry point ───────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
