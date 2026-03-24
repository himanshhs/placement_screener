import os, json
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from app.models.models import db, Drive, DriveScore, Student
from app.services.auth_service import placement_cell_required, login_required
from app.services.jd_analyzer import suggest_weights, extract_jd_from_pdf, summarise_suggestions

drive_bp = Blueprint("drive", __name__)


@drive_bp.route("/new", methods=["GET", "POST"])
@placement_cell_required
def new_drive():
    if request.method == "POST":
        # ── JD text ──────────────────────────────────────────────────────
        jd_text = request.form.get("jd_text", "").strip()
        jd_file = request.files.get("jd_file")
        jd_path = None

        if jd_file and jd_file.filename:
            filename = f"jd_{jd_file.filename}"
            jd_path  = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            jd_file.save(jd_path)
            if not jd_text:
                jd_text = extract_jd_from_pdf(jd_path)

        if not jd_text:
            flash("Please provide a JD — either paste text or upload a PDF.", "danger")
            return redirect(url_for("drive.new_drive"))

        # ── Auto-suggest weights ──────────────────────────────────────────
        weights  = suggest_weights(jd_text)
        notes    = summarise_suggestions(weights)

        # store in session so the preview page can use them
        session["pending_drive"] = {
            "company_name":   request.form.get("company_name", "").strip(),
            "role_title":     request.form.get("role_title", "").strip(),
            "jd_text":        jd_text,
            "jd_file_path":   jd_path,
            "shortlist_count": int(request.form.get("shortlist_count", 50)),
            "weights":        weights,
            "notes":          notes,
        }
        return redirect(url_for("drive.configure_drive"))

    return render_template("dashboard/new_drive.html")


@drive_bp.route("/configure", methods=["GET", "POST"])
@placement_cell_required
def configure_drive():
    """
    Show auto-suggested weights as sliders.
    Placement cell adjusts and confirms.
    """
    pending = session.get("pending_drive")
    if not pending:
        return redirect(url_for("drive.new_drive"))

    if request.method == "POST":
        # read adjusted weights from sliders
        def fw(name, default):
            try:
                return round(float(request.form.get(name, default)), 4)
            except (ValueError, TypeError):
                return default

        drive = Drive(
            company_name     = pending["company_name"],
            role_title       = pending["role_title"],
            jd_text          = pending["jd_text"],
            jd_file_path     = pending.get("jd_file_path"),
            shortlist_count  = pending["shortlist_count"],

            weight_skills        = fw("weight_skills",        0.28),
            weight_projects      = fw("weight_projects",      0.22),
            weight_experience    = fw("weight_experience",    0.15),
            weight_github        = fw("weight_github",        0.13),
            weight_cp            = fw("weight_cp",            0.08),
            weight_cgpa          = fw("weight_cgpa",          0.04),

            boost_startup_founder = fw("boost_startup_founder", 1.0),
            boost_ml_internship   = fw("boost_ml_internship",   1.0),
            boost_open_source     = fw("boost_open_source",     1.0),

            min_cgpa         = fw("min_cgpa",    0.0) or None,
            max_backlogs     = int(request.form.get("max_backlogs", 99)),
            allowed_branches = json.dumps(
                [b.strip() for b in request.form.get("allowed_branches", "").split(",") if b.strip()]
            ),
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
    from app.services.scoring_engine import run_drive_scoring
    result = run_drive_scoring(drive_id, db.session)
    if "error" in result:
        flash(result["error"], "danger")
    else:
        flash(
            f"Scoring complete — {result['scored']} scored, "
            f"{result['excluded']} excluded, {result['errors']} errors.",
            "success"
        )
    return redirect(url_for("dashboard.drive_detail", drive_id=drive_id))


@drive_bp.route("/<int:drive_id>/export")
@login_required
def export_shortlist(drive_id):
    """Export shortlisted students as Excel."""
    import openpyxl
    from flask import send_file
    import io

    drive = db.session.get(Drive, drive_id)
    if not drive:
        flash("Drive not found.", "danger")
        return redirect(url_for("dashboard.index"))

    # HR can only export their own drive
    if session.get("user_role") == "company_hr" and session.get("drive_id") != drive_id:
        flash("Access restricted.", "danger")
        return redirect(url_for("dashboard.index"))

    scores = (
        db.session.query(DriveScore)
        .filter_by(drive_id=drive_id, is_shortlisted=True)
        .order_by(DriveScore.rank)
        .all()
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Shortlist"
    headers = [
        "Rank", "Name", "ERP ID", "Branch", "CGPA", "Email",
        "Score", "Skills", "Projects", "Internships",
        "Experience", "Certifications", "GitHub", "CP",
        "Matched Skills", "Missing Skills", "Flags"
    ]
    ws.append(headers)

    for ds in scores:
        s = ds.student
        ws.append([
            ds.rank, s.name, s.erp_id, s.branch, s.cgpa, s.email,
            ds.final_score,
            ds.score_skills, ds.score_projects,
            getattr(ds, "score_internships", ""),
            ds.score_experience,
            getattr(ds, "score_certifications", ""),
            ds.score_github, ds.score_cp,
            ", ".join(json.loads(ds.matched_skills or "[]")),
            ", ".join(json.loads(ds.missing_skills  or "[]")),
            ", ".join(json.loads(ds.flags           or "[]")),
        ])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"shortlist_{drive.company_name.replace(' ','_')}.xlsx"
    return send_file(buf, as_attachment=True,
                     download_name=filename,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
