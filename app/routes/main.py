from flask import Blueprint, redirect, url_for, session
main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard.index"))
    return redirect(url_for("auth.login"))
