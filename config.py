"""
Configuration settings for Benjo Moments Photography System.
"""
import os
import secrets

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FLASK_ENV = os.environ.get("FLASK_ENV", "development").lower()
IS_PRODUCTION = FLASK_ENV == "production"

# Secret key for sessions
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if IS_PRODUCTION:
        raise RuntimeError("SECRET_KEY must be set in production.")
    SECRET_KEY = secrets.token_urlsafe(32)

# Database and uploads (configurable for persistent disks)
DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "database.db"))
UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(BASE_DIR, "static", "uploads"))

# Upload configuration
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

# Session security defaults
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = IS_PRODUCTION

# CSRF
CSRF_TOKEN_FIELD = "csrf_token"

# Album folders
ALBUM_FOLDERS = {
    "weddings": "weddings",
    "kukyala": "kukyala",
    "birthdays": "birthdays",
    "baby": "baby",
    "other": "other",
}

# Default admin credentials (env-driven in production)
DEFAULT_ADMIN_EMAIL = os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@benjomoments.com")
DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD")
if not DEFAULT_ADMIN_PASSWORD and not IS_PRODUCTION:
    DEFAULT_ADMIN_PASSWORD = "admin123"
DEFAULT_ADMIN_NAME = os.environ.get("DEFAULT_ADMIN_NAME", "Admin User")
