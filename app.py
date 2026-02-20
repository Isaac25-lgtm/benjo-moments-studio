"""
Benjo Moments Photography System
Main Flask Application Entry Point

Run with: python app.py
"""
import logging
import os
import hmac
import secrets

# Load .env file for local development (python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from flask import Flask, abort, request, session
import config

logger = logging.getLogger(__name__)


def run_migrations():
    """Run Alembic migrations (upgrade head) at startup."""
    try:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "alembic.ini"))
        alembic_cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "migrations"))
        alembic_cfg.set_main_option("sqlalchemy.url", config.DATABASE_URL)
        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied successfully.")
    except Exception as exc:
        logger.error("Alembic migration failed: %s", exc)
        raise


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Configuration
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
    app.config["UPLOAD_FOLDER"] = config.UPLOAD_FOLDER
    app.config["SESSION_COOKIE_HTTPONLY"] = config.SESSION_COOKIE_HTTPONLY
    app.config["SESSION_COOKIE_SAMESITE"] = config.SESSION_COOKIE_SAMESITE
    app.config["SESSION_COOKIE_SECURE"] = config.SESSION_COOKIE_SECURE

    # Ensure upload directory exists
    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

    # Run Alembic migrations before serving any requests
    run_migrations()

    # Seed defaults
    import database
    with app.app_context():
        database.init_default_settings()
        database.create_default_pricing_packages()
        if not config.TEST_AUTH_MODE:
            database.create_default_admin()

    # CSRF token helper for Jinja templates
    def generate_csrf_token():
        token = session.get("_csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["_csrf_token"] = token
        return token

    app.jinja_env.globals["csrf_token"] = generate_csrf_token

    @app.before_request
    def protect_against_csrf():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            token = request.form.get(config.CSRF_TOKEN_FIELD) or request.headers.get("X-CSRF-Token")
            session_token = session.get("_csrf_token")
            if not session_token or not token or not hmac.compare_digest(session_token, token):
                abort(400, description="Invalid CSRF token. Refresh the page and try again.")

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    # Register blueprints
    from auth import auth
    from admin import admin
    from public import public
    app.register_blueprint(auth)
    app.register_blueprint(admin)
    app.register_blueprint(public)

    logger.info(
        "Benjo Moments started | env=%s | TEST_AUTH_MODE=%s | DB=%s",
        config.FLASK_ENV,
        config.TEST_AUTH_MODE,
        "sqlite" if "sqlite" in (config.DATABASE_URL or "") else "postgres",
    )
    return app


if __name__ == "__main__":
    app = create_app()
    print("\n" + "=" * 60)
    print("  BENJO MOMENTS PHOTOGRAPHY SYSTEM")
    print("=" * 60)
    print(f"\n  Server running at: http://127.0.0.1:5000")
    print(f"\n  Admin Login:       http://127.0.0.1:5000/login")
    print(f"  Admin Dashboard:   http://127.0.0.1:5000/admin")
    print(f"  TEST_AUTH_MODE:    {config.TEST_AUTH_MODE}")
    print("=" * 60 + "\n")
    app.run(debug=not config.IS_PRODUCTION)
