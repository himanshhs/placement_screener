"""
scoring_engine.py
─────────────────
The brain of the system. Runs the full scoring pipeline for every
eligible student in a drive and saves results to drive_scores.

Pipeline per student:
    1. Eligibility filter     — hard cutoffs (CGPA, backlogs, branch)
    2. SBERT section scoring  — cosine similarity per resume section vs JD
    3. Signal score injection — GitHub score, CP score, CGPA normalised
    4. Weighted combination   — drive weights × component scores
    5. Special signal boosts  — configured tag multipliers
    6. Explainability build   — matched/missing skills, flags
    7. Save to DriveScore     — upsert + rank
"""

import json
import numpy as np
from datetime import datetime
from typing import Optional


# ── Embedding helpers ──────────────────────────────────────────────────────

_model = None  # lazy-loaded — only imported when scoring actually runs


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _embed(text: str) -> list[float]:
    """Return SBERT embedding as a plain Python list."""
    if not text or not text.strip():
        return []
    model = _get_model()
    vec = model.encode(text, convert_to_numpy=True)
    return vec.tolist()


def _cosine(a: list, b: list) -> float:
    """Cosine similarity between two vectors. Returns 0.0 on empty input."""
    if not a or not b:
        return 0.0
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def _load_embedding(json_str: Optional[str]) -> list:
    """Deserialise a cached embedding from the DB, or return []."""
    if not json_str:
        return []
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return []


def _ensure_resume_embeddings(resume, db_session) -> dict:
    """
    Compute and cache SBERT embeddings for each resume section.
    Only recomputes sections whose embedding is missing (None).
    Returns {section: embedding_list}.
    """
    sections = {
        "skills":     (resume.raw_skills,     "embedding_skills"),
        "projects":   (resume.raw_projects,   "embedding_projects"),
        "experience": (resume.raw_experience, "embedding_experience"),
        "full":       (resume.raw_full,       "embedding_full"),
    }
    embeddings = {}
    changed = False

    for name, (raw_text, col) in sections.items():
        cached = _load_embedding(getattr(resume, col))
        if cached:
            embeddings[name] = cached
        else:
            vec = _embed(raw_text or "")
            embeddings[name] = vec
            setattr(resume, col, json.dumps(vec))
            changed = True

    if changed:
        db_session.commit()

    return embeddings


def _ensure_jd_embedding(drive, db_session) -> list:
    """Compute and cache JD embedding on the Drive row."""
    cached = _load_embedding(drive.jd_embedding)
    if cached:
        return cached
    vec = _embed(drive.jd_text or "")
    drive.jd_embedding = json.dumps(vec)
    db_session.commit()
    return vec


# ── Stage 1: Eligibility filter ───────────────────────────────────────────

def _passes_eligibility(student, drive) -> tuple[bool, str]:
    """
    Returns (passes: bool, reason: str).
    Hard filters — student is excluded entirely if any fail.
    """
    if drive.min_cgpa and (student.cgpa or 0) < drive.min_cgpa:
        return False, f"CGPA {student.cgpa} below minimum {drive.min_cgpa}"

    if drive.max_backlogs is not None and (student.backlogs or 0) > drive.max_backlogs:
        return False, f"Backlogs {student.backlogs} exceeds maximum {drive.max_backlogs}"

    if drive.allowed_branches:
        try:
            allowed = json.loads(drive.allowed_branches)
            if allowed and student.branch not in allowed:
                return False, f"Branch {student.branch} not in {allowed}"
        except (json.JSONDecodeError, TypeError):
            pass

    return True, "eligible"


# ── Stage 2: SBERT section scoring ────────────────────────────────────────

def _score_resume_sections(resume_embeddings: dict, jd_vec: list) -> dict:
    """
    Compute cosine similarity between each resume section and the JD.
    Returns {section: score_0_to_100}.
    """
    return {
        "skills":     round(_cosine(resume_embeddings.get("skills",     []), jd_vec) * 100, 2),
        "projects":   round(_cosine(resume_embeddings.get("projects",   []), jd_vec) * 100, 2),
        "experience": round(_cosine(resume_embeddings.get("experience", []), jd_vec) * 100, 2),
    }


