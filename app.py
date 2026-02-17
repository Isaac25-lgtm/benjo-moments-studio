"""
Benjo Moments Photography System
Main Flask Application Entry Point

Run with: python app.py
"""
import os
import hmac
import secrets
from flask import Flask, abort, request, session
import config
import database
from auth import auth
from admin import admin
from public import public

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
    app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
    app.config['SESSION_COOKIE_HTTPONLY'] = config.SESSION_COOKIE_HTTPONLY
    app.config['SESSION_COOKIE_SAMESITE'] = config.SESSION_COOKIE_SAMESITE
    app.config['SESSION_COOKIE_SECURE'] = config.SESSION_COOKIE_SECURE

    # Ensure runtime directories exist
    db_dir = os.path.dirname(config.DATABASE_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

    def generate_csrf_token():
        token = session.get('_csrf_token')
        if not token:
            token = secrets.token_urlsafe(32)
            session['_csrf_token'] = token
        return token

    app.jinja_env.globals['csrf_token'] = generate_csrf_token

    @app.before_request
    def protect_against_csrf():
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            token = request.form.get(config.CSRF_TOKEN_FIELD) or request.headers.get('X-CSRF-Token')
            session_token = session.get('_csrf_token')
            if not session_token or not token or not hmac.compare_digest(session_token, token):
                abort(400, description='Invalid CSRF token. Refresh the page and try again.')

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        return response
    
    # Register blueprints
    app.register_blueprint(auth)
    app.register_blueprint(admin)
    app.register_blueprint(public)
    
    # Initialize database on first run
    with app.app_context():
        database.init_db()
        database.create_default_admin()
        database.init_default_settings()
        database.create_default_pricing_packages()
    
    return app

if __name__ == '__main__':
    app = create_app()
    print("\n" + "="*60)
    print("  BENJO MOMENTS PHOTOGRAPHY SYSTEM")
    print("="*60)
    print(f"\n  Server running at: http://127.0.0.1:5000")
    print(f"\n  Admin Login: http://127.0.0.1:5000/login")
    if not config.DEFAULT_ADMIN_PASSWORD:
        print("  Note: DEFAULT_ADMIN_PASSWORD is not configured.")
    print("  Admin Dashboard: http://127.0.0.1:5000/admin")
    print("="*60 + "\n")
    app.run(debug=not config.IS_PRODUCTION)
