"""
keyword_extractor.py
─────────────────────
Section-aware keyword and n-gram extraction for resume display.

Each section has a different extraction strategy:
    Skills        — 1-gram tech signals (what they know)
    Projects      — 2-3 gram noun phrases (what they built)
    Internships   — company + role + domain phrases (where they worked)
    Experience    — action + domain phrases (what they did)
    Certifications— credential names (what they earned)
    Education     — degree + institution (where they studied)
"""

import re
from collections import Counter

# ── Known tech signals for skills section ─────────────────────────────────
TECH_SIGNALS = {
    "python","java","javascript","typescript","c++","c#","golang","rust",
    "kotlin","swift","ruby","php","scala","r","matlab","bash","sql","html","css",
    "react","angular","vue","next.js","node.js","flask","django","spring",
    "fastapi","express","laravel","tensorflow","pytorch","keras","scikit-learn",
    "pandas","numpy","opencv","langchain","hugging face",
    "aws","gcp","azure","docker","kubernetes","terraform","jenkins","git","linux",
    "nginx","redis","kafka","rabbitmq","elasticsearch","graphql","rest","api",
    "postgresql","mysql","mongodb","sqlite","firebase","dynamodb","cassandra",
    "machine learning","deep learning","nlp","computer vision","data science",
    "system design","microservices","websockets","competitive programming",
    "data structures","algorithms","open source","reinforcement learning",
}

# ── Words to strip from n-gram extraction ─────────────────────────────────
STOPWORDS = {
    "a","an","the","and","or","but","in","on","at","to","for","of","with",
    "by","from","as","is","was","are","were","be","been","being","have",
    "has","had","do","does","did","will","would","could","should","may",
    "might","shall","can","need","used","using","built","created","developed",
    "implemented","worked","made","designed","during","this","that","these",
    "those","which","who","whom","their","our","your","its","we","i","my",
    "also","more","over","both","each","all","any","such","into","through",
    "between","own","same","other","than","then","when","where","how","what",
    "while","after","before","about","than","very","just","up","out","one",
    "per","including","multiple","various","different","new","across","within",
    "under","team","company","college","university","year","month","months",
}


