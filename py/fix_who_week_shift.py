#!/usr/bin/env python3
"""One-time repair: re-date WHO baseline rows onto WHO's own week-start dates.

convert_who_to_workflow.py used to map a WHO epi-week number onto ISO week N of
the same year. WHO epi-weeks are not ISO weeks, and for 2026 they are offset by
one, so every 2026 WHO row was written a week early. Nigeria showed 855 cases at
ISO week 18 where the true value for that week is 56.

The converter is fixed (it now reads reference/who_epiweek_calendar.json), but
the already-generated data/{ISO}/cholera_data_who.csv files still carry the old
dates. Re-running the converter is not a safe way to repair them: it appends
rather than replaces, and the current upstream extract is a different vintage
from the one these files were built from, so a regeneration would silently
change case values as well as dates. This re-dates the existing rows and touches
nothing else.

The correction is derived, not assumed. For each row the ISO week number is read
back out of its TL, that number is looked up in WHO's calendar, and TL/TR are
rewritten to WHO's own dates - so a year where the two schemes agree is left
untouched automatically.

Usage:
    python py/fix_who_week_shift.py --dry-run
    python py/fix_who_week_shift.py --apply
"""

import argparse
import csv
import json
import re
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CALENDAR = ROOT / "reference" / "who_epiweek_calendar.json"
NOTE_RE = re.compile(r"for week (\d+) of (\d{4})")


def load_calendar():
    weeks = json.loads(CALENDAR.read_text())["weeks"]
    return weeks


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    cal = load_calendar()
    files = sorted((ROOT / "data").glob("*/cholera_data_who.csv"))
    tot_rows = tot_fixed = 0
    by_year = {}
    changed_files = []
    examples = []

    for f in files:
        with open(f, newline="", encoding="utf-8-sig") as fh:
            rdr = csv.DictReader(fh)
            fields = rdr.fieldnames
            rows = list(rdr)
        if not rows:
            continue
        n_fixed = 0
        for r in rows:
            tot_rows += 1
            tl = (r.get("TL") or "").strip()
            if len(tl) != 10:
                continue
            try:
                d = date.fromisoformat(tl)
            except ValueError:
                continue

            # The converter wrote TL as the Monday of ISO week N for WHO week N,
            # so the ISO week of TL recovers the WHO week number. Prefer the
            # week stated in processing_notes where it exists - it is what the
            # converter actually read from the source.
            m = NOTE_RE.search(r.get("processing_notes") or "")
            if m:
                wk, yr = int(m.group(1)), int(m.group(2))
            else:
                iso = d.isocalendar()
                wk, yr = iso[1], iso[0]

            true_start = cal.get(f"{yr}-{wk:02d}")
            if not true_start:
                continue
            if true_start == tl:
                continue                      # already correct; nothing to do

            new_tl = date.fromisoformat(true_start)
            new_tr = new_tl + timedelta(days=6)
            if len(examples) < 6:
                examples.append(
                    f"    {f.parent.name} WHO {yr}w{wk:02d}: "
                    f"{tl}..{r.get('TR')} -> {new_tl}..{new_tr}  "
                    f"(sCh={r.get('sCh')})")
            r["TL"] = new_tl.isoformat()
            r["TR"] = new_tr.isoformat()
            # reporting_date must stay >= TR
            rd = (r.get("reporting_date") or "").strip()
            if len(rd) == 10:
                try:
                    if date.fromisoformat(rd) < new_tr:
                        r["reporting_date"] = new_tr.isoformat()
                except ValueError:
                    pass
            n_fixed += 1
            by_year[yr] = by_year.get(yr, 0) + 1

        if n_fixed:
            changed_files.append((f, n_fixed, rows, fields))
            tot_fixed += n_fixed

    print(f"scanned {len(files)} files, {tot_rows} rows")
    print(f"rows needing re-dating: {tot_fixed} across {len(changed_files)} countries")
    for yr in sorted(by_year):
        print(f"  {yr}: {by_year[yr]}")
    if examples:
        print("  examples:")
        for e in examples:
            print(e)

    if not a.apply:
        print("\n(dry run - nothing written)")
        return 0
    if not tot_fixed:
        print("\nnothing to do")
        return 0

    for f, n, rows, fields in changed_files:
        shutil.copy2(f, f.with_suffix(".csv.prefix_backup"))
        tmp = f.with_suffix(".csv.tmp")
        with open(tmp, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        tmp.replace(f)
    print(f"\nrewrote {len(changed_files)} files "
          f"(originals kept as *.csv.prefix_backup)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
