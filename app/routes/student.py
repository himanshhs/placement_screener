"""
student.py
──────────
Routes for student self-registration, resume upload,
profile view, and placement-cell bulk import.
"""

import os
import io
from flask import (Blueprint, render_template, request,
                   redirect, url_for, flash, current_app, session)
from app.models.models import db, Student
from app.services.auth_service import login_required, placement_cell_required

student_bp = Blueprint("student", __name__)


# ── Student self-registration ──────────────────────────────────────────────

@student_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        erp_id = request.form.get("erp_id", "").strip()
        email  = request.form.get("email",  "").strip().lower()
        name   = request.form.get("name",   "").strip()

        if not erp_id or not email or not name:
            flash("ERP ID, name and email are required.", "danger")
            return redirect(url_for("student.register"))

        existing = db.session.query(Student).filter(
            (Student.erp_id == erp_id) | (Student.email == email)
        ).first()

        if existing:
            flash("A student with this ERP ID or email already exists.", "danger")
            return redirect(url_for("student.register"))

        student = Student(
            erp_id          = erp_id,
            name            = name,
            email           = email,
            branch          = request.form.get("branch",   "").strip() or None,
            year            = _int(request.form.get("year")),
            cgpa            = _float(request.form.get("cgpa")),
            backlogs        = _int(request.form.get("backlogs")) or 0,
            tenth_pct       = _float(request.form.get("tenth_pct")),
            twelfth_pct     = _float(request.form.get("twelfth_pct")),
            github_url      = request.form.get("github_url",      "").strip() or None,
            linkedin_url    = request.form.get("linkedin_url",    "").strip() or None,
            leetcode_user   = request.form.get("leetcode_user",   "").strip() or None,
            codeforces_user = request.form.get("codeforces_user", "").strip() or None,
            codechef_user   = request.form.get("codechef_user",   "").strip() or None,
        )
        db.session.add(student)
        db.session.commit()

        # handle resume upload right away if provided
        resume_file = request.files.get("resume")
        if resume_file and resume_file.filename.endswith(".pdf"):
            _save_and_parse_resume(student.id, resume_file)

        flash("Registration successful! Your profile has been saved.", "success")
        return redirect(url_for("student.profile", student_id=student.id))

    return render_template("student/register.html")


# ── Resume upload (standalone) ─────────────────────────────────────────────

@student_bp.route("/<int:student_id>/upload-resume", methods=["POST"])
def upload_resume(student_id):
    student = db.session.get(Student, student_id)
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("dashboard.students"))

    resume_file = request.files.get("resume")
    if not resume_file or not resume_file.filename.endswith(".pdf"):
        flash("Please upload a valid PDF file.", "danger")
        return redirect(url_for("student.profile", student_id=student_id))

    _save_and_parse_resume(student_id, resume_file)
    flash("Resume uploaded and parsed successfully.", "success")
    return redirect(url_for("student.profile", student_id=student_id))


# ── Refresh external signals ───────────────────────────────────────────────

@student_bp.route("/<int:student_id>/refresh", methods=["POST"])
@placement_cell_required
def refresh_signals(student_id):
    """Re-fetch GitHub and CP signals for a student."""
    student = db.session.get(Student, student_id)
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("dashboard.students"))

    fetched = []

    if student.github_url:
        try:
            from app.services.github_fetcher import fetch_github_signals, save_github_signals
            signals = fetch_github_signals(student.github_url)
            save_github_signals(student.id, signals, db.session)
            fetched.append("GitHub")
        except Exception as e:
            flash(f"GitHub fetch failed: {e}", "warning")

    codolio = student.leetcode_user or student.codechef_user
    if codolio:
        try:
            from app.services.cp_fetcher import fetch_cp_signals, save_cp_signals
            signals = fetch_cp_signals(codolio, student.codeforces_user)
            save_cp_signals(student.id, signals, db.session)
            fetched.append("CP platforms")
        except Exception as e:
            flash(f"CP fetch failed: {e}", "warning")

    if fetched:
        flash(f"Refreshed: {', '.join(fetched)}.", "success")
    else:
        flash("No external profiles linked — nothing to refresh.", "warning")

    return redirect(url_for("student.profile", student_id=student_id))


# ── Student profile view ───────────────────────────────────────────────────

@student_bp.route("/<int:student_id>")
@placement_cell_required
def profile(student_id):
    student = db.session.get(Student, student_id)
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("dashboard.students"))
    return render_template("student/profile.html", student=student)


# ── ERP CSV bulk import ────────────────────────────────────────────────────

@student_bp.route("/import", methods=["GET", "POST"])
@placement_cell_required
def bulk_import():
    result = None
    sample_csv = None

    if request.method == "POST":
        if "sample" in request.form:
            from app.services.erp_importer import generate_sample_csv
            sample_csv = generate_sample_csv()
        else:
            csv_file = request.files.get("csv_file")
            if not csv_file or not csv_file.filename.endswith(".csv"):
                flash("Please upload a valid CSV file.", "danger")
                return redirect(url_for("student.bulk_import"))

            update = request.form.get("update_existing") == "on"

            from app.services.erp_importer import import_from_csv
            stream = io.StringIO(csv_file.stream.read().decode("utf-8-sig"))
            result = import_from_csv(stream, db.session, update_existing=update)

            if result["errors"]:
                for err in result["errors"][:5]:
                    flash(f"Row {err['row']}: {err['reason']}", "warning")

            flash(
                f"Import complete — {result['imported']} new, "
                f"{result['updated']} updated, {result['skipped']} skipped.",
                "success"
            )

    return render_template("student/bulk_import.html",
                           result=result, sample_csv=sample_csv)


# ── Helpers ────────────────────────────────────────────────────────────────

def _int(val):
    try: return int(val) if val else None
    except (ValueError, TypeError): return None

def _float(val):
    try: return float(val) if val else None
    except (ValueError, TypeError): return None

def _save_and_parse_resume(student_id: int, file_obj):
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    filename   = f"resume_{student_id}.pdf"
    filepath   = os.path.join(upload_dir, filename)
    file_obj.save(filepath)
    try:
        from app.services.resume_parser import parse_resume, save_parsed_resume
        parsed = parse_resume(filepath)
        save_parsed_resume(student_id, filepath, parsed, db.session)
    except Exception as e:
        flash(f"Resume saved but parsing failed: {e}", "warning")
