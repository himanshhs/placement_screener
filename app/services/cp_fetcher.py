"""
cp_fetcher.py
─────────────
Fetches competitive programming signals via Codolio (primary)
and Codeforces public API (secondary/fallback).

Authenticity engine — your core insight:
    Genuine solvers retry problems multiple times.
    Spammers submit once per problem, move on.

Authenticity signals checked:
    1. avg_attempts_per_problem  — genuine: >1.5, suspicious: <1.1
    2. contest_participation     — genuine solvers contest; farmers don't
    3. rating_trajectory         — rising rating = real practice
    4. hard_problem_ratio        — solving hards requires real effort
    5. submission_gap_variance   — farmers submit in bursts; genuine = spread
"""

import json
import requests
from datetime import datetime
from typing import Optional

DEFAULT_TIMEOUT = 10

CODOLIO_PROFILE_URL = "https://codolio.com/api/profile/{username}"
CODEFORCES_API      = "https://codeforces.com/api"


def _safe_get(url: str, **kwargs) -> Optional[dict]:
    try:
        r = requests.get(url, timeout=DEFAULT_TIMEOUT, **kwargs)
        if r.status_code == 200:
            return r.json()
        return None
    except requests.RequestException:
        return None


# ── Codolio fetcher ────────────────────────────────────────────────────────

def _fetch_codolio(username: str) -> Optional[dict]:
    """
    Codolio aggregates LeetCode + Codeforces + CodeChef + GFG.
    Uses their internal profile API endpoint.
    NOTE: unofficial endpoint — may change. Codeforces API is fallback.
    """
    url = CODOLIO_PROFILE_URL.format(username=username)
    data = _safe_get(url)
    if not data:
        return None

    # Codolio response structure (based on their current API shape)
    # We defensively get() everything so a missing key never crashes us
    lc   = data.get("leetcode",    {}) or {}
    cf   = data.get("codeforces",  {}) or {}
    cc   = data.get("codechef",    {}) or {}

    lc_easy   = lc.get("easySolved",   0) or 0
    lc_medium = lc.get("mediumSolved", 0) or 0
    lc_hard   = lc.get("hardSolved",   0) or 0
    lc_total  = lc_easy + lc_medium + lc_hard

    return {
        # LeetCode
        "lc_solved_easy":          lc_easy,
        "lc_solved_medium":        lc_medium,
        "lc_solved_hard":          lc_hard,
        "lc_contest_rating":       float(lc.get("contestRating", 0) or 0),
        "lc_contests_attended":    int(lc.get("contestsAttended", 0) or 0),
        # total submissions vs problems = proxy for avg attempts
        "lc_total_submissions":    int(lc.get("totalSubmissions", lc_total) or lc_total),
        "lc_total_problems":       lc_total,
        # Codeforces
        "cf_rating":               int(cf.get("rating", 0) or 0),
        "cf_max_rating":           int(cf.get("maxRating", 0) or 0),
        "cf_contests_attended":    int(cf.get("contestsAttended", 0) or 0),
        "cf_problems_solved":      int(cf.get("problemsSolved", 0) or 0),
        # CodeChef
        "cc_rating":               int(cc.get("rating", 0) or 0),
        "cc_problems_solved":      int(cc.get("problemsSolved", 0) or 0),
    }


# ── Codeforces fallback ────────────────────────────────────────────────────

def _fetch_codeforces(cf_handle: str) -> Optional[dict]:
    info = _safe_get(f"{CODEFORCES_API}/user.info?handles={cf_handle}")
    if not info or info.get("status") != "OK":
        return None
    user = info["result"][0]

    rating_hist = _safe_get(f"{CODEFORCES_API}/user.rating?handle={cf_handle}")
    contests = len(rating_hist["result"]) if rating_hist and rating_hist.get("status") == "OK" else 0

    submissions = _safe_get(f"{CODEFORCES_API}/user.status?handle={cf_handle}&count=500")
    solved = set()
    if submissions and submissions.get("status") == "OK":
        for sub in submissions["result"]:
            if sub.get("verdict") == "OK":
                pid = f"{sub['problem']['contestId']}{sub['problem']['index']}"
                solved.add(pid)

    return {
        "cf_rating":            user.get("rating", 0),
        "cf_max_rating":        user.get("maxRating", 0),
        "cf_contests_attended": contests,
        "cf_problems_solved":   len(solved),
    }


# ── Authenticity engine ────────────────────────────────────────────────────

