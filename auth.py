"""
Authentication module for Benjo Moments Photography System.
Handles login, logout, and session protection.

TEST_AUTH_MODE=true  → any non-empty email/password accepted (dev/demo).
  If TEST_PIN env var is set, password must equal TEST_PIN.
TEST_AUTH_MODE=false → credentials validated against the users table (production).

Phase 7: rate limit applied on login; Phase 8: permanent session + TEST_PIN.
"""
import logging
import secrets
from datetime import timedelta
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

import config
import database
from extensions import limiter

logger = logging.getLogger(__name__)
auth = Blueprint("auth", __name__)


def login_required(f):
    """Decorator to protect routes that require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


@auth.route("/login", methods=["GET", "POST"])
@auth.route("/admin/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    """Handle user login with rate limiting (Phase 7)."""
    if "user_id" in session:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "error")
            return render_template("auth/login.html")

        if config.TEST_AUTH_MODE:
            # -------------------------------------------------------------------
            # TEST AUTH MODE: accept any non-empty credentials (Phase 8 hardening)
            # If TEST_PIN is set, password must match it exactly.
            # -------------------------------------------------------------------
            if config.TEST_PIN and password != config.TEST_PIN:
                logger.warning("TEST_AUTH_MODE: wrong TEST_PIN attempt for %s", email)
                flash("Invalid credentials.", "error")
                return render_template("auth/login.html")

            logger.debug("TEST_AUTH_MODE active — bypass for %s", email)
            display_name = (
                email.split("@")[0].replace(".", " ").replace("_", " ").title()
            )
            session.clear()
            session.permanent = True
            session["user_id"] = 1
            session["user_name"] = display_name
            session["user_email"] = email
            session["user_role"] = "admin"
            session["_csrf_token"] = secrets.token_urlsafe(32)
            flash(f"Welcome, {display_name}! (Test mode — any credentials accepted)", "success")
            return redirect(url_for("admin.dashboard"))
        else:
            # -------------------------------------------------------------------
            # PRODUCTION MODE: validate against DB with Werkzeug password hash
            # -------------------------------------------------------------------
            user = database.get_user_by_email(email)
            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session.permanent = True
                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                session["user_email"] = user["email"]
                session["user_role"] = user.get("role", "admin")
                session["_csrf_token"] = secrets.token_urlsafe(32)
                flash(f"Welcome back, {user['name']}!", "success")
                return redirect(url_for("admin.dashboard"))
            else:
                logger.warning("Failed login attempt for email: %s", email)
                flash("Invalid email or password.", "error")

    return render_template("auth/login.html")


@auth.route("/logout", methods=["POST"])
@login_required
def logout():
    """Handle user logout."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
