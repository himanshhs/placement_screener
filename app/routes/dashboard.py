import json
from flask import Blueprint, render_template, session, redirect, url_for, flash
from app.models.models import db, Drive, DriveScore, Student
from app.services.auth_service import login_required

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    if session.get("user_role") == "placement_cell":
        drives = db.session.query(Drive).order_by(Drive.created_at.desc()).all()
        students_count = db.session.query(Student).count()
        return render_template("dashboard/index.html",
                               drives=drives,
                               students_count=students_count)
    else:
        # HR — redirect straight to their drive
        return redirect(url_for("dashboard.drive_detail",
                                drive_id=session.get("drive_id")))


@dashboard_bp.route("/drives/<int:drive_id>")
@login_required
def drive_detail(drive_id):
    # HR can only see their own drive
    if session.get("user_role") == "company_hr" and session.get("drive_id") != drive_id:
        flash("Access restricted.", "danger")
        return redirect(url_for("dashboard.index"))

    drive = db.session.get(Drive, drive_id)
    if not drive:
        flash("Drive not found.", "danger")
        return redirect(url_for("dashboard.index"))

    scores = (
        db.session.query(DriveScore)
        .filter_by(drive_id=drive_id)
        .order_by(DriveScore.rank)
        .all()
    )

    # parse JSON fields for template
    for ds in scores:
        ds.matched_list = json.loads(ds.matched_skills or "[]")
        ds.missing_list = json.loads(ds.missing_skills or "[]")
        ds.flags_list   = json.loads(ds.flags          or "[]")
        ds.boosts_dict  = json.loads(ds.boost_applied  or "{}")

    shortlisted = [s for s in scores if s.is_shortlisted]
    all_scored  = scores

    return render_template("dashboard/drive_detail.html",
                           drive=drive,
                           shortlisted=shortlisted,
                           all_scored=all_scored)


@dashboard_bp.route("/students")
@login_required
def students():
    if session.get("user_role") != "placement_cell":
        flash("Access restricted.", "danger")
        return redirect(url_for("dashboard.index"))

    all_students = db.session.query(Student).order_by(Student.name).all()
    return render_template("dashboard/students.html", students=all_students)
