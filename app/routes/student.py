"""
student.py
──────────
Student self-registration, login, profile editing,
resume upload, bulk ERP import, and placement cell profile view.
"""

import os, io
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, current_app, session)
from app.models.models import db, Student, User
from app.services.auth_service import (placement_cell_required,
                                        hash_password, check_password)

student_bp = Blueprint("student", __name__)


# ── helpers ────────────────────────────────────────────────────────────────
def _int(v):
    try: return int(v) if v else None
    except: return None

def _float(v):
    try: return float(v) if v else None
    except: return None

def _current_student():
    return db.session.get(Student, session.get("student_id"))

def _save_resume(student_id, file_obj):
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    filepath   = os.path.join(upload_dir, f"resume_{student_id}.pdf")
    file_obj.save(filepath)
    try:
        from app.services.resume_parser import parse_resume, save_parsed_resume
        parsed = parse_resume(filepath)
        save_parsed_resume(student_id, filepath, parsed, db.session)
        flash("Resume uploaded and parsed successfully.", "success")
    except Exception as e:
        flash(f"Resume saved but parsing failed: {e}", "warning")


# ── student registration ────────────────────────────────────────────────────
@student_bp.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        erp_id   = request.form.get("erp_id","").strip()
        email    = request.form.get("email","").strip().lower()
        name     = request.form.get("name","").strip()
        password = request.form.get("password","").strip()

        if not all([erp_id, email, name, password]):
            flash("ERP ID, name, email and password are all required.", "danger")
            return redirect(url_for("student.register"))

        if db.session.query(Student).filter(
            (Student.erp_id==erp_id)|(Student.email==email)
        ).first():
            flash("A student with this ERP ID or email already exists.", "danger")
            return redirect(url_for("student.register"))

        student = Student(
            erp_id=erp_id, name=name, email=email,
            branch=request.form.get("branch","").strip() or None,
            year=_int(request.form.get("year")),
            cgpa=_float(request.form.get("cgpa")),
            backlogs=_int(request.form.get("backlogs")) or 0,
            tenth_pct=_float(request.form.get("tenth_pct")),
            twelfth_pct=_float(request.form.get("twelfth_pct")),
            github_url=request.form.get("github_url","").strip() or None,
            linkedin_url=request.form.get("linkedin_url","").strip() or None,
            leetcode_user=request.form.get("leetcode_user","").strip() or None,
            codeforces_user=request.form.get("codeforces_user","").strip() or None,
            codechef_user=request.form.get("codechef_user","").strip() or None,
        )
        db.session.add(student)
        db.session.flush()

        # create user account for student
        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=name,
            role="student",
            drive_id=None,
        )
        db.session.add(user)

        resume_file = request.files.get("resume")
        if resume_file and resume_file.filename.endswith(".pdf"):
            _save_resume(student.id, resume_file)

        db.session.commit()
        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("student/register.html")


# ── student login ───────────────────────────────────────────────────────────
@student_bp.route("/login", methods=["GET","POST"])
def student_login():
    if request.method == "POST":
        email    = request.form.get("email","").strip().lower()
        password = request.form.get("password","")

        user = db.session.query(User).filter_by(
            email=email, role="student", is_active=True
        ).first()

        if not user or not check_password(password, user.password_hash):
            flash("Invalid email or password.", "danger")
            return redirect(url_for("student.student_login"))

        # find the matching student record
        student = db.session.query(Student).filter_by(email=email).first()
        if not student:
            flash("Student profile not found.", "danger")
            return redirect(url_for("student.student_login"))

        session["student_id"]   = student.id
        session["student_name"] = student.name
        session["student_email"]= email
        flash(f"Welcome back, {student.name}!", "success")
        return redirect(url_for("student.my_profile"))

    return render_template("student/student_login.html")


@student_bp.route("/logout")
def student_logout():
    session.pop("student_id", None)
    session.pop("student_name", None)
    session.pop("student_email", None)
    flash("Logged out.", "info")
    return redirect(url_for("student.student_login"))


# ── student own profile ─────────────────────────────────────────────────────
@student_bp.route("/me")
def my_profile():
    if not session.get("student_id"):
        flash("Please log in to view your profile.", "warning")
        return redirect(url_for("student.student_login"))

    student = _current_student()
    if not student:
        flash("Profile not found.", "danger")
        return redirect(url_for("student.student_login"))

    from app.services.keyword_extractor import extract_section_insights
    insights = extract_section_insights(student.resume)
    return render_template("student/my_profile.html",
                           student=student,getattr=getattr, insights=insights)


