"""
SQLAlchemy database engine and session management for Benjo Moments.

Usage:
    from db import SessionLocal, engine

    with SessionLocal() as session:
        # use session...

For Alembic migrations, the Base and engine are imported from models.
"""
import logging

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
_is_sqlite = config.DATABASE_URL and config.DATABASE_URL.startswith("sqlite")

_connect_args = {}
_pool_kwargs = {}

if _is_sqlite:
    # SQLite needs check_same_thread=False for Flask's threaded server.
    # Do NOT add pool_size/max_overflow — SQLite uses StaticPool by default.
    _connect_args = {"check_same_thread": False}
    logger.info("Database: SQLite (fallback mode) at %s", config.DATABASE_PATH)
else:
    # PostgreSQL (Neon): conservative pool sizing for 2 gunicorn workers.
    # Each worker × 3 connections = 6 active + 2 overflow = 8 max connections.
    # Neon free tier allows 10 concurrent connections.
    _pool_kwargs = {
        "pool_size": 3,
        "max_overflow": 2,
    }
    logger.info("Database: PostgreSQL via DATABASE_URL")

engine = create_engine(
    config.DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,     # detect and drop stale connections (essential for Neon)
    pool_recycle=300,       # recycle every 5 min (Neon closes idle > 5 min)
    echo=False,             # set True temporarily for query debugging
    **_pool_kwargs,
)

# Enable foreign key enforcement for SQLite
if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

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
