"""
Configuration settings for Benjo Moments Photography System.
"""
import os

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Secret key for sessions
SECRET_KEY = os.environ.get('SECRET_KEY', 'benjo-moments-secret-key-change-in-production')

# Database configuration
DATABASE_PATH = os.path.join(BASE_DIR, 'database.db')

# Upload configuration
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

# Album folders
ALBUM_FOLDERS = {
    'weddings': 'weddings',
    'kukyala': 'kukyala',
    'birthdays': 'birthdays',
    'baby': 'baby',
    'other': 'other'
}

# Default admin credentials (change in production)
DEFAULT_ADMIN_EMAIL = 'admin@benjomoments.com'
DEFAULT_ADMIN_PASSWORD = 'admin123'
DEFAULT_ADMIN_NAME = 'Admin User'
