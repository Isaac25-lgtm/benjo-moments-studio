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
from datetime import datetime, timedelta
from urllib.parse import urlparse

# Load .env file for local development (python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from flask import Flask, abort, jsonify, render_template, request, session
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix

import config
from extensions import init_limiter

import subprocess

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Capture git SHA once at process startup (baked into the running image)
# ---------------------------------------------------------------------------
def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "unknown"

_BUILD_SHA = _git_sha()
_BUILD_TIME = __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


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
    # /__version — deploy fingerprint (no auth required, no secrets exposed)
    # -----------------------------------------------------------------------
    @app.route("/__version")
    def version():
        return jsonify(
            sha=_BUILD_SHA,
            built_at=_BUILD_TIME,
            render_service=os.environ.get("RENDER_SERVICE_NAME", "local"),
        )

    @app.route("/healthz")
    def health():
        try:
            from db import engine
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            if not os.path.isdir(config.UPLOAD_FOLDER) or not os.access(
                config.UPLOAD_FOLDER,
                os.W_OK,
            ):
                raise RuntimeError("Upload storage is not writable.")
        except Exception:
            logger.exception("Health check failed")
            return jsonify(status="unhealthy"), 503
        return jsonify(status="ok"), 200

    # -----------------------------------------------------------------------
    # Upload directory
    # -----------------------------------------------------------------------
    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
    for folder in config.ALBUM_FOLDERS.values():
        os.makedirs(os.path.join(config.UPLOAD_FOLDER, folder), exist_ok=True)
    os.makedirs(os.path.join(config.UPLOAD_FOLDER, "hero"), exist_ok=True)
    os.makedirs(os.path.join(config.UPLOAD_FOLDER, "client_collections"), exist_ok=True)

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
        database.create_default_services()
        if not config.TEST_AUTH_MODE:
            database.synchronize_environment_admin()

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
    app.jinja_env.globals["current_year"] = datetime.now().year

    def whatsapp_url(number):
        digits = "".join(ch for ch in str(number or "") if ch.isdigit())
        if digits.startswith("0"):
            digits = "256" + digits[1:]
        return f"https://wa.me/{digits}" if digits else None

    app.jinja_env.globals["whatsapp_url"] = whatsapp_url

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
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if config.IS_PRODUCTION:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
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
            wants_html = request.accept_mimetypes.accept_html
        except Exception:
            wants_html = True  # safe default — show friendly redirect
        if wants_html:
            flash("Too many requests. Please slow down and try again in a minute.", "error")
            referrer = request.referrer
            if not referrer or urlparse(referrer).netloc != request.host:
                referrer = url_for("public.index")
            return redirect(referrer), 303
        return jsonify(error="Too many requests", retry_after=str(e.description)), 429

    # -----------------------------------------------------------------------
    # Upload too large error handler (413)
    # -----------------------------------------------------------------------
    @app.errorhandler(413)
    def request_entity_too_large(e):
        from flask import flash, redirect, request, url_for
        flash("File(s) too large. Please upload smaller images (max 10 MB each, 100 MB total).", "error")
        referrer = request.referrer
        if not referrer or urlparse(referrer).netloc != request.host:
            referrer = url_for("public.index")
        return redirect(referrer), 303

    @app.errorhandler(500)
    def internal_server_error(e):
        original = getattr(e, "original_exception", None)
        logger.error(
            "Unhandled application error",
            exc_info=(type(original), original, original.__traceback__) if original else True,
        )
        return render_template("errors/500.html"), 500

    # -----------------------------------------------------------------------
    # Blueprint registration
    # -----------------------------------------------------------------------
    from auth import auth
    from admin import admin
    from admin_extended import admin_extended
    from client_gallery import client_gallery
    from public import public
    app.register_blueprint(auth)
    app.register_blueprint(admin)
    app.register_blueprint(admin_extended)
    app.register_blueprint(client_gallery)
    app.register_blueprint(public)

    logger.info(
        "Benjo Moments started | env=%s | TEST_AUTH_MODE=%s | DB=postgresql | limiter_storage=%s",
        config.FLASK_ENV,
        config.TEST_AUTH_MODE,
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