# ── Stage 3: Signal score injection ───────────────────────────────────────

def _get_signal_scores(student) -> dict:
    """Pull pre-computed sub-scores from GitHub and CP signal rows."""
    github_score = 0.0
    if student.github_signal:
        github_score = student.github_signal.github_score or 0.0

    cp_score = 0.0
    cp_flagged = False
    if student.cp_signal:
        cp_score   = student.cp_signal.cp_score or 0.0
        cp_flagged = student.cp_signal.flag_suspicious or False

    # normalise CGPA to 0–100
    # assuming 10-point scale; adjust here if your college uses percentage
    cgpa_score = round(((student.cgpa or 0) / 10.0) * 100, 2)
    cgpa_score = min(cgpa_score, 100.0)

    return {
        "github": github_score,
        "cp":     cp_score,
        "cgpa":   cgpa_score,
        "cp_flagged": cp_flagged,
    }


# ── Stage 4: Weighted combination ─────────────────────────────────────────

def _weighted_score(section_scores: dict, signal_scores: dict, drive) -> float:
    """
    Combine all component scores using drive's weight configuration.
    All weights should sum to 1.0.
    """
    score = (
        section_scores["skills"]     * (drive.weight_skills     or 0.30) +
        section_scores["projects"]   * (drive.weight_projects   or 0.25) +
        section_scores["experience"] * (drive.weight_experience or 0.15) +
        signal_scores["github"]      * (drive.weight_github     or 0.15) +
        signal_scores["cp"]          * (drive.weight_cp         or 0.10) +
        signal_scores["cgpa"]        * (drive.weight_cgpa       or 0.05)
    )
    return round(score, 2)


# ── Stage 5: Special signal boosts ────────────────────────────────────────

def _apply_boosts(base_score: float, student, drive) -> tuple[float, dict]:
    """
    Apply configured tag multipliers.
    Multipliers stack multiplicatively, capped at 1.25x total boost.
    Returns (boosted_score, boosts_applied_dict).
    """
    multiplier = 1.0
    boosts_applied = {}

    tag_config = [
        ("is_startup_founder", drive.boost_startup_founder, "startup founder"),
        ("has_ml_internship",  drive.boost_ml_internship,  "ML internship"),
        ("has_open_source",    drive.boost_open_source,    "open source contributor"),
    ]

    for attr, boost_value, label in tag_config:
        if getattr(student, attr, False) and boost_value and boost_value > 1.0:
            multiplier *= boost_value
            boosts_applied[label] = boost_value

    # cap total boost at 25% above base
    multiplier = min(multiplier, 1.25)
    boosted = round(min(base_score * multiplier, 100.0), 2)
    return boosted, boosts_applied


# ── Stage 6: Explainability ────────────────────────────────────────────────

def _build_explainability(resume, drive, signal_scores: dict) -> tuple[list, list, list]:
    """
    Extract matched and missing keywords between resume and JD.
    Returns (matched_skills, missing_skills, flags).

    Simple keyword overlap approach — fast and transparent.
    Can be upgraded to NLP extraction later.
    """
    jd_text   = (drive.jd_text or "").lower()
    full_text = (resume.raw_full if resume else "") or ""
    full_lower = full_text.lower()

    # extract meaningful words from JD (length > 3, skip stopwords)
    stopwords = {
        "with", "and", "the", "for", "that", "have", "will", "this",
        "from", "they", "been", "your", "work", "must", "should", "able",
        "good", "strong", "experience", "knowledge", "understanding",
    }
    jd_words = set(
        w.strip(".,;:()[]") for w in jd_text.split()
        if len(w) > 3 and w not in stopwords
    )

    matched  = sorted([w for w in jd_words if w in full_lower])[:15]
    missing  = sorted([w for w in jd_words if w not in full_lower])[:15]

    flags = []
    if signal_scores.get("cp_flagged"):
        flags.append("CP authenticity concern — verify manually")
    if signal_scores.get("github", 0) == 0:
        flags.append("No GitHub activity found")
    if signal_scores.get("cp", 0) == 0:
        flags.append("No CP platform activity found")

    return matched, missing, flags


