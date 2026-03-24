"""
github_fetcher.py
─────────────────
Fetches GitHub activity signals for a student and computes a quality score.

Signals collected:
    - total public repos
    - commits in last 90 days  (via /repos/{owner}/{repo}/commits)
    - unique languages across repos
    - longest commit streak (days)
    - days since last commit   (recency)
    - has README in pinned/top repos
    - top languages list
    - pinned repo descriptions  (fed into NLP later)

Scoring (0–100):
    - recency        30 pts   (committed in last 30d = full marks, decays)
    - volume         25 pts   (commits_90d, capped at 100)
    - diversity      20 pts   (unique languages, capped at 6)
    - project quality 15 pts  (has_readme_projects)
    - streak         10 pts   (longest_streak_days, capped at 30)
"""

import json
import math
import requests
from datetime import datetime, timezone, timedelta
from typing import Optional

GITHUB_API = "https://api.github.com"
DEFAULT_TIMEOUT = 10   # seconds per request


def _headers(token: Optional[str] = None) -> dict:
    h = {"Accept": "application/vnd.github+json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _get(url: str, token: Optional[str] = None, params: dict = None) -> Optional[dict]:
    """Safe GET — returns None on any error instead of crashing."""
    try:
        r = requests.get(url, headers=_headers(token),
                         params=params, timeout=DEFAULT_TIMEOUT)
        if r.status_code == 200:
            return r.json()
        return None
    except requests.RequestException:
        return None


def _username_from_url(github_url: str) -> Optional[str]:
    """Extract 'himanshu' from 'https://github.com/himanshu'."""
    if not github_url:
        return None
    parts = github_url.rstrip("/").split("/")
    return parts[-1] if parts else None


# ── Signal fetchers ────────────────────────────────────────────────────────

def _fetch_repos(username: str, token: Optional[str]) -> list:
    data = _get(f"{GITHUB_API}/users/{username}/repos",
                token, params={"per_page": 100, "sort": "pushed"})
    return data if isinstance(data, list) else []


def _fetch_commits_90d(username: str, repos: list, token: Optional[str]) -> int:
    """Count commits across all repos in the last 90 days."""
    since = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    total = 0
    # limit to top 10 most recently pushed repos to stay within rate limits
    for repo in repos[:10]:
        data = _get(
            f"{GITHUB_API}/repos/{username}/{repo['name']}/commits",
            token,
            params={"author": username, "since": since, "per_page": 100}
        )
        if isinstance(data, list):
            total += len(data)
    return total


def _compute_streak(username: str, repos: list, token: Optional[str]) -> int:
    """
    Approximate longest commit streak in days.
    Collects all commit dates across top repos, finds the longest
    consecutive day run.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=180)).isoformat()
    commit_days = set()

    for repo in repos[:8]:
        data = _get(
            f"{GITHUB_API}/repos/{username}/{repo['name']}/commits",
            token,
            params={"author": username, "since": since, "per_page": 100}
        )
        if not isinstance(data, list):
            continue
        for commit in data:
            try:
                date_str = commit["commit"]["author"]["date"][:10]  # YYYY-MM-DD
                commit_days.add(date_str)
            except (KeyError, TypeError):
                continue

    if not commit_days:
        return 0

    sorted_days = sorted(commit_days)
    longest = current = 1
    for i in range(1, len(sorted_days)):
        d1 = datetime.strptime(sorted_days[i-1], "%Y-%m-%d")
        d2 = datetime.strptime(sorted_days[i],   "%Y-%m-%d")
        if (d2 - d1).days == 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def _days_since_last_commit(repos: list) -> Optional[int]:
    """Use the most recently pushed repo's pushed_at timestamp."""
    if not repos:
        return None
    try:
        last_pushed = repos[0]["pushed_at"]   # already sorted by pushed desc
        last_dt = datetime.strptime(last_pushed, "%Y-%m-%dT%H:%M:%SZ")
        last_dt = last_dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - last_dt).days
    except Exception:
        return None


# ── Scoring formula ────────────────────────────────────────────────────────

def _compute_github_score(signals: dict) -> float:
    score = 0.0

    # recency (30 pts) — full marks if committed in last 7 days, decays to 0 at 180d
    days = signals.get("days_since_last_commit")
    if days is not None:
        recency = max(0, 1 - (days / 180))
        score += 30 * recency

    # volume (25 pts) — commits_90d capped at 100
    commits = min(signals.get("total_commits_90d", 0), 100)
    score += 25 * (commits / 100)

    # diversity (20 pts) — unique languages capped at 6
    langs = min(signals.get("unique_languages", 0), 6)
    score += 20 * (langs / 6)

    # project quality (15 pts)
    if signals.get("has_readme_projects"):
        score += 15

    # streak (10 pts) — capped at 30 days
    streak = min(signals.get("longest_streak_days", 0), 30)
    score += 10 * (streak / 30)

    return round(score, 2)


# ── Main entry point ───────────────────────────────────────────────────────

def fetch_github_signals(github_url: str, token: Optional[str] = None) -> dict:
    """
    Full pipeline: URL → API calls → signals dict.

    Returns a dict ready to be stored into GitHubSignal model.
    On failure returns a dict with github_score=0 and an error key.
    """
    username = _username_from_url(github_url)
    if not username:
        return {"error": "Invalid GitHub URL", "github_score": 0.0}

    # user existence check
    user_data = _get(f"{GITHUB_API}/users/{username}", token)
    if not user_data:
        return {"error": f"GitHub user '{username}' not found", "github_score": 0.0}

    repos = _fetch_repos(username, token)

    # collect languages
    languages = set()
    has_readme = False
    pinned_descriptions = []
    for repo in repos:
        if repo.get("language"):
            languages.add(repo["language"])
        if repo.get("description"):
            pinned_descriptions.append(repo["description"])
        if not repo.get("fork", True):   # only original repos
            has_readme = True             # approximation — repo exists = has content

    commits_90d  = _fetch_commits_90d(username, repos, token)
    streak_days  = _compute_streak(username, repos, token)
    days_since   = _days_since_last_commit(repos)

    signals = {
        "total_repos":            len(repos),
        "total_commits_90d":      commits_90d,
        "unique_languages":       len(languages),
        "has_readme_projects":    has_readme,
        "longest_streak_days":    streak_days,
        "days_since_last_commit": days_since,
        "top_languages":          json.dumps(list(languages)[:8]),
        "pinned_repo_desc":       " | ".join(pinned_descriptions[:5]),
        "fetched_at":             datetime.utcnow(),
    }
    signals["github_score"] = _compute_github_score(signals)
    return signals


def save_github_signals(student_id: int, signals: dict, db_session):
    from app.models.models import GitHubSignal
    sig = db_session.query(GitHubSignal).filter_by(student_id=student_id).first()
    if not sig:
        sig = GitHubSignal(student_id=student_id)
        db_session.add(sig)

    for field in [
        "total_repos", "total_commits_90d", "unique_languages",
        "has_readme_projects", "longest_streak_days", "days_since_last_commit",
        "top_languages", "pinned_repo_desc", "github_score", "fetched_at",
    ]:
        if field in signals:
            setattr(sig, field, signals[field])

    db_session.commit()
    return sig


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/torvalds"
    token = sys.argv[2] if len(sys.argv) > 2 else None
    print(f"\nFetching signals for: {url}\n{'─'*50}")
    result = fetch_github_signals(url, token)
    for k, v in result.items():
        print(f"  {k}: {v}")