def _clean(text: str) -> str:
    # preserve hyphens between words (e.g. real-time -> real time)
    text = re.sub(r'(\w)-(\w)', r'\1 \2', text)
    text = re.sub(r"[•●◆▪▸►✓✔➢–—]+", " ", text)
    # remove punctuation that bleeds into tokens
    text = re.sub(r"[^\w\s#+]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def _tokens(text: str) -> list:
    """Tokenise — strip trailing digits/noise, skip stopwords."""
    preserve = {"ai","ml","ui","ux","os","db","vm","qa"}
    raw = _clean(text).split()
    clean = []
    for t in raw:
        t = t.strip("0123456789.")
        if t in preserve:
            clean.append(t)
        elif len(t) > 2 and t not in STOPWORDS and not t.isdigit():
            clean.append(t)
    return clean


def _ngrams(tokens: list, n: int) -> list:
    return [" ".join(tokens[i:i+n]) for i in range(len(tokens)-n+1)]


# ── Section-specific extractors ────────────────────────────────────────────

def _extract_skills(text: str, n: int = 10) -> list:
    """
    For skills section: match known tech signals.
    Returns clean title-cased tech keywords.
    """
    if not text: return []
    lower = text.lower()
    found = []

    # multi-word signals first
    for sig in sorted(TECH_SIGNALS, key=len, reverse=True):
        if sig in lower and sig not in found:
            found.append(sig)
        if len(found) >= n:
            break

    # fill remaining with meaningful single tokens
    if len(found) < n:
        for tok in _tokens(text):
            if tok not in found and tok not in STOPWORDS and len(tok) > 3:
                found.append(tok)
            if len(found) >= n:
                break

    return [_title(k) for k in found[:n]]


def _extract_projects(text: str, n: int = 8) -> list:
    """
    For projects section: extract project titles and tech stack terms.

    Project titles are short lines that appear BEFORE the tech stack line
    (which is a comma-separated list of tools on the next line).
    We detect them as short lines with mixed/title case that are not
    pure tech-stack lists and not long descriptive sentences.
    """
    if not text: return []
    lines = text.split("\n")
    result = []
    seen_lower: set = set()

    for i, line in enumerate(lines):
        line = line.strip()
        if not line or line[0] in "•-–":
            continue
        if re.match(r'^\d', line):
            continue
        # Tech stack lines: comma-separated short tokens (e.g. "Python, Flask, NLP")
        # Detect: most tokens are short and separated by commas
        comma_parts = [p.strip() for p in line.split(",")]
        if len(comma_parts) >= 3 and all(len(p) < 25 for p in comma_parts):
            # It's a tech stack line — extract individual tech tokens instead
            for part in comma_parts:
                part_clean = part.strip("() ")
                if part_clean and len(part_clean) > 1:
                    pl = part_clean.lower()
                    if pl not in seen_lower:
                        result.append(_title(part_clean))
                        seen_lower.add(pl)
            continue
        # Long descriptive sentences are bullet points, skip
        if len(line) > 60:
            continue
        # Project title: must have at least one capital, reasonable length
        if not re.search(r'[A-Z]', line):
            continue
        line_clean = re.sub(r'[&]', 'and', line).strip()
        # Remove tech suffixes in parens e.g. "System (Python, Flask)"
        line_clean = re.sub(r'\s*\(.*?\)', '', line_clean).strip()
        ll = line_clean.lower()
        if ll not in seen_lower and len(ll) > 3:
            result.append(line_clean)
            seen_lower.add(ll)

        if len(result) >= n:
            break

    return result[:n]


def _extract_internships(text: str, n: int = 8) -> list:
    """
    For internships: company names, role titles, domain phrases.
    """
    if not text: return []

    month_noise = {"June","July","August","May","Sep","Oct","Jan","Feb",
                   "Mar","Apr","November","December","January","February",
                   "March","April","September","October","Intern","Training",
                   "The","And","For","With","At","To","Of"}

    proper = re.findall(r'\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})+)\b', text)
    proper_clean = [p for p in proper
                    if not any(w in month_noise for w in p.split())
                    and len(p) > 5]

    tokens = _tokens(text)
    domain_bigrams = [_title(g) for g in _ngrams(tokens, 2)
                      if not any(w in STOPWORDS for w in g.split())]

    combined = list(dict.fromkeys(proper_clean[:4] + domain_bigrams))
    return combined[:n]


def _extract_experience(text: str, n: int = 8) -> list:
    """
    For experience: extract role titles and company names by reading
    short capitalised lines (which is how every resume formats them)
    rather than producing blind bigrams/trigrams from lowercased tokens.
    """
    if not text: return []
    result = []
    seen_lower: set = set()

    # Words that appear in date lines, location lines, or generic labels
    _noise = {
        "the","and","for","with","at","to","of","a","an","in","on","by",
        "built","led","applied","performed","developed","integrated",
        "implemented","remote","jan","feb","mar","apr","may","jun","jul",
        "aug","sep","oct","nov","dec","india","intern","training",
        # Indian cities commonly appearing in resume location lines
        "nagpur","mumbai","pune","delhi","bangalore","bengaluru","hyderabad",
        "chennai","kolkata","ahmedabad","jaipur","lucknow","bhopal","indore",
        "noida","gurugram","gurgaon","surat","vadodara","vizag","visakhapatnam",
    }

    for line in text.split("\n"):
        line = line.strip()
        # skip blank, bullet, or date lines
        if not line or line[0] in "•-–" or re.match(r'^\d', line):
            continue
        # skip long descriptive sentences
        if len(line) > 55:
            continue
        # must contain at least one capital letter (proper noun signal)
        if not re.search(r'[A-Z]', line):
            continue
        line_clean = re.sub(r'[,;:.]$', '', line).strip()
        words_lower = [w.lower().strip(".,;:") for w in line_clean.split()]
        # skip lines that are entirely noise/stopwords
        if all(w in _noise for w in words_lower):
            continue
        # Preserve genuine all-caps abbreviations (CEO, MVP, ML, AI …)
        display = " ".join(
            w if (w.isupper() and len(w) <= 4) else w.capitalize()
            for w in line_clean.split()
        )
        ll = display.lower()
        if ll not in seen_lower:
            result.append(display)
            seen_lower.add(ll)
        if len(result) >= n:
            break

    return result[:n]


def _extract_certifications(text: str, n: int = 6) -> list:
    """
    For certifications: extract credential names.
    Looks for known platforms and capitalised multi-word phrases.
    """
    if not text: return []

    platforms = ["aws","google","microsoft","ibm","coursera","nptel",
                 "udemy","hackerrank","meta","oracle","cisco","tensorflow",
                 "deeplearning.ai","mongodb","kubernetes"]

    lower = text.lower()
    found = []

    for p in platforms:
        if p in lower:
            found.append(p.title())

    # also grab capitalised credential phrases
    creds = re.findall(
        r'\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){1,4})\b', text
    )
    noise = {"June","July","August","May","The","And","For","With"}
    for c in creds:
        if c not in noise and c not in found and len(c) > 6:
            found.append(c)
        if len(found) >= n:
            break

    return found[:n]


def _extract_education(text: str, n: int = 5) -> list:
    """
    For education: degree, branch, institution name.
    No tech keywords — context is academic not technical.
    """
    if not text: return []

    degrees = re.findall(
        r'\b(B\.?Tech|M\.?Tech|B\.?E|M\.?E|BCA|MCA|B\.?Sc|M\.?Sc|Ph\.?D|MBA)\b',
        text, re.IGNORECASE
    )
    cgpa_match = re.search(r'cgpa\s*([\d.]+)', text, re.IGNORECASE)
    branches = re.findall(
        r'\b(CSE|IT|ECE|EE|ME|CE|AIDS|AIML|Data Science|Computer Science|'
        r'Information Technology|Electronics|Mechanical|Civil)\b',
        text, re.IGNORECASE
    )

    result = []
    seen_lower: set = set()

    def _add(item: str):
        ll = item.lower()
        if ll not in seen_lower:
            result.append(item)
            seen_lower.add(ll)

    if degrees:   _add(degrees[0].upper())
    if branches:  _add(branches[0].title())   # title-case, not ALL-CAPS
    raw_cgpa = cgpa_match.group(1).rstrip('.') if cgpa_match else None
    if cgpa_match: _add(f"CGPA {raw_cgpa}")

    # institution names — capitalised proper nouns, deduped case-insensitively
    institutions = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', text)
    noise = {"June","July","August","May","The","Data Science","Computer Science"}
    for inst in institutions:
        if inst not in noise:
            _add(inst)
        if len(result) >= n:
            break

    return result[:n]


def _title(s: str) -> str:
    """Smart title case — preserve known acronyms and non-standard casings."""
    acronyms = {"aws","gcp","nlp","sql","api","css","php","npm","iot",
                "html","rest","git","ide","sdk","orm","cdn","dns","tcp",
                "cse","it","ece","ee","me","ce"}
    # tokens whose display casing doesn't follow normal title-case rules
    overrides = {
        "scikit-learn": "Scikit-Learn",
        "numpy":        "NumPy",
        "opencv":       "OpenCV",
        "tensorflow":   "TensorFlow",
        "pytorch":      "PyTorch",
        "javascript":   "JavaScript",
        "typescript":   "TypeScript",
        "mongodb":      "MongoDB",
        "postgresql":   "PostgreSQL",
        "graphql":      "GraphQL",
        "github":       "GitHub",
        "gitlab":       "GitLab",
        "linkedin":     "LinkedIn",
        "langchain":    "LangChain",
        "fastapi":      "FastAPI",
        "nextjs":       "Next.js",
        "nodejs":       "Node.js",
        "next.js":      "Next.js",
        "node.js":      "Node.js",
        "hugging face": "Hugging Face",
        "vs code":      "VS Code",
        "deeplearning.ai": "DeepLearning.AI",
    }
    s_lower = s.lower()
    if s_lower in overrides:
        return overrides[s_lower]
    words = s.split()
    result = []
    for w in words:
        wl = w.lower()
        if wl in overrides:
            result.append(overrides[wl])
        elif wl in acronyms:
            result.append(w.upper())
        elif "." in w:
            result.append(w)
        else:
            result.append(w.capitalize())
    return " ".join(result)


# ── Main entry point ───────────────────────────────────────────────────────

SECTION_EXTRACTORS = {
    "Skills":         _extract_skills,
    "Projects":       _extract_projects,
    "Internships":    _extract_internships,
    "Experience":     _extract_experience,
    "Certifications": _extract_certifications,
    "Education":      _extract_education,
}


def extract_section_insights(resume) -> dict:
    """
    Returns {section_name: [keyword, ...]} for each non-empty section.
    Each section uses its own extraction strategy.
    """
    if not resume:
        return {}

    raw_map = {
        "Skills":         resume.raw_skills,
        "Projects":       resume.raw_projects,
        "Internships":    resume.raw_internships,
        "Experience":     resume.raw_experience,
        "Certifications": resume.raw_certifications,
        "Education":      resume.raw_education,
    }

    return {
        name: SECTION_EXTRACTORS[name](text or "")
        for name, text in raw_map.items()
        if text and text.strip()
    }
