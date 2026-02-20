"""
Benjo Moments Photography System
Main Flask Application Entry Point

Run with: python app.py
Deploys via: gunicorn wsgi:app  (see render.yaml)
"""
import logging
import os
import hmac
import secrets
from datetime import timedelta

# Load .env file for local development (python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from flask import Flask, abort, jsonify, request, session
from werkzeug.middleware.proxy_fix import ProxyFix

import config
from extensions import init_limiter

logger = logging.getLogger(__name__)


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # -----------------------------------------------------------------------
    # ProxyFix: correct request.remote_addr behind Render's reverse proxy.
    # Must be applied BEFORE the limiter reads the IP.  (Phase 7 / Phase 9)
    # -----------------------------------------------------------------------
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # -----------------------------------------------------------------------
    # Flask configuration
    # -----------------------------------------------------------------------
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
    app.config["UPLOAD_FOLDER"] = config.UPLOAD_FOLDER
    app.config["SESSION_COOKIE_HTTPONLY"] = config.SESSION_COOKIE_HTTPONLY
    app.config["SESSION_COOKIE_SAMESITE"] = config.SESSION_COOKIE_SAMESITE
    app.config["SESSION_COOKIE_SECURE"] = config.SESSION_COOKIE_SECURE
    # Permanent session lifetime (Phase 8) — default 8 hours
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=config.SESSION_LIFETIME_HOURS)

    # -----------------------------------------------------------------------
    # Rate limiter init (Phase 7)
    # -----------------------------------------------------------------------
    init_limiter(app)

    # -----------------------------------------------------------------------
    # Upload directory
    # -----------------------------------------------------------------------
    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

    # NOTE (Phase 9): Alembic migrations are NO LONGER run at startup.
    # They run via Render's releaseCommand: "alembic upgrade head".
    # For local development, run: alembic upgrade head before starting the app.

    # -----------------------------------------------------------------------
    # Seed defaults (idempotent — safe to run every startup)
    # -----------------------------------------------------------------------
    import database
    with app.app_context():
        database.init_default_settings()
        database.create_default_pricing_packages()
        if not config.TEST_AUTH_MODE:
            database.create_default_admin()

    # -----------------------------------------------------------------------
    # CSRF token for Jinja templates
    # -----------------------------------------------------------------------
    def generate_csrf_token():
        token = session.get("_csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["_csrf_token"] = token
        return token

    app.jinja_env.globals["csrf_token"] = generate_csrf_token

    # -----------------------------------------------------------------------
    # CSRF protection middleware
    # -----------------------------------------------------------------------
    @app.before_request
    def protect_against_csrf():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            token = request.form.get(config.CSRF_TOKEN_FIELD) or request.headers.get("X-CSRF-Token")
            session_token = session.get("_csrf_token")
            if not session_token or not token or not hmac.compare_digest(session_token, token):
                abort(400, description="Invalid CSRF token. Refresh the page and try again.")

    # -----------------------------------------------------------------------
    # Security response headers
    # -----------------------------------------------------------------------
    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    # -----------------------------------------------------------------------
    # Rate limit error handler — friendly 429 response (Phase 7)
    # -----------------------------------------------------------------------
    @app.errorhandler(429)
    def ratelimit_handler(e):
        from flask import flash, redirect, request, url_for
        # For HTML requests: flash a message and redirect back (no crash page).
        # accept_html is a callable that returns True/False.
        try:
            wants_html = request.accept_mimetypes.accept_html()
        except Exception:
            wants_html = True  # safe default — show friendly redirect
        if wants_html:
            flash("Too many requests. Please slow down and try again in a minute.", "error")
            referrer = request.referrer or url_for("public.index")
            return redirect(referrer), 303
        return jsonify(error="Too many requests", retry_after=str(e.description)), 429

    # -----------------------------------------------------------------------
    # Blueprint registration
    # -----------------------------------------------------------------------
    from auth import auth
    from admin import admin
    from public import public
    app.register_blueprint(auth)
    app.register_blueprint(admin)
    app.register_blueprint(public)

    logger.info(
        "Benjo Moments started | env=%s | TEST_AUTH_MODE=%s | DB=%s | limiter_storage=%s",
        config.FLASK_ENV,
        config.TEST_AUTH_MODE,
        "sqlite" if "sqlite" in (config.DATABASE_URL or "") else "postgres",
        config.RATELIMIT_STORAGE_URI,
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