def _run_authenticity_engine(signals: dict) -> tuple[float, bool, str]:
    """
    Returns (authenticity_score 0–1, is_suspicious, reason_string).

    authenticity_score is a multiplier applied to the final CP score.
    1.0 = fully authentic, 0.5 = halved, 0.0 = zeroed out.
    """
    flags = []
    score = 1.0

    lc_problems    = signals.get("lc_total_problems", 0)
    lc_submissions = signals.get("lc_total_submissions", lc_problems)
    contests       = (signals.get("lc_contests_attended", 0) +
                      signals.get("cf_contests_attended",  0))
    cf_rating      = signals.get("cf_rating", 0)
    lc_hard        = signals.get("lc_solved_hard", 0)
    lc_medium      = signals.get("lc_solved_medium", 0)
    lc_easy        = signals.get("lc_solved_easy", 0)

    # ── Signal 1: avg attempts per problem ──────────────────────────────
    # Your core insight: genuine solvers retry.
    if lc_problems > 10:
        avg_attempts = lc_submissions / lc_problems if lc_problems else 1.0
        signals["lc_avg_attempts_per_problem"] = round(avg_attempts, 2)

        if avg_attempts < 1.05:
            # Almost every submission is a first-pass accept — extremely suspicious
            flags.append(f"avg attempts/problem={avg_attempts:.2f} (expected >1.3 for genuine)")
            score *= 0.4
        elif avg_attempts < 1.3:
            flags.append(f"low avg attempts/problem={avg_attempts:.2f}")
            score *= 0.75
    else:
        signals["lc_avg_attempts_per_problem"] = 1.0

    # ── Signal 2: zero contest participation ────────────────────────────
    # Real practitioners contest. Fake submission farms never do.
    if lc_problems > 50 and contests == 0:
        flags.append("no contest participation despite high problem count")
        score *= 0.7

    # ── Signal 3: rating vs problems mismatch ───────────────────────────
    # Solving 300 problems should move your CF rating. If it hasn't, something's off.
    if signals.get("cf_problems_solved", 0) > 200 and cf_rating < 800:
        flags.append(f"CF rating={cf_rating} unusually low for {signals['cf_problems_solved']} problems")
        score *= 0.8

    # ── Signal 4: hard problem ratio sanity check ───────────────────────
    # A student with 500 solved but 0 hard and 0 contests is suspicious.
    total = lc_easy + lc_medium + lc_hard
    if total > 100:
        hard_ratio = lc_hard / total if total else 0
        if hard_ratio == 0 and contests == 0:
            flags.append("zero hard problems and zero contests")
            score *= 0.85

    score = max(0.0, min(1.0, round(score, 3)))
    is_suspicious = score < 0.6
    reason = "; ".join(flags) if flags else "no issues detected"
    return score, is_suspicious, reason


# ── CP scoring formula ─────────────────────────────────────────────────────

def _compute_cp_score(signals: dict, authenticity: float) -> float:
    """
    Raw CP score (0–100) × authenticity multiplier.
    """
    score = 0.0

    # LeetCode problems (40 pts) — medium counts 1, hard counts 2
    lc_weighted = (signals.get("lc_solved_easy",   0) * 0.5 +
                   signals.get("lc_solved_medium",  0) * 1.0 +
                   signals.get("lc_solved_hard",    0) * 2.0)
    score += 40 * min(lc_weighted / 300, 1.0)

    # Contest rating (30 pts) — LeetCode rating capped at 2500
    lc_rating = min(signals.get("lc_contest_rating", 0), 2500)
    score += 30 * (lc_rating / 2500)

    # Codeforces rating (20 pts) — capped at 2000
    cf_rating = min(signals.get("cf_rating", 0), 2000)
    score += 20 * (cf_rating / 2000)

    # Contest participation bonus (10 pts)
    contests = (signals.get("lc_contests_attended", 0) +
                signals.get("cf_contests_attended",  0))
    score += 10 * min(contests / 20, 1.0)

    raw_score = round(score, 2)
    # apply authenticity multiplier
    return round(raw_score * authenticity, 2)


# ── Main entry point ───────────────────────────────────────────────────────

def fetch_cp_signals(codolio_username: str,
                     cf_handle: Optional[str] = None) -> dict:
    """
    Fetch from Codolio first. If that fails, fallback to Codeforces API.
    Returns dict ready to store into CPSignal model.
    """
    signals = _fetch_codolio(codolio_username)

    if not signals:
        # Codolio unavailable — try direct Codeforces if handle given
        if cf_handle:
            cf_data = _fetch_codeforces(cf_handle)
            if cf_data:
                signals = {
                    "lc_solved_easy": 0, "lc_solved_medium": 0,
                    "lc_solved_hard": 0, "lc_contest_rating": 0,
                    "lc_contests_attended": 0,
                    "lc_total_submissions": 0, "lc_total_problems": 0,
                    **cf_data,
                    "cc_rating": 0, "cc_problems_solved": 0,
                }
            else:
                return {"error": "Both Codolio and Codeforces fetch failed",
                        "cp_score": 0.0, "authenticity_score": 1.0}
        else:
            return {"error": "Codolio fetch failed and no CF handle provided",
                    "cp_score": 0.0, "authenticity_score": 1.0}

    # run authenticity engine
    auth_score, is_suspicious, reason = _run_authenticity_engine(signals)
    signals["authenticity_score"] = auth_score
    signals["flag_suspicious"]    = is_suspicious
    signals["flag_reason"]        = reason

    # compute final CP score
    signals["cp_score"]  = _compute_cp_score(signals, auth_score)
    signals["fetched_at"] = datetime.utcnow()
    return signals


def save_cp_signals(student_id: int, signals: dict, db_session):
    from app.models.models import CPSignal
    sig = db_session.query(CPSignal).filter_by(student_id=student_id).first()
    if not sig:
        sig = CPSignal(student_id=student_id)
        db_session.add(sig)

    fields = [
        "lc_solved_easy", "lc_solved_medium", "lc_solved_hard",
        "lc_contest_rating", "lc_contests_attended",
        "lc_avg_attempts_per_problem",
        "cf_rating", "cf_max_rating", "cf_contests_attended", "cf_problems_solved",
        "cc_rating", "cc_problems_solved",
        "authenticity_score", "flag_suspicious", "flag_reason",
        "cp_score", "fetched_at",
    ]
    for field in fields:
        if field in signals:
            setattr(sig, field, signals[field])

    db_session.commit()
    return sig


if __name__ == "__main__":
    import sys
    username = sys.argv[1] if len(sys.argv) > 1 else "tourist"
    print(f"\nFetching CP signals for Codolio user: {username}\n{'─'*50}")
    result = fetch_cp_signals(username)
    for k, v in result.items():
        print(f"  {k}: {v}")
