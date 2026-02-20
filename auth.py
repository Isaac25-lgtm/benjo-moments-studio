"""
Authentication module for Benjo Moments Photography System.
Handles login, logout, and session protection.

TEST_AUTH_MODE=true  → any non-empty email/password is accepted (dev/demo).
TEST_AUTH_MODE=false → credentials validated against the users table.
"""
import logging
import secrets
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

import config
import database

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
def login():
    """Handle user login."""
    if "user_id" in session:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "error")
            return render_template("auth/login.html")

        if config.TEST_AUTH_MODE:
            # ---------------------------------------------------------------
            # TEST AUTH MODE: accept any non-empty credentials
            # ---------------------------------------------------------------
            logger.debug("TEST_AUTH_MODE active — bypassing credential check for %s", email)
            display_name = (
                email.split("@")[0].replace(".", " ").replace("_", " ").title()
            )
            session.clear()
            session["user_id"] = 1
            session["user_name"] = display_name
            session["user_email"] = email
            session["user_role"] = "admin"
            session["_csrf_token"] = secrets.token_urlsafe(32)
            flash(f"Welcome, {display_name}! (Test mode — any credentials accepted)", "success")
            return redirect(url_for("admin.dashboard"))
        else:
            # ---------------------------------------------------------------
            # PRODUCTION MODE: validate against DB
            # ---------------------------------------------------------------
            user = database.get_user_by_email(email)
            if user and check_password_hash(user["password_hash"], password):
                session.clear()
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
