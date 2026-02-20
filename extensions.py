"""
extensions.py — Shared Flask extension instances.

Import here to avoid circular imports when blueprints need the limiter.
The limiter is initialised (bound to the Flask app) in app.py via init_limiter(app).
"""
import os

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ---------------------------------------------------------------------------
# Rate-limit storage selection (Phase 9)
# Priority: RATELIMIT_STORAGE_URI > REDIS_URL > memory://
# ---------------------------------------------------------------------------
def _storage_uri() -> str:
    explicit = os.environ.get("RATELIMIT_STORAGE_URI")
    if explicit:
        return explicit
    redis = os.environ.get("REDIS_URL")
    if redis:
        return redis
    return "memory://"


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_storage_uri(),
    default_limits=[],          # no global default — apply per-route only
    headers_enabled=True,       # send X-RateLimit-* headers to client
)


def init_limiter(app):
    """Bind the limiter to the Flask app."""
    limiter.init_app(app)
