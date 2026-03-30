"""
drive.py
─────────
Drive creation, weight config, scoring, export and deletion.
All edge cases handled gracefully — no 500 crashes.
"""

import os, json
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session, current_app, send_file)
from app.models.models import db, Drive, DriveScore, Student
from app.services.auth_service import placement_cell_required, login_required
from app.services.jd_analyzer import (suggest_weights, extract_jd_from_pdf,
                                       summarise_suggestions)

drive_bp = Blueprint("drive", __name__)


@drive_bp.route("/new", methods=["GET","POST"])
@placement_cell_required
def new_drive():
    if request.method == "POST":
        company = request.form.get("company_name","").strip()
        role    = request.form.get("role_title","").strip()

        if not company:
            flash("Company name is required.", "danger")
            return redirect(url_for("drive.new_drive"))

        jd_text = request.form.get("jd_text","").strip()
        jd_file = request.files.get("jd_file")
        jd_path = None

        if jd_file and jd_file.filename:
            filename = f"jd_{jd_file.filename}"
            jd_path  = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            jd_file.save(jd_path)
            if not jd_text:
                try:
                    jd_text = extract_jd_from_pdf(jd_path)
                except Exception as e:
                    flash(f"Could not read JD PDF: {e}. Try pasting text instead.", "warning")

        # edge case: invalid / empty JD — use balanced defaults, don't crash
        if not jd_text or len(jd_text.strip()) < 20:
            flash("JD text is too short or missing — using balanced default weights. "
                  "You can adjust them on the next screen.", "warning")
            jd_text = jd_text or ""

        weights = suggest_weights(jd_text)
        notes   = summarise_suggestions(weights)

        try:
            shortlist_count = int(request.form.get("shortlist_count", 50))
        except (ValueError, TypeError):
            shortlist_count = 50

        session["pending_drive"] = {
            "company_name":    company,
            "role_title":      role,
            "jd_text":         jd_text,
            "jd_file_path":    jd_path,
            "shortlist_count": shortlist_count,
            "weights":         weights,
            "notes":           notes,
        }
        return redirect(url_for("drive.configure_drive"))

    return render_template("dashboard/new_drive.html")


@drive_bp.route("/configure", methods=["GET","POST"])
@placement_cell_required
def configure_drive():
    pending = session.get("pending_drive")
    if not pending:
        flash("Session expired. Please start again.", "warning")
        return redirect(url_for("drive.new_drive"))

    if request.method == "POST":
        def fw(name, default):
            try: return round(float(request.form.get(name, default)), 4)
            except: return default

        drive = Drive(
            company_name     = pending["company_name"],
            role_title       = pending["role_title"],
            jd_text          = pending["jd_text"],
            jd_file_path     = pending.get("jd_file_path"),
            shortlist_count  = pending["shortlist_count"],
            weight_skills    = fw("weight_skills",    0.28),
            weight_projects  = fw("weight_projects",  0.22),
            weight_experience= fw("weight_experience",0.15),
            weight_github    = fw("weight_github",    0.13),
            weight_cp        = fw("weight_cp",        0.08),
            weight_cgpa      = fw("weight_cgpa",      0.04),
            boost_startup_founder = fw("boost_startup_founder", 1.0),
            boost_ml_internship   = fw("boost_ml_internship",   1.0),
            boost_open_source     = fw("boost_open_source",     1.0),
            min_cgpa         = fw("min_cgpa", 0.0) or None,
            max_backlogs     = int(request.form.get("max_backlogs", 99)),
            allowed_branches = json.dumps([
                b.strip() for b in
                request.form.get("allowed_branches","").split(",")
                if b.strip()
            ]),
        )
        db.session.add(drive)
        db.session.commit()
        session.pop("pending_drive", None)
        flash(f"Drive created for {drive.company_name}.", "success")
        return redirect(url_for("dashboard.drive_detail", drive_id=drive.id))

    return render_template("dashboard/configure_drive.html", pending=pending)


