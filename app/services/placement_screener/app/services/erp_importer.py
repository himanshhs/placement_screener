"""
erp_importer.py
───────────────
Bulk-imports students from a CSV exported from the college ERP.

Expected CSV columns (case-insensitive, order doesn't matter):
    erp_id, name, email, branch, year, cgpa, backlogs,
    tenth_pct, twelfth_pct, github_url, linkedin_url,
    leetcode_user, codeforces_user, codechef_user

Only erp_id, name, email are mandatory.
All others are optional — missing = stored as None.

Usage:
    result = import_from_csv("students.csv", db.session)
    print(result["imported"], result["skipped"], result["errors"])
"""

import csv
import io
from datetime import datetime
from typing import Union


# map of our field names → possible CSV column header variants
COLUMN_MAP = {
    "erp_id":           ["erp_id", "roll_no", "prn", "roll", "student_id", "id"],
    "name":             ["name", "student_name", "full_name"],
    "email":            ["email", "email_id", "mail"],
    "branch":           ["branch", "dept", "department", "stream"],
    "year":             ["year", "current_year", "sem_year"],
    "cgpa":             ["cgpa", "gpa", "cpi"],
    "backlogs":         ["backlogs", "backlog", "atkt"],
    "tenth_pct":        ["tenth_pct", "tenth", "10th", "ssc"],
    "twelfth_pct":      ["twelfth_pct", "twelfth", "12th", "hsc"],
    "github_url":       ["github_url", "github", "github_link"],
    "linkedin_url":     ["linkedin_url", "linkedin", "linkedin_link"],
    "leetcode_user":    ["leetcode_user", "leetcode"],
    "codeforces_user":  ["codeforces_user", "codeforces", "cf_handle"],
    "codechef_user":    ["codechef_user", "codechef", "cc_handle"],
}


def _normalise_headers(raw_headers: list) -> dict:
    """
    Returns a mapping of {our_field: csv_column_index}
    by matching raw CSV headers against COLUMN_MAP variants.
    """
    lowered = [h.strip().lower() for h in raw_headers]
    mapping = {}
    for field, variants in COLUMN_MAP.items():
        for variant in variants:
            if variant in lowered:
                mapping[field] = lowered.index(variant)
                break
    return mapping


def _get_val(row: list, col_map: dict, field: str,
             default=None, cast=None):
    """Safely get a value from a CSV row by field name."""
    idx = col_map.get(field)
    if idx is None or idx >= len(row):
        return default
    raw = row[idx].strip()
    if not raw:
        return default
    if cast:
        try:
            return cast(raw)
        except (ValueError, TypeError):
            return default
    return raw


def import_from_csv(
    source: Union[str, io.StringIO],
    db_session,
    update_existing: bool = True
) -> dict:
    """
    Import students from a CSV file path or StringIO object.

    Args:
        source:          file path string or StringIO
        db_session:      SQLAlchemy session
        update_existing: if True, updates existing student rows;
                         if False, skips them

    Returns:
        {
            imported: int,   # new rows created
            updated:  int,   # existing rows updated
            skipped:  int,   # rows skipped (duplicate + update_existing=False)
            errors:   list   # [{row, reason}]
        }
    """
    from app.models.models import Student

    if isinstance(source, str):
        f = open(source, newline="", encoding="utf-8-sig")
    else:
        f = source

    try:
        reader = csv.reader(f)
        headers = next(reader)
        col_map = _normalise_headers(headers)

        if "erp_id" not in col_map or "name" not in col_map or "email" not in col_map:
            return {
                "imported": 0, "updated": 0, "skipped": 0,
                "errors": [{"row": 0, "reason":
                    "CSV missing required columns: erp_id, name, email"}]
            }

        imported = updated = skipped = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):
            if not any(row):       # skip blank lines
                continue

            erp_id = _get_val(row, col_map, "erp_id")
            name   = _get_val(row, col_map, "name")
            email  = _get_val(row, col_map, "email")

            if not erp_id or not name or not email:
                errors.append({"row": row_num,
                                "reason": "Missing erp_id, name, or email"})
                continue

            existing = db_session.query(Student).filter_by(erp_id=erp_id).first()

            if existing and not update_existing:
                skipped += 1
                continue

            student = existing or Student()
            student.erp_id         = erp_id
            student.name           = name
            student.email          = email
            student.branch         = _get_val(row, col_map, "branch")
            student.year           = _get_val(row, col_map, "year",    cast=int)
            student.cgpa           = _get_val(row, col_map, "cgpa",    cast=float)
            student.backlogs       = _get_val(row, col_map, "backlogs",cast=int, default=0)
            student.tenth_pct      = _get_val(row, col_map, "tenth_pct",  cast=float)
            student.twelfth_pct    = _get_val(row, col_map, "twelfth_pct",cast=float)
            student.github_url     = _get_val(row, col_map, "github_url")
            student.linkedin_url   = _get_val(row, col_map, "linkedin_url")
            student.leetcode_user  = _get_val(row, col_map, "leetcode_user")
            student.codeforces_user= _get_val(row, col_map, "codeforces_user")
            student.codechef_user  = _get_val(row, col_map, "codechef_user")
            student.updated_at     = datetime.utcnow()

            if not existing:
                db_session.add(student)
                imported += 1
            else:
                updated += 1

        db_session.commit()
        return {"imported": imported, "updated": updated,
                "skipped": skipped, "errors": errors}

    except Exception as e:
        db_session.rollback()
        return {"imported": 0, "updated": 0, "skipped": 0,
                "errors": [{"row": 0, "reason": str(e)}]}
    finally:
        if isinstance(source, str):
            f.close()


def generate_sample_csv() -> str:
    """Returns a sample CSV string the placement cell can use as a template."""
    headers = [
        "erp_id","name","email","branch","year","cgpa","backlogs",
        "tenth_pct","twelfth_pct","github_url","leetcode_user","codeforces_user"
    ]
    rows = [
        ["CS2021001","Himanshu Patil","himanshu@college.edu","CSE","3",
         "8.7","0","91.2","87.5","https://github.com/himanshu","himanshu_lc","himanshu_cf"],
        ["CS2021002","Priya Sharma","priya@college.edu","IT","3",
         "7.9","0","85.0","82.3","https://github.com/priya","","priya_cf"],
    ]
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(headers)
    writer.writerows(rows)
    return out.getvalue()
