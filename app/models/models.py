from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# ─────────────────────────────────────────────
# STUDENT  (synced from college ERP)
# ─────────────────────────────────────────────
class Student(db.Model):
    __tablename__ = "students"

    id            = db.Column(db.Integer, primary_key=True)
    erp_id        = db.Column(db.String(32), unique=True, nullable=False)   # college roll / PRN
    name          = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    branch        = db.Column(db.String(60))    # CSE, IT, ECE …
    year          = db.Column(db.Integer)        # 1–4
    cgpa          = db.Column(db.Float)
    backlogs      = db.Column(db.Integer, default=0)
    tenth_pct     = db.Column(db.Float)
    twelfth_pct   = db.Column(db.Float)

    # external profile links (filled by student on registration)
    github_url    = db.Column(db.String(200))
    linkedin_url  = db.Column(db.String(200))
    leetcode_user = db.Column(db.String(80))
    codeforces_user = db.Column(db.String(80))
    codechef_user = db.Column(db.String(80))

    # special tags — set by placement cell or auto-detected
    is_startup_founder  = db.Column(db.Boolean, default=False)
    has_ml_internship   = db.Column(db.Boolean, default=False)
    has_open_source     = db.Column(db.Boolean, default=False)

    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    resume        = db.relationship("Resume",        back_populates="student", uselist=False)
    github_signal = db.relationship("GitHubSignal",  back_populates="student", uselist=False)
    cp_signal     = db.relationship("CPSignal",      back_populates="student", uselist=False)
    scores        = db.relationship("DriveScore",    back_populates="student")

    def __repr__(self):
        return f"<Student {self.erp_id} — {self.name}>"


# ─────────────────────────────────────────────
# RESUME  (parsed sections stored as JSON)
# ─────────────────────────────────────────────
class Resume(db.Model):
    __tablename__ = "resumes"

    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    file_path   = db.Column(db.String(300))          # stored PDF path

    # raw text per section — populated by the section-aware parser
    raw_skills          = db.Column(db.Text)
    raw_projects        = db.Column(db.Text)
    raw_internships     = db.Column(db.Text)
    raw_experience      = db.Column(db.Text)
    raw_certifications  = db.Column(db.Text)
    raw_achievements    = db.Column(db.Text)
    raw_education       = db.Column(db.Text)
    raw_full            = db.Column(db.Text)

    # SBERT embedding vectors stored as JSON arrays
    embedding_skills          = db.Column(db.Text)
    embedding_projects        = db.Column(db.Text)
    embedding_internships     = db.Column(db.Text)
    embedding_experience      = db.Column(db.Text)
    embedding_certifications  = db.Column(db.Text)
    embedding_full            = db.Column(db.Text)

    parsed_at   = db.Column(db.DateTime)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    student     = db.relationship("Student", back_populates="resume")

    def __repr__(self):
        return f"<Resume student_id={self.student_id}>"


# ─────────────────────────────────────────────
# GITHUB SIGNAL
# ─────────────────────────────────────────────
class GitHubSignal(db.Model):
    __tablename__ = "github_signals"

    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)

    total_repos         = db.Column(db.Integer, default=0)
    total_commits_90d   = db.Column(db.Integer, default=0)   # last 90 days
    unique_languages    = db.Column(db.Integer, default=0)   # language diversity
    has_readme_projects = db.Column(db.Boolean, default=False)
    longest_streak_days = db.Column(db.Integer, default=0)
    days_since_last_commit = db.Column(db.Integer)           # recency signal
    top_languages       = db.Column(db.Text)                 # JSON list e.g. ["Python","JS"]
    pinned_repo_desc    = db.Column(db.Text)                 # combined text for NLP

    # computed quality score 0–100
    github_score        = db.Column(db.Float, default=0.0)

    fetched_at  = db.Column(db.DateTime)
    student     = db.relationship("Student", back_populates="github_signal")


# ─────────────────────────────────────────────
# CP SIGNAL  (competitive programming authenticity)
# ─────────────────────────────────────────────
class CPSignal(db.Model):
    __tablename__ = "cp_signals"

    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)

    # LeetCode
    lc_solved_easy      = db.Column(db.Integer, default=0)
    lc_solved_medium    = db.Column(db.Integer, default=0)
    lc_solved_hard      = db.Column(db.Integer, default=0)
    lc_contest_rating   = db.Column(db.Float,   default=0.0)
    lc_contests_attended = db.Column(db.Integer, default=0)
    # authenticity: ratio of acceptance submissions to total submissions per problem
    # genuine solvers retry; spammers do 1-shot submissions
    lc_avg_attempts_per_problem = db.Column(db.Float, default=1.0)

    # Codeforces
    cf_rating           = db.Column(db.Integer, default=0)
    cf_max_rating       = db.Column(db.Integer, default=0)
    cf_contests_attended = db.Column(db.Integer, default=0)
    cf_problems_solved  = db.Column(db.Integer, default=0)

    # CodeChef
    cc_rating           = db.Column(db.Integer, default=0)
    cc_problems_solved  = db.Column(db.Integer, default=0)

    # authenticity flags (set by authenticity engine)
    authenticity_score  = db.Column(db.Float, default=1.0)   # 0–1 multiplier
    flag_suspicious     = db.Column(db.Boolean, default=False)
    flag_reason         = db.Column(db.String(200))           # human-readable explanation

    # aggregate CP score 0–100 (post authenticity weighting)
    cp_score            = db.Column(db.Float, default=0.0)

    fetched_at  = db.Column(db.DateTime)
    student     = db.relationship("Student", back_populates="cp_signal")


