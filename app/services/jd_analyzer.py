"""
jd_analyzer.py
──────────────
Reads a JD text and auto-suggests drive weight configuration.

Strategy:
    Scan JD for keyword signals that indicate what matters most
    to this company. Return suggested weights that sum to 1.0.

    e.g. a JD heavy on "machine learning, Python, model training"
         gets higher weight_skills and weight_projects.
         A JD mentioning "2+ years experience, led teams"
         gets higher weight_experience.
         A JD saying "competitive programming, DSA"
         gets higher weight_cp.
"""

import re


# Keyword groups — each maps to a scoring axis
SIGNAL_KEYWORDS = {
    "skills": [
        "python", "java", "javascript", "react", "node", "sql", "machine learning",
        "deep learning", "tensorflow", "pytorch", "docker", "kubernetes", "aws",
        "cloud", "backend", "frontend", "fullstack", "api", "rest", "microservices",
        "data structures", "algorithms", "system design", "linux", "git",
    ],
    "projects": [
        "projects", "built", "developed", "created", "portfolio", "github",
        "open source", "hackathon", "side project", "personal project",
        "product", "startup", "launched", "shipped",
    ],
    "internships": [
        "internship", "intern", "training", "industrial", "summer project",
        "apprentice", "placement", "on-the-job",
    ],
    "experience": [
        "years of experience", "work experience", "professional experience",
        "industry experience", "previous role", "employed", "employment",
        "full-time", "part-time", "led", "managed", "team lead",
    ],
    "certifications": [
        "certified", "certification", "aws certified", "google certified",
        "microsoft certified", "coursera", "udemy", "mooc", "credential",
        "license",
    ],
    "github": [
        "github", "contributions", "open source", "repositories", "commits",
        "active coder", "coding activity", "public repos",
    ],
    "cp": [
        "competitive programming", "leetcode", "codeforces", "codechef",
        "data structures", "algorithms", "dsa", "problem solving",
        "competitive coder", "acm", "icpc",
    ],
    "cgpa": [
        "cgpa", "gpa", "percentage", "academic", "first class", "distinction",
        "marks", "grades", "aggregate",
    ],
}

# Base weights — starting point before keyword adjustment
BASE_WEIGHTS = {
    "skills":         0.28,
    "projects":       0.22,
    "internships":    0.10,
    "experience":     0.10,
    "certifications": 0.05,
    "github":         0.13,
    "cp":             0.08,
    "cgpa":           0.04,
}


def _count_signals(jd_lower: str, keywords: list) -> int:
    return sum(1 for kw in keywords if kw in jd_lower)


def suggest_weights(jd_text: str) -> dict:
    """
    Analyse JD text and return suggested weight dict.
    All values sum to 1.0.
    """
    if not jd_text or not jd_text.strip():
        return BASE_WEIGHTS.copy()

    jd_lower = jd_text.lower()

    # count keyword hits per axis
    hits = {
        axis: _count_signals(jd_lower, keywords)
        for axis, keywords in SIGNAL_KEYWORDS.items()
    }

    total_hits = sum(hits.values()) or 1

    # blend: 60% base weight + 40% keyword signal
    blended = {}
    for axis in BASE_WEIGHTS:
        signal_weight = hits[axis] / total_hits
        blended[axis] = round(
            0.60 * BASE_WEIGHTS[axis] + 0.40 * signal_weight, 4
        )

    # normalise so weights sum exactly to 1.0
    total = sum(blended.values())
    normalised = {k: round(v / total, 4) for k, v in blended.items()}

    # fix floating point drift — add remainder to skills (highest weight)
    remainder = round(1.0 - sum(normalised.values()), 4)
    normalised["skills"] = round(normalised["skills"] + remainder, 4)

    return normalised


def extract_jd_from_pdf(file_path: str) -> str:
    """Extract raw text from a JD PDF using PyMuPDF."""
    try:
        import fitz
        doc = fitz.open(file_path)
        text = "\n".join(page.get_text("text") for page in doc)
        doc.close()
        return text.strip()
    except ImportError:
        raise RuntimeError("PyMuPDF not installed. Run: pip install pymupdf")
    except Exception as e:
        raise RuntimeError(f"Failed to read JD PDF: {e}")


def summarise_suggestions(weights: dict) -> list:
    """
    Return a human-readable list of suggestions for the placement cell.
    e.g. ["Skills weighted higher — JD emphasises technical stack",
          "CP weighted higher — JD mentions DSA/competitive programming"]
    """
    notes = []
    if weights.get("cp", 0) > 0.12:
        notes.append("CP weighted higher — JD emphasises DSA / problem solving")
    if weights.get("projects", 0) > 0.25:
        notes.append("Projects weighted higher — JD values shipped work")
    if weights.get("experience", 0) > 0.14:
        notes.append("Experience weighted higher — JD requires prior work history")
    if weights.get("internships", 0) > 0.13:
        notes.append("Internships weighted higher — JD values industry exposure")
    if weights.get("cgpa", 0) > 0.08:
        notes.append("CGPA weighted higher — JD mentions academic performance")
    if weights.get("certifications", 0) > 0.07:
        notes.append("Certifications weighted higher — JD values credentials")
    if not notes:
        notes.append("Balanced weights applied — no strong signal emphasis found")
    return notes
