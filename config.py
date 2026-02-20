"""
Configuration settings for Benjo Moments Photography System.
All sensitive values must come from environment variables in production.
"""
import os
import logging
import secrets

# ---------------------------------------------------------------------------
# Base directory
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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
# TEST_AUTH_MODE=false → validate credentials against DB (production)
TEST_AUTH_MODE = os.environ.get("TEST_AUTH_MODE", "true").lower() in ("1", "true", "yes")

# USE_SQLITE_FALLBACK=true → fall back to SQLite when DATABASE_URL is unset
# Only honoured in non-production environments.
USE_SQLITE_FALLBACK = (
    not IS_PRODUCTION
    and os.environ.get("USE_SQLITE_FALLBACK", "true").lower() in ("1", "true", "yes")
)

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

# Legacy SQLite path — used only when USE_SQLITE_FALLBACK is active
DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "database.db"))

if not DATABASE_URL:
    if IS_PRODUCTION:
        raise RuntimeError(
            "DATABASE_URL environment variable must be set in production. "
            "Set it to your Neon Postgres connection string."
        )
    if USE_SQLITE_FALLBACK:
        DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
        logger.warning("DATABASE_URL not set — using SQLite fallback at %s", DATABASE_PATH)

# ---------------------------------------------------------------------------
# File uploads
# ---------------------------------------------------------------------------
UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(BASE_DIR, "static", "uploads"))
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

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
    "other": "other",
}

# ---------------------------------------------------------------------------
# Default admin credentials (env-driven; only used when TEST_AUTH_MODE=false)
# ---------------------------------------------------------------------------
DEFAULT_ADMIN_EMAIL = os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@benjomoments.com")
DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD")
if not DEFAULT_ADMIN_PASSWORD and not IS_PRODUCTION:
    DEFAULT_ADMIN_PASSWORD = "admin123"
DEFAULT_ADMIN_NAME = os.environ.get("DEFAULT_ADMIN_NAME", "Admin User")
