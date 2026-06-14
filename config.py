"""
Configuration settings for Benjo Moments Photography System.
All sensitive values must come from environment variables in production.
"""
import os
import logging
import secrets
import hashlib
import hmac
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Base directory
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
if os.environ.get("FLASK_ENV", "development").lower() != "production":
    load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------
FLASK_ENV = os.environ.get("FLASK_ENV", "development").lower()
IS_PRODUCTION = FLASK_ENV == "production"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = logging.INFO if IS_PRODUCTION else logging.DEBUG
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("benjo_moments")

# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------
# TEST_AUTH_MODE=true  → any non-empty email/password logs in (dev/demo only)
# TEST_AUTH_MODE=false → use the environment-managed admin (production)
TEST_AUTH_MODE = os.environ.get("TEST_AUTH_MODE", "false").lower() in ("1", "true", "yes")
if IS_PRODUCTION and TEST_AUTH_MODE:
    raise RuntimeError("TEST_AUTH_MODE must be false in production.")

# ---------------------------------------------------------------------------
# Secret key
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if IS_PRODUCTION:
        raise RuntimeError(
            "SECRET_KEY environment variable must be set in production. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
    SECRET_KEY = secrets.token_urlsafe(32)
    logger.warning("SECRET_KEY not set — using a random ephemeral key (sessions will reset on restart).")

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is required. Benjo Moments supports PostgreSQL only. "
        "Set it in .env locally and in the Render dashboard for production."
    )

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

if not DATABASE_URL.startswith("postgresql+psycopg2://"):
    raise RuntimeError("DATABASE_URL must be a PostgreSQL psycopg2 connection URL.")

DB_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", "2"))
DB_POOL_TIMEOUT = int(os.environ.get("DB_POOL_TIMEOUT", "15"))
DB_POOL_RECYCLE = int(os.environ.get("DB_POOL_RECYCLE", "300"))
DB_CONNECT_TIMEOUT = int(os.environ.get("DB_CONNECT_TIMEOUT", "10"))

# ---------------------------------------------------------------------------
# File uploads
# ---------------------------------------------------------------------------
UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(BASE_DIR / "instance" / "uploads"))
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB (supports batch uploads of up to 10 images)
MAX_IMAGE_FILE_SIZE = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000

# ---------------------------------------------------------------------------
# Session / CSRF
# ---------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = IS_PRODUCTION
CSRF_TOKEN_FIELD = "csrf_token"
SESSION_LIFETIME_HOURS = int(os.environ.get("SESSION_LIFETIME_HOURS", "8"))

# ---------------------------------------------------------------------------
# Auth hardening (Phase 8)
# ---------------------------------------------------------------------------
# TEST_PIN: if set, the password must match this value when TEST_AUTH_MODE=true.
# Leave unset to accept any non-empty password (original behaviour).
TEST_PIN = os.environ.get("TEST_PIN")  # None by default

# ---------------------------------------------------------------------------
# Rate limiting (Phase 7)
# ---------------------------------------------------------------------------
# Priority: RATELIMIT_STORAGE_URI > REDIS_URL > memory://
RATELIMIT_STORAGE_URI = (
    os.environ.get("RATELIMIT_STORAGE_URI")
    or os.environ.get("REDIS_URL")
    or "memory://"
)

# ---------------------------------------------------------------------------
# Album folders
# ---------------------------------------------------------------------------
ALBUM_FOLDERS = {
    "weddings": "weddings",
    "kukyala": "kukyala",
    "birthdays": "birthdays",
    "baby": "baby",
    "graduations": "graduations",
    "parties": "parties",
    "corporate": "corporate",
    "church": "church",
    "community": "community",
    "portraits": "portraits",
    "family": "family",
    "couples": "couples",
    "studio": "studio",
    "passport": "passport",
    "video": "video",
    "graphics": "graphics",
    "products": "products",
    "food": "food",
    "real-estate": "real-estate",
    "advertising": "advertising",
    "other": "other",
}

# ---------------------------------------------------------------------------
# Authoritative admin credentials
# ---------------------------------------------------------------------------
DEFAULT_ADMIN_EMAIL = os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@benjomoments.com")
DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD")
if not DEFAULT_ADMIN_PASSWORD and not IS_PRODUCTION:
    DEFAULT_ADMIN_PASSWORD = "admin123"
DEFAULT_ADMIN_NAME = os.environ.get("DEFAULT_ADMIN_NAME", "Admin User")

if IS_PRODUCTION:
    if not DEFAULT_ADMIN_EMAIL or "@" not in DEFAULT_ADMIN_EMAIL:
        raise RuntimeError("DEFAULT_ADMIN_EMAIL must be a valid email address in production.")
    if not DEFAULT_ADMIN_PASSWORD:
        raise RuntimeError("DEFAULT_ADMIN_PASSWORD must be set in production.")
    if len(DEFAULT_ADMIN_PASSWORD) < 12:
        raise RuntimeError("DEFAULT_ADMIN_PASSWORD must be at least 12 characters in production.")

DEFAULT_ADMIN_EMAIL = DEFAULT_ADMIN_EMAIL.strip().lower()
ADMIN_CREDENTIAL_VERSION = hmac.new(
    SECRET_KEY.encode("utf-8"),
    f"{DEFAULT_ADMIN_EMAIL}\0{DEFAULT_ADMIN_PASSWORD or ''}".encode("utf-8"),
    hashlib.sha256,
).hexdigest()
