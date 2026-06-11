"""
SQLAlchemy database engine and session management for Benjo Moments.

Usage:
    from db import SessionLocal, engine

    with SessionLocal() as session:
        # use session...

For Alembic migrations, the Base and engine are imported from models.
"""
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import config

logger = logging.getLogger(__name__)

logger.info(
    "Database: PostgreSQL | pool_size=%s | max_overflow=%s",
    config.DB_POOL_SIZE,
    config.DB_MAX_OVERFLOW,
)

engine = create_engine(
    config.DATABASE_URL,
    connect_args={
        "connect_timeout": config.DB_CONNECT_TIMEOUT,
        "application_name": "benjo_moments",
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    },
    pool_pre_ping=True,
    pool_recycle=config.DB_POOL_RECYCLE,
    pool_use_lifo=True,
    pool_size=config.DB_POOL_SIZE,
    max_overflow=config.DB_MAX_OVERFLOW,
    pool_timeout=config.DB_POOL_TIMEOUT,
    echo=False,
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_session():
    """Context-managed database session for use in application code."""
    return SessionLocal()