# ── Main: score one student for one drive ─────────────────────────────────

def score_student_for_drive(student, drive, jd_vec: list, db_session) -> Optional[dict]:
    """
    Full pipeline for one student × one drive.
    Returns the result dict, or None if student is ineligible.
    Saves/updates DriveScore row.
    """
    from app.models.models import DriveScore

    # Stage 1 — eligibility
    passes, reason = _passes_eligibility(student, drive)
    if not passes:
        return None

    # Stage 2 — SBERT section scoring
    resume = student.resume
    if resume:
        resume_embeddings = _ensure_resume_embeddings(resume, db_session)
    else:
        resume_embeddings = {}

    section_scores = _score_resume_sections(resume_embeddings, jd_vec)

    # Stage 3 — signal scores
    signal_scores = _get_signal_scores(student)

    # Stage 4 — weighted combination
    base_score = _weighted_score(section_scores, signal_scores, drive)

    # Stage 5 — boosts
    final_score, boosts_applied = _apply_boosts(base_score, student, drive)

    # Stage 6 — explainability
    matched, missing, flags = _build_explainability(resume, drive, signal_scores)

    # Save to DB
    ds = db_session.query(DriveScore).filter_by(
        drive_id=drive.id, student_id=student.id
    ).first()
    if not ds:
        ds = DriveScore(drive_id=drive.id, student_id=student.id)
        db_session.add(ds)

    ds.score_skills     = section_scores["skills"]
    ds.score_projects   = section_scores["projects"]
    ds.score_experience = section_scores["experience"]
    ds.score_github     = signal_scores["github"]
    ds.score_cp         = signal_scores["cp"]
    ds.score_cgpa       = signal_scores["cgpa"]
    ds.final_score      = final_score
    ds.matched_skills   = json.dumps(matched)
    ds.missing_skills   = json.dumps(missing)
    ds.boost_applied    = json.dumps(boosts_applied)
    ds.flags            = json.dumps(flags)
    ds.scored_at        = datetime.utcnow()

    db_session.commit()
    return {"student_id": student.id, "final_score": final_score}


# ── Main: score ALL students for a drive ──────────────────────────────────

def run_drive_scoring(drive_id: int, db_session) -> dict:
    """
    Score every student for the given drive.
    After scoring, assigns ranks and marks top-N as shortlisted.

    Returns summary: {total, scored, excluded, errors}
    """
    from app.models.models import Drive, Student, DriveScore

    drive = db_session.query(Drive).get(drive_id)
    if not drive:
        return {"error": f"Drive {drive_id} not found"}

    # ensure JD embedding is ready before looping
    jd_vec = _ensure_jd_embedding(drive, db_session)

    students = db_session.query(Student).all()

    total = len(students)
    scored = excluded = errors = 0

    for student in students:
        try:
            result = score_student_for_drive(student, drive, jd_vec, db_session)
            if result is None:
                excluded += 1
            else:
                scored += 1
        except Exception as e:
            errors += 1
            print(f"  Error scoring student {student.id}: {e}")

    # assign ranks among scored students
    _assign_ranks(drive_id, drive.shortlist_count, db_session)

    return {
        "drive_id": drive_id,
        "total":    total,
        "scored":   scored,
        "excluded": excluded,
        "errors":   errors,
    }


def _assign_ranks(drive_id: int, shortlist_count: int, db_session):
    """
    Sort DriveScore rows by final_score descending,
    assign rank numbers, mark top-N as shortlisted.
    """
    from app.models.models import DriveScore

    scores = (
        db_session.query(DriveScore)
        .filter_by(drive_id=drive_id)
        .order_by(DriveScore.final_score.desc())
        .all()
    )

    for rank, ds in enumerate(scores, start=1):
        ds.rank           = rank
        ds.is_shortlisted = rank <= (shortlist_count or 50)

    db_session.commit()