# ── student edit links ──────────────────────────────────────────────────────
@student_bp.route("/me/edit-links", methods=["POST"])
def edit_links():
    if not session.get("student_id"):
        return redirect(url_for("student.student_login"))

    student = _current_student()
    if not student:
        return redirect(url_for("student.student_login"))

    student.github_url      = request.form.get("github_url","").strip() or None
    student.linkedin_url    = request.form.get("linkedin_url","").strip() or None
    student.leetcode_user   = request.form.get("leetcode_user","").strip() or None
    student.codeforces_user = request.form.get("codeforces_user","").strip() or None
    student.codechef_user   = request.form.get("codechef_user","").strip() or None
    db.session.commit()
    flash("Profile links updated successfully.", "success")
    return redirect(url_for("student.my_profile"))


# ── student resume upload ───────────────────────────────────────────────────
@student_bp.route("/me/upload-resume", methods=["POST"])
def my_upload_resume():
    if not session.get("student_id"):
        return redirect(url_for("student.student_login"))

    student = _current_student()
    resume_file = request.files.get("resume")
    if not resume_file or not resume_file.filename.endswith(".pdf"):
        flash("Please upload a valid PDF file.", "danger")
        return redirect(url_for("student.my_profile"))

    _save_resume(student.id, resume_file)
    return redirect(url_for("student.my_profile"))


# ── placement cell: view student ────────────────────────────────────────────
@student_bp.route("/<int:student_id>")
@placement_cell_required
def profile(student_id):
    student = db.session.get(Student, student_id)
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("dashboard.students"))
    from app.services.keyword_extractor import extract_section_insights
    insights = extract_section_insights(student.resume)
    return render_template("student/profile.html",
                           student=student, insights=insights)


# ── placement cell: upload resume for student ───────────────────────────────
@student_bp.route("/<int:student_id>/upload-resume", methods=["POST"])
@placement_cell_required
def upload_resume(student_id):
    student = db.session.get(Student, student_id)
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("dashboard.students"))
    resume_file = request.files.get("resume")
    if not resume_file or not resume_file.filename.endswith(".pdf"):
        flash("Please upload a valid PDF.", "danger")
        return redirect(url_for("student.profile", student_id=student_id))
    _save_resume(student_id, resume_file)
    return redirect(url_for("student.profile", student_id=student_id))


# ── placement cell: refresh signals ────────────────────────────────────────
@student_bp.route("/<int:student_id>/refresh", methods=["POST"])
@placement_cell_required
def refresh_signals(student_id):
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
    else:
        flash("No GitHub URL linked — skipping GitHub refresh.", "warning")

    codolio = student.leetcode_user or student.codechef_user
    if codolio:
        try:
            from app.services.cp_fetcher import fetch_cp_signals, save_cp_signals
            signals = fetch_cp_signals(codolio, student.codeforces_user)
            save_cp_signals(student.id, signals, db.session)
            fetched.append("CP platforms")
        except Exception as e:
            flash(f"CP fetch failed: {e}", "warning")
    else:
        flash("No CP platform linked — skipping CP refresh.", "warning")

    if fetched:
        flash(f"Refreshed: {', '.join(fetched)}.", "success")
    return redirect(url_for("student.profile", student_id=student_id))


# ── bulk CSV import ─────────────────────────────────────────────────────────
@student_bp.route("/import", methods=["GET","POST"])
@placement_cell_required
def bulk_import():
    result = None
    sample_csv = None

    if request.method == "POST":
        if "sample" in request.form:
            from app.services.erp_importer import generate_sample_csv
            sample_csv = generate_sample_csv()
            return render_template("student/bulk_import.html",
                                   result=None, sample_csv=sample_csv)

        csv_file = request.files.get("csv_file")

        # edge case: no file uploaded
        if not csv_file or csv_file.filename == "":
            flash("No file selected. Please upload a CSV file.", "danger")
            return redirect(url_for("student.bulk_import"))

        # edge case: wrong file type
        if not csv_file.filename.endswith(".csv"):
            flash("Invalid file type. Please upload a .csv file.", "danger")
            return redirect(url_for("student.bulk_import"))

        raw = csv_file.stream.read()

        # edge case: empty file
        if not raw.strip():
            flash("The uploaded CSV file is empty.", "danger")
            return redirect(url_for("student.bulk_import"))

        update = request.form.get("update_existing") == "on"
        stream = io.StringIO(raw.decode("utf-8-sig"))

        from app.services.erp_importer import import_from_csv
        result = import_from_csv(stream, db.session, update_existing=update)

        # edge case: missing required columns
        if result["errors"] and result["imported"] == 0 and result["updated"] == 0:
            for err in result["errors"][:3]:
                flash(f"Row {err['row']}: {err['reason']}", "danger")
            return render_template("student/bulk_import.html",
                                   result=result, sample_csv=sample_csv)

        for err in result["errors"][:3]:
            flash(f"Row {err['row']}: {err['reason']}", "warning")

        flash(
            f"Import complete — {result['imported']} new, "
            f"{result['updated']} updated, {result['skipped']} skipped.",
            "success"
        )

    return render_template("student/bulk_import.html",
                           result=result, sample_csv=sample_csv)
