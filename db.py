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
_connect_args = {}
if config.DATABASE_URL and config.DATABASE_URL.startswith("sqlite"):
    # SQLite needs check_same_thread=False for Flask's threaded server
    _connect_args = {"check_same_thread": False}
    logger.info("Database: SQLite (fallback mode) at %s", config.DATABASE_PATH)
else:
    logger.info("Database: PostgreSQL via DATABASE_URL")

engine = create_engine(
    config.DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,         # detect stale connections
    pool_recycle=300,           # recycle connections every 5 minutes (Neon compatible)
    echo=False,                 # set True temporarily for query debugging
)

# Enable foreign key enforcement for SQLite
if config.DATABASE_URL and config.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_session():
    """Context-managed database session for use in application code."""
    return SessionLocal()