# ─────────────────────────────────────────────
# COMPANY DRIVE
# ─────────────────────────────────────────────
class Drive(db.Model):
    __tablename__ = "drives"

    id              = db.Column(db.Integer, primary_key=True)
    company_name    = db.Column(db.String(120), nullable=False)
    role_title      = db.Column(db.String(120))
    jd_text         = db.Column(db.Text)                     # raw JD
    jd_file_path    = db.Column(db.String(300))
    shortlist_count = db.Column(db.Integer, default=50)      # how many to shortlist

    # JD embedding (full, for fallback scoring)
    jd_embedding    = db.Column(db.Text)                     # JSON float list

    # weight configuration — placement cell can override
    # all weights sum to 1.0
    weight_skills       = db.Column(db.Float, default=0.30)
    weight_projects     = db.Column(db.Float, default=0.25)
    weight_experience   = db.Column(db.Float, default=0.15)
    weight_github       = db.Column(db.Float, default=0.15)
    weight_cp           = db.Column(db.Float, default=0.10)
    weight_cgpa         = db.Column(db.Float, default=0.05)

    # special signal boost multipliers (0 = disabled, 1 = no boost, >1 = boosted)
    boost_startup_founder = db.Column(db.Float, default=1.0)
    boost_ml_internship   = db.Column(db.Float, default=1.0)
    boost_open_source     = db.Column(db.Float, default=1.0)

    # eligibility filters (hard cutoffs applied before scoring)
    min_cgpa        = db.Column(db.Float, default=0.0)
    max_backlogs    = db.Column(db.Integer, default=99)
    allowed_branches = db.Column(db.Text)                    # JSON list e.g. ["CSE","IT"]

    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    drive_date      = db.Column(db.DateTime)

    scores          = db.relationship("DriveScore", back_populates="drive")

    def __repr__(self):
        return f"<Drive {self.company_name} — {self.role_title}>"


# ─────────────────────────────────────────────
# DRIVE SCORE  (one row per student per drive)
# ─────────────────────────────────────────────
class DriveScore(db.Model):
    __tablename__ = "drive_scores"

    id          = db.Column(db.Integer, primary_key=True)
    drive_id    = db.Column(db.Integer, db.ForeignKey("drives.id"),    nullable=False)
    student_id  = db.Column(db.Integer, db.ForeignKey("students.id"),  nullable=False)

    # component scores (0–100 each)
    score_skills          = db.Column(db.Float, default=0.0)
    score_projects        = db.Column(db.Float, default=0.0)
    score_internships     = db.Column(db.Float, default=0.0)
    score_experience      = db.Column(db.Float, default=0.0)
    score_certifications  = db.Column(db.Float, default=0.0)
    score_github          = db.Column(db.Float, default=0.0)
    score_cp              = db.Column(db.Float, default=0.0)
    score_cgpa            = db.Column(db.Float, default=0.0)

    # final weighted score (0–100) after boosts
    final_score       = db.Column(db.Float, default=0.0)

    # explainability — stored as JSON for the dashboard
    matched_skills    = db.Column(db.Text)    # JSON list of matched keywords
    missing_skills    = db.Column(db.Text)    # JSON list of JD keywords not found
    boost_applied     = db.Column(db.Text)    # JSON dict of boosts that fired
    flags             = db.Column(db.Text)    # JSON list of warning flags

    is_shortlisted    = db.Column(db.Boolean, default=False)
    rank              = db.Column(db.Integer)

    scored_at         = db.Column(db.DateTime, default=datetime.utcnow)

    student   = db.relationship("Student", back_populates="scores")
    drive     = db.relationship("Drive",   back_populates="scores")

    __table_args__ = (
        db.UniqueConstraint("drive_id", "student_id", name="uq_drive_student"),
    )

    def __repr__(self):
        return f"<DriveScore drive={self.drive_id} student={self.student_id} score={self.final_score:.1f}>"