@drive_bp.route("/<int:drive_id>/run", methods=["POST"])
@placement_cell_required
def run_scoring(drive_id):
    drive = db.session.get(Drive, drive_id)
    if not drive:
        flash("Drive not found.", "danger")
        return redirect(url_for("dashboard.index"))

    # edge case: no students in DB
    total_students = db.session.query(Student).count()
    if total_students == 0:
        flash("No students in the database. Import students first before scoring.", "warning")
        return redirect(url_for("dashboard.drive_detail", drive_id=drive_id))

    # edge case: no JD text
    if not drive.jd_text or len(drive.jd_text.strip()) < 10:
        flash("This drive has no job description — scores will be based on "
              "GitHub, CP, and CGPA signals only.", "warning")

    try:
        from app.services.scoring_engine import run_drive_scoring
        result = run_drive_scoring(drive_id, db.session)

        if "error" in result:
            flash(result["error"], "danger")
        elif result["scored"] == 0 and result["excluded"] == total_students:
            flash(
                f"No eligible students found. All {total_students} students were "
                f"excluded by the eligibility filters (CGPA, backlogs, branch). "
                f"Try relaxing the filters.", "warning"
            )
        else:
            flash(
                f"Scoring complete — {result['scored']} scored, "
                f"{result['excluded']} excluded by filters, "
                f"{result['errors']} errors.", "success"
            )
    except Exception as e:
        flash(f"Scoring failed: {e}", "danger")

    return redirect(url_for("dashboard.drive_detail", drive_id=drive_id))


@drive_bp.route("/<int:drive_id>/delete", methods=["POST"])
@placement_cell_required
def delete_drive(drive_id):
    drive = db.session.get(Drive, drive_id)
    if not drive:
        flash("Drive not found.", "danger")
        return redirect(url_for("dashboard.index"))

    company = drive.company_name
    # delete scores first (FK constraint)
    DriveScore.query.filter_by(drive_id=drive_id).delete()
    db.session.delete(drive)
    db.session.commit()
    flash(f"Drive for {company} deleted.", "success")
    return redirect(url_for("dashboard.index"))


@drive_bp.route("/<int:drive_id>/export")
@login_required
def export_shortlist(drive_id):
    import openpyxl, io as _io
    from flask import send_file

    drive = db.session.get(Drive, drive_id)
    if not drive:
        flash("Drive not found.", "danger")
        return redirect(url_for("dashboard.index"))

    if session.get("user_role") == "company_hr" and session.get("drive_id") != drive_id:
        flash("Access restricted.", "danger")
        return redirect(url_for("dashboard.index"))

    scores = (
        db.session.query(DriveScore)
        .filter_by(drive_id=drive_id, is_shortlisted=True)
        .order_by(DriveScore.rank)
        .all()
    )

    if not scores:
        flash("No shortlisted students to export. Run scoring first.", "warning")
        return redirect(url_for("dashboard.drive_detail", drive_id=drive_id))

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Shortlist"
    ws.append([
        "Rank","Name","ERP ID","Branch","CGPA","Email",
        "Final Score","Skills","Projects","Internships",
        "Experience","GitHub","CP","CGPA Score",
        "Matched Keywords","Missing Keywords","Flags","Authenticity"
    ])
    for ds in scores:
        s = ds.student
        cp_auth = ""
        if s.cp_signal:
            cp_auth = "FLAGGED" if s.cp_signal.flag_suspicious else "OK"
        ws.append([
            ds.rank, s.name, s.erp_id, s.branch, s.cgpa, s.email,
            round(ds.final_score, 2),
            round(ds.score_skills, 2), round(ds.score_projects, 2),
            round(getattr(ds,"score_internships",0) or 0, 2),
            round(ds.score_experience, 2),
            round(ds.score_github, 2), round(ds.score_cp, 2),
            round(ds.score_cgpa, 2),
            ", ".join(json.loads(ds.matched_skills or "[]")),
            ", ".join(json.loads(ds.missing_skills  or "[]")),
            ", ".join(json.loads(ds.flags           or "[]")),
            cp_auth,
        ])

    buf = _io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"shortlist_{drive.company_name.replace(' ','_')}.xlsx"
    return send_file(buf, as_attachment=True,
                     download_name=filename,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
