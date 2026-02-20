"""
Alembic migrations environment for Benjo Moments Photography System.

Reads DATABASE_URL from the environment (same as app config) so that
`alembic upgrade head` works both locally and on Render.
"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# ---------------------------------------------------------------------------
# Make sure the app root is on sys.path so we can import config + models
# ---------------------------------------------------------------------------
APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_ROOT))

# Load .env if present (local dev only)
try:
    from dotenv import load_dotenv
    load_dotenv(APP_ROOT / ".env")
except ImportError:
    pass

# Import app config and models
import config as app_config  # noqa: E402
from models import Base  # noqa: E402  — this registers all ORM models

# ---------------------------------------------------------------------------
# Alembic config object
# ---------------------------------------------------------------------------
alembic_cfg = context.config

# Override sqlalchemy.url from the DATABASE_URL env var (never hardcode it)
alembic_cfg.set_main_option("sqlalchemy.url", app_config.DATABASE_URL)

# Set up logging from alembic.ini if the file exists
if alembic_cfg.config_file_name is not None:
    fileConfig(alembic_cfg.config_file_name)

# Target our models' metadata for autogenerate
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Migration runners
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL without connecting)."""
    url = alembic_cfg.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (directly against a live DB)."""
    connectable = engine_from_config(
        alembic_cfg.get_section(alembic_cfg.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
