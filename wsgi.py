"""
WSGI entry point for production deployment.
Used by Gunicorn on Render.
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
