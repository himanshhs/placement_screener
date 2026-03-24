"""
resume_parser.py
────────────────
Extracts and sections a resume PDF into:
    skills | projects | experience | internships |
    certifications | achievements | education | full_text

Stage 1 — raw text via PyMuPDF
Stage 2 — section detection via keyword heading map
Stage 3 — clean + store into resumes table
"""

import re
from datetime import datetime


SECTION_PATTERNS = {
    "skills": [
        r"technical\s*skills", r"core\s*skills",
        r"skills\s*&?\s*technologies", r"skills\s*and\s*technologies",
        r"technologies", r"tools\s*&?\s*technologies",
        r"programming\s*languages", r"competencies", r"^skills$",
    ],
    "projects": [
        r"projects?", r"personal\s*projects?", r"academic\s*projects?",
        r"key\s*projects?", r"notable\s*projects?", r"major\s*projects?",
    ],
    "internships": [
        r"internships?",
        r"internship\s*experience",
        r"industry\s*internships?",
        r"summer\s*internships?",
        r"industrial\s*training",
        r"in[- ]?plant\s*training",
    ],
    "experience": [
        r"work\s*experience",
        r"professional\s*experience",
        r"employment(\s*history)?",
        r"^experience$",
    ],
    "certifications": [
        r"certifications?",
        r"certificates?",
        r"licen[sc]es?\s*&?\s*certifications?",
        r"professional\s*certifications?",
        r"online\s*courses?\s*&?\s*certifications?",
        r"courses?\s*&?\s*certifications?",
        r"moocs?",
    ],
    "achievements": [
        r"achievements?",
        r"awards?\s*&?\s*achievements?",
        r"honors?\s*&?\s*awards?",
        r"accomplishments?",
        r"extra[- ]?curricular",
        r"positions?\s*of\s*responsibility",
        r"leadership",
        r"activities",
    ],
    "education": [
        r"education",
        r"educational\s*background",
        r"academic\s*background",
        r"qualifications?",
        r"academics?",
    ],
}

_COMPILED = {
    section: [re.compile(p, re.IGNORECASE) for p in patterns]
    for section, patterns in SECTION_PATTERNS.items()
}

ABBREVIATIONS = {
    r"\bml\b":  "machine learning",
    r"\bai\b":  "artificial intelligence",
    r"\bnlp\b": "natural language processing",
    r"\bcv\b":  "computer vision",
    r"\bds\b":  "data science",
    r"\bapi\b": "application programming interface",
    r"\boop\b": "object oriented programming",
    r"\baws\b": "amazon web services",
    r"\bgcp\b": "google cloud platform",
    r"\bci\b":  "continuous integration",
    r"\bcd\b":  "continuous deployment",
}


def _expand_abbreviations(text: str) -> str:
    for pattern, expansion in ABBREVIATIONS.items():
        text = re.sub(pattern, expansion, text, flags=re.IGNORECASE)
    return text


def _clean_text(text: str) -> str:
    text = re.sub(r"[•●◆▪▸►✓✔➢]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[^\x20-\x7E\n]", " ", text)
    return text.strip()


def _detect_section(line: str):
    stripped = line.strip()
    if not stripped or len(stripped) > 60 or stripped.endswith("."):
        return None
    for section, patterns in _COMPILED.items():
        for pattern in patterns:
            if pattern.search(stripped):
                return section
    return None


def extract_text_from_pdf(file_path: str) -> str:
    try:
        import fitz
        doc = fitz.open(file_path)
        pages = [page.get_text("text") for page in doc]
        doc.close()
        return "\n".join(pages)
    except ImportError:
        raise RuntimeError("PyMuPDF not installed. Run: pip install pymupdf")
    except Exception as e:
        raise RuntimeError(f"Failed to read PDF '{file_path}': {e}")


def split_into_sections(raw_text: str) -> dict:
    sections = {k: [] for k in [
        "skills", "projects", "internships", "experience",
        "certifications", "achievements", "education", "unclassified"
    ]}
    current_section = "unclassified"
    for line in raw_text.split("\n"):
        detected = _detect_section(line)
        if detected:
            current_section = detected
            continue
        sections[current_section].append(line)
    return {s: "\n".join(lines).strip() for s, lines in sections.items()}


def parse_resume(file_path: str) -> dict:
    raw_text = extract_text_from_pdf(file_path)
    if not raw_text.strip():
        raise ValueError("No text extracted. PDF may be a scanned image.")

    sections = split_into_sections(raw_text)
    result = {}
    for name, text in sections.items():
        if name == "unclassified":
            continue
        result[f"raw_{name}"] = _expand_abbreviations(_clean_text(text))

    result["raw_full"]  = _expand_abbreviations(_clean_text(raw_text))
    result["parsed_at"] = datetime.utcnow()
    return result


def save_parsed_resume(student_id: int, file_path: str, parsed: dict, db_session):
    from app.models.models import Resume
    resume = db_session.query(Resume).filter_by(student_id=student_id).first()
    if not resume:
        resume = Resume(student_id=student_id)
        db_session.add(resume)

    resume.file_path           = str(file_path)
    resume.raw_skills          = parsed.get("raw_skills", "")
    resume.raw_projects        = parsed.get("raw_projects", "")
    resume.raw_internships     = parsed.get("raw_internships", "")
    resume.raw_experience      = parsed.get("raw_experience", "")
    resume.raw_certifications  = parsed.get("raw_certifications", "")
    resume.raw_education       = parsed.get("raw_education", "")
    resume.raw_full            = parsed.get("raw_full", "")
    resume.parsed_at           = parsed.get("parsed_at", datetime.utcnow())

    # clear cached embeddings on every new parse
    for col in ["embedding_skills", "embedding_projects", "embedding_internships",
                "embedding_experience", "embedding_certifications", "embedding_full"]:
        setattr(resume, col, None)

    db_session.commit()
    return resume


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python resume_parser.py path/to/resume.pdf")
        sys.exit(1)
    result = parse_resume(sys.argv[1])
    for key, value in result.items():
        if key == "parsed_at":
            continue
        preview = value[:200].replace("\n", " ") if value else "(empty)"
        print(f"\n[{key.upper()}]\n{preview}...")
