#!/usr/bin/env python3
"""
Normalize metadata_ai.csv files across all 40 MOSAIC countries.

Fixes:
1. Reliability_Level: "1" → "Level 1", "Level_1" → "Level 1", "0.7" → "Level 2", etc.
2. Date_Range: "/" separator → " to " (e.g. "2015-01-01/2015-12-31" → "2015-01-01 to 2015-12-31")
3. source_database: "AI32" → "AI", "Systematic search" → "AI"
4. Status: "validated" (lowercase) → "Validated"
"""

import csv
import io
import re
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

RELIABILITY_MAP = {
    "1":       "Level 1",
    "2":       "Level 2",
    "3":       "Level 3",
    "4":       "Level 4",
    "Level_1": "Level 1",
    "Level_2": "Level 2",
    "Level_3": "Level 3",
    "Level_4": "Level 4",
    "0.7":     "Level 2",   # 0.7 weight = Level 2 boundary
    "0.8":     "Level 2",
    "0.9":     "Level 1",
    "1.0":     "Level 1",
}

# Status values to normalise (only capitalisation fixes)
STATUS_MAP = {
    "validated": "Validated",
    "VALIDATED": "Validated",
    "verified":  "Verified",
    "VERIFIED":  "Verified",
    "active":    "Active",
    "ACTIVE":    "Active",
}

EXPECTED_COLS = [
    "Index","Source","URL","Description","Date_Range","Data_Type",
    "Status","Reliability_Level","Validation_Status","Search_Technique",
    "Language_Original","Citation_Depth","Cross_References","Discovery_Method","source_database"
]


def fix_date_range(dr: str) -> str:
    """Convert slash-separated date ranges to ' to ' format."""
    dr = dr.strip()
    if "/" in dr:
        parts = dr.split("/", 1)
        if len(parts) == 2:
            return f"{parts[0].strip()} to {parts[1].strip()}"
    return dr


def fix_reliability(r: str) -> str:
    r = r.strip()
    if r in RELIABILITY_MAP:
        return RELIABILITY_MAP[r]
    # If it looks like "Active" or something clearly wrong in this field, keep as-is
    # and flag it — caller will log a warning
    return r


def fix_source_database(db: str) -> str:
    db = db.strip()
    if db in ("AI", "JHU", "WHO", ""):
        return db
    # Known bad values
    if db.startswith("AI") and db != "AI":  # e.g. "AI32"
        return "AI"
    if db in ("Systematic search", "systematic search", "Web Search", "Web search"):
        return "AI"
    return db


def fix_status(s: str) -> str:
    return STATUS_MAP.get(s.strip(), s.strip())


def fix_comma_in_url_rows(content: str, fieldnames: list) -> tuple[str, list]:
    """
    Detect and repair rows where an unquoted comma inside the URL field causes
    a column shift. Returns corrected CSV content and list of fix descriptions.
    """
    fixes = []
    lines = content.split('\n')
    corrected = [lines[0]]  # keep header
    n_expected = len(fieldnames)

    for lineno, line in enumerate(lines[1:], start=2):
        if not line.strip():
            corrected.append(line)
            continue
        # Quick check: does this row parse to more columns than expected?
        import csv as _csv
        parsed = next(_csv.reader([line]))
        if len(parsed) == n_expected:
            corrected.append(line)
            continue
        if len(parsed) == n_expected + 1:
            # Likely the URL (col 2) contains an unquoted comma — join cols 2 and 3
            fixed_url = parsed[2] + "," + parsed[3]
            new_fields = parsed[:2] + [fixed_url] + parsed[4:]
            if len(new_fields) == n_expected:
                # Re-serialize with proper quoting
                buf = _csv.StringIO()
                writer = _csv.writer(buf, quoting=_csv.QUOTE_MINIMAL)
                writer.writerow(new_fields)
                corrected.append(buf.getvalue().rstrip('\r\n'))
                fixes.append(f"  line {lineno}: unquoted comma in URL repaired → '{fixed_url[:60]}...'")
                continue
        corrected.append(line)
    return '\n'.join(corrected), fixes


def process_country(iso: str, meta_path: Path, dry_run: bool = False) -> dict:
    changes = defaultdict(list)

    with open(meta_path, newline="", encoding="utf-8") as f:
        content = f.read()

    # First pass: fix any unquoted commas in URL field
    reader_check = csv.DictReader(io.StringIO(content))
    fieldnames = reader_check.fieldnames
    if not fieldnames:
        return {"error": "empty file"}
    content, url_fixes = fix_comma_in_url_rows(content, fieldnames)
    if url_fixes:
        changes["URL_comma_repair"] = url_fixes

    reader = csv.DictReader(io.StringIO(content))
    fieldnames = reader.fieldnames

    if not fieldnames:
        return {"error": "empty file"}

    rows = list(reader)
    if not rows:
        return dict(changes)
    new_rows = []

    for row in rows:
        new_row = dict(row)
        idx = row.get("Index", "?")

        # 1. Reliability_Level
        orig_r = row.get("Reliability_Level", "").strip()
        fixed_r = fix_reliability(orig_r)
        if fixed_r != orig_r:
            if orig_r not in ("Level 1", "Level 2", "Level 3", "Level 4", ""):
                new_row["Reliability_Level"] = fixed_r
                changes["Reliability_Level"].append(
                    f"  row {idx}: '{orig_r}' → '{fixed_r}'"
                )

        # 2. Date_Range
        orig_dr = row.get("Date_Range", "").strip()
        fixed_dr = fix_date_range(orig_dr)
        if fixed_dr != orig_dr:
            new_row["Date_Range"] = fixed_dr
            changes["Date_Range"].append(
                f"  row {idx}: '{orig_dr}' → '{fixed_dr}'"
            )

        # 3. source_database
        orig_db = row.get("source_database", "").strip()
        fixed_db = fix_source_database(orig_db)
        if fixed_db != orig_db:
            new_row["source_database"] = fixed_db
            changes["source_database"].append(
                f"  row {idx}: '{orig_db}' → '{fixed_db}'"
            )

        # 4. Status capitalisation
        orig_st = row.get("Status", "").strip()
        fixed_st = fix_status(orig_st)
        if fixed_st != orig_st:
            new_row["Status"] = fixed_st
            changes["Status"].append(
                f"  row {idx}: '{orig_st}' → '{fixed_st}'"
            )

        new_rows.append(new_row)

    if changes and not dry_run:
        with open(meta_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(new_rows)

    return dict(changes)


def main(dry_run: bool = False):
    total_changes = 0
    countries_changed = 0

    print(f"{'DRY RUN — ' if dry_run else ''}Normalizing metadata_ai.csv files\n")
    print(f"{'='*60}")

    for d in sorted(DATA_DIR.iterdir()):
        if not d.is_dir():
            continue
        iso = d.name
        meta = d / "metadata_ai.csv"
        if not meta.exists():
            continue

        changes = process_country(iso, meta, dry_run=dry_run)

        if changes:
            countries_changed += 1
            n = sum(len(v) for v in changes.values())
            total_changes += n
            print(f"\n{iso} ({n} fixes):")
            for field, items in changes.items():
                print(f"  [{field}]")
                for item in items:
                    print(item)

    print(f"\n{'='*60}")
    print(f"Total: {total_changes} fixes across {countries_changed} countries")
    if dry_run:
        print("(DRY RUN — no files written)")
    else:
        print("All files updated.")


if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
