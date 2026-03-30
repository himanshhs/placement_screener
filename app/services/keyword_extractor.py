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
    For projects section: extract 2-3 gram noun phrases.
    These capture what was built, not just what tech was used.
    """
    if not text: return []
    tokens = _tokens(text)

    bigrams  = _ngrams(tokens, 2)
    trigrams = _ngrams(tokens, 3)

    # prefer trigrams that contain a meaningful action or domain noun
    action_words = {
        "analysis","detection","classification","prediction","generation",
        "recognition","recommendation","tracking","monitoring","automation",
        "processing","extraction","summarization","translation","optimization",
        "visualisation","visualization","dashboard","pipeline","system","tool",
        "platform","application","engine","framework","service","api","model",
        "bot","scraper","tracker","manager","scheduler","simulator","calculator",
    }

    scored = []
    for gram in trigrams + bigrams:
        words = gram.split()
        if any(w in action_words for w in words):
            scored.append((2, gram))
        else:
            scored.append((1, gram))

    # deduplicate — remove bigrams fully contained in a trigram
    seen = set()
    result = []
    for _, gram in sorted(scored, key=lambda x: -x[0]):
        words = gram.split()
        if not any(w in seen for w in words):
            result.append(gram)
            seen.update(words)
        if len(result) >= n:
            break

    return [_title(k) for k in result[:n]]


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
    For experience: action + domain bigrams and trigrams.
    """
    if not text: return []
    tokens = _tokens(text)
    bigrams = _ngrams(tokens, 2)
    trigrams = _ngrams(tokens, 3)
    combined = trigrams[:3] + bigrams
    seen = set()
    result = []
    for gram in combined:
        key = tuple(gram.split())
        if key not in seen:
            seen.add(key)
            result.append(gram)
        if len(result) >= n:
            break
    return [_title(g) for g in result[:n]]


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
    if degrees:   result.append(degrees[0].upper())
    if branches:  result.append(branches[0].upper())
    raw_cgpa = cgpa_match.group(1).rstrip('.')
    if cgpa_match:result.append(f"CGPA {raw_cgpa}")

    # institution names — capitalised proper nouns
    institutions = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', text)
    noise = {"June","July","August","May","The"}
    for inst in institutions:
        if inst not in noise and inst not in result:
            result.append(inst)
        if len(result) >= n:
            break

    return result[:n]


def _title(s: str) -> str:
    """Smart title case — preserve known acronyms."""
    acronyms = {"aws","gcp","nlp","sql","api","css","php","npm","iot",
                "html","rest","git","ide","sdk","orm","cdn","dns","tcp",
                "cse","it","ece","ee","me","ce"}
    words = s.split()
    result = []
    for w in words:
        if w.lower() in acronyms:
            result.append(w.upper())
        elif "." in w or w in {"next.js","node.js","scikit-learn"}:
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
