"""
auth_service.py
───────────────
Handles password hashing, session management, and role checking.
Uses werkzeug (bundled with Flask) for password hashing — no extra deps.
"""

import hashlib
import os
from datetime import datetime
from functools import wraps
from flask import session, redirect, url_for, flash


def hash_password(password: str) -> str:
    """SHA-256 hash with a random salt. Format: salt$hash"""
    salt = os.urandom(16).hex()
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${hashed}"


def check_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored salt$hash string."""
    try:
        salt, hashed = stored_hash.split("$")
        return hashlib.sha256((salt + password).encode()).hexdigest() == hashed
    except Exception:
        return False


def login_user(user, db_session):
    """Store user info in Flask session."""
    session["user_id"]   = user.id
    session["user_role"] = user.role
    session["user_name"] = user.full_name or user.email
    session["drive_id"]  = user.drive_id  # None for placement cell
    user.last_login = datetime.utcnow()
    db_session.commit()


def logout_user():
    session.clear()


def current_user_id():
    return session.get("user_id")


def current_role():
    return session.get("user_role")


def is_placement_cell():
    return session.get("user_role") == "placement_cell"


def is_company_hr():
    return session.get("user_role") == "company_hr"


# ── Route decorators ───────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user_id():
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def placement_cell_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user_id():
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        if not is_placement_cell():
            flash("Access restricted to placement cell.", "danger")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)
    return decorated


def create_default_admin(db_session):
    """
    Creates a default placement cell account if none exists.
    Called once on app startup.
    Credentials: admin@placement.com / admin123
    CHANGE THIS IN PRODUCTION.
    """
    from app.models.models import User
    existing = db_session.query(User).filter_by(role="placement_cell").first()
    if not existing:
        admin = User(
            email         = "admin@placement.com",
            password_hash = hash_password("admin123"),
            full_name     = "Placement Cell Admin",
            role          = "placement_cell",
        )
        db_session.add(admin)
        db_session.commit()
        print("  Default admin created: admin@placement.com / admin123")
