"""
Benjo Moments Photography System
Main Flask Application Entry Point

Run with: python app.py
"""
import os
from flask import Flask
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
    print(f"\n  Admin Login:")
    print(f"    Email: {config.DEFAULT_ADMIN_EMAIL}")
    print(f"    Password: {config.DEFAULT_ADMIN_PASSWORD}")
    print("\n  Admin Dashboard: http://127.0.0.1:5000/admin")
    print("="*60 + "\n")
    app.run(debug=True)
