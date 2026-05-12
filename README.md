# PlaceIQ — Placement Intelligence System

An AI-powered placement screening system built for college placement cells.
Replaces 10th/12th percentage filtering with multi-signal scoring using
resume NLP, GitHub activity, competitive programming authenticity, and
JD-based dynamic weight configuration.

---

## What it does

- **Imports students** from college ERP via CSV bulk upload
- **Parses resumes** section-by-section (Skills, Projects, Internships,
  Experience, Certifications, Education)
- **Fetches GitHub signals** — commits, streak, language diversity, recency
- **Fetches CP signals** — LeetCode/Codeforces via Codolio with an
  authenticity engine that detects fake submissions
- **Scores students per drive** using SBERT semantic similarity against
  the JD, weighted by configurable per-drive weights
- **Ranks and shortlists** with full explainability — matched keywords,
  missing skills, flags
- **Exports Excel** shortlist ready to send to the company

---

## Quick start (local)

```bash
git clone <your-repo-url>
cd placement_screener

python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt

python run.py
```

Open `http://localhost:5000`

Default login:
- Email: `admin@placement.com`
- Password: `admin123`

**Change the default password before real use.**

---

## Populate with sample data

```bash
python scripts/seed_sample_data.py
```

Creates 10 students with varied profiles + 2 drives (Google, TCS) with
scoring already run. Requires `sentence-transformers` and `pymupdf`
installed.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Database | SQLite (SQLAlchemy ORM) |
| NLP / Scoring | sentence-transformers (`all-MiniLM-L6-v2`), cosine similarity |
| PDF parsing | PyMuPDF (fitz) |
| Frontend | Jinja2 templates, vanilla CSS + JS |
| Auth | Session-based, bcrypt-style SHA-256 + salt |
| Export | openpyxl |

---

## Project structure

```
placement_screener/
├── run.py                    # entry point
├── requirements.txt
├── Procfile                  # for Render/Heroku deployment
├── render.yaml               # Render config
├── scripts/
│   └── seed_sample_data.py
└── app/
    ├── __init__.py           # app factory
    ├── models/models.py      # all DB tables
    ├── routes/               # auth, dashboard, drive, student
    └── services/             # resume_parser, scoring_engine,
                              # github_fetcher, cp_fetcher,
                              # jd_analyzer, keyword_extractor,
                              # erp_importer, auth_service
```

---

## Deployment on Render (free tier)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` — just set these env vars:
   - `SECRET_KEY` — any long random string
   - `GITHUB_TOKEN` — optional, for higher GitHub API rate limits
5. Deploy

---

## Key design decisions

**Why not use 10th/12th percentage?**
Placement cells were forced to use it because no better tool existed.
PlaceIQ replaces it with signals that actually predict performance —
technical skills, real project work, genuine coding activity.

**CP authenticity engine**
Genuine competitive programmers retry problems multiple times (avg
attempts/problem > 1.3). Fake submission farms submit once per problem
and move on. This ratio, combined with contest participation and rating
trajectory, produces an authenticity score (0–1) that multiplies the
raw CP score.

**Section-aware SBERT scoring**
Instead of treating the entire resume as one text blob, each section
is embedded separately and matched against the JD independently.
Skills, Projects, and Internships each contribute with their own weight.

**Configurable weights per drive**
A product company JD heavy on "system design, Python, distributed
systems" gets different suggested weights than a service company JD
mentioning "communication, SQL, certifications". The JD analyzer
reads keyword signals and suggests weights automatically, with the
placement cell able to override via sliders before confirming.
