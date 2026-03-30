from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models.models import db, User
from app.services.auth_service import hash_password, check_password, login_user, logout_user

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email    = request.form.get("email","").strip().lower()
        password = request.form.get("password","")

        user = db.session.query(User).filter_by(
            email=email, is_active=True
        ).first()

        if not user or not check_password(password, user.password_hash):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html")

        # student role — redirect to student portal
        if user.role == "student":
            from app.models.models import Student
            student = db.session.query(Student).filter_by(email=email).first()
            if student:
                session["student_id"]    = student.id
                session["student_name"]  = student.name
                session["student_email"] = email
                return redirect(url_for("student.my_profile"))
            flash("Student profile not found.", "danger")
            return render_template("auth/login.html")

        login_user(user, db.session)
        if user.role == "placement_cell":
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("dashboard.drive_detail",
                                drive_id=user.drive_id))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/users/create", methods=["GET","POST"])
def create_hr_user():
    if session.get("user_role") != "placement_cell":
        flash("Access restricted.", "danger")
        return redirect(url_for("auth.login"))

    from app.models.models import Drive
    drives = db.session.query(Drive).all()

    if request.method == "POST":
        email    = request.form.get("email","").strip().lower()
        name     = request.form.get("full_name","").strip()
        password = request.form.get("password","")
        drive_id = request.form.get("drive_id", type=int)

        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("auth/create_hr.html", drives=drives)

        if db.session.query(User).filter_by(email=email).first():
            flash("Email already exists.", "danger")
            return render_template("auth/create_hr.html", drives=drives)

        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=name,
            role="company_hr",
            drive_id=drive_id,
        )
        db.session.add(user)
        db.session.commit()
        flash(f"HR login created for {email}.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/create_hr.html", drives=drives)
