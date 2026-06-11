"""
Alembic migrations environment for Benjo Moments Photography System.

Reads DATABASE_URL directly from the environment (does NOT import config.py)
so that `alembic upgrade head` works both locally and on Render without
triggering the production-only RuntimeError guard in config.py.
"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# ---------------------------------------------------------------------------
# Make sure the app root is on sys.path so we can import models
# ---------------------------------------------------------------------------
APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_ROOT))

# Load .env if present (local dev only — no-op in production)
try:
    from dotenv import load_dotenv
    load_dotenv(APP_ROOT / ".env")
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Resolve DATABASE_URL directly — do NOT import config.py.
# config.py raises RuntimeError in production when DATABASE_URL is absent,
# which would crash the pre-deploy step before the env var is available.
# ---------------------------------------------------------------------------
_db_url = os.environ.get("DATABASE_URL")

if not _db_url:
    raise RuntimeError(
        "DATABASE_URL is required. Set a PostgreSQL URL in .env locally "
        "or in the Render dashboard."
    )

# Normalise Render's legacy 'postgres://' scheme for SQLAlchemy 2.x
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif _db_url.startswith("postgresql://"):
    _db_url = _db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

if not _db_url.startswith("postgresql+psycopg2://"):
    raise RuntimeError("DATABASE_URL must use PostgreSQL with psycopg2.")

# Import models — this registers ORM metadata without touching config.py
from models import Base  # noqa: E402

# ---------------------------------------------------------------------------
# Alembic config object
# ---------------------------------------------------------------------------
alembic_cfg = context.config

# Override sqlalchemy.url with our resolved URL (never rely on alembic.ini)
alembic_cfg.set_main_option("sqlalchemy.url", _db_url)

# Set up logging from alembic.ini when it exists
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
