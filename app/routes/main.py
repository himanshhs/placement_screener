from flask import Blueprint, render_template
main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    return "<h2>Placement Screener — up and running</h2>"
