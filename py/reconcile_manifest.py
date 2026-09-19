#!/usr/bin/env python3
"""Mark countries `done` that genuinely completed but were mis-scored.

The runner's completeness gate used `find -newermt "@<epoch>"`, which BSD find
cannot parse. The error was discarded and every country was recorded as
0-of-7 agents, so countries that had in fact run all seven agents are sitting
in the manifest as `incomplete_0of7` and would be re-run from scratch on the
next launch - hours of duplicated work per country.

A country is reconciled to `done` only when all three hold:
  1. all seven canonical search_log_agent_N.txt exist and were written after
     the country's first recorded start in this run,
  2. ./data/{ISO}/search_report.txt exists (Agent 7's deliverable),
  3. py/validate_quality.py exits clean for it.

Anything short of that is left alone to be re-run, which is the safe direction
to be wrong in.

Usage:
    python py/reconcile_manifest.py              # report only
    python py/reconcile_manifest.py --apply
"""
import argparse
import csv
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "reference" / "run_manifest.csv"
FIELDS = ["iso", "status", "started", "finished", "rows_before", "rows_after",
          "sources_before", "sources_after", "exit_code", "log"]


def csvcount(p):
    if not p.exists():
        return 0
    try:
        with open(p, newline="", encoding="utf-8") as fh:
            return sum(1 for _ in csv.DictReader(fh))
    except Exception:
        return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    if not MANIFEST.exists():
        print("no manifest"); return 0

    rows = list(csv.DictReader(open(MANIFEST, newline="")))
    first_start, last_status = {}, {}
    for r in rows:
        iso = r.get("iso")
        if not iso:
            continue
        last_status[iso] = r.get("status")
        if iso not in first_start and r.get("started"):
            first_start[iso] = r["started"]

    promote = []
    for iso, status in sorted(last_status.items()):
        if status == "done":
            continue
        d = ROOT / "data" / iso
        try:
            t0 = datetime.strptime(first_start[iso], "%Y-%m-%d %H:%M:%S").timestamp()
        except (KeyError, ValueError):
            continue

        logs = [d / f"search_log_agent_{k}.txt" for k in range(1, 8)]
        missing = [p.name for p in logs if not p.exists()]
        stale = [p.name for p in logs if p.exists() and p.stat().st_mtime <= t0]
        report = d / "search_report.txt"

        why = []
        if missing:
            why.append(f"missing {len(missing)}")
        if stale:
            why.append(f"{len(stale)} not rewritten this run")
        if not report.exists():
            why.append("no search_report.txt")
        if why:
            print(f"  {iso:4s} leave as {status:16s} ({'; '.join(why)})")
            continue

        rc = subprocess.run([sys.executable, "py/validate_quality.py", iso, "--quiet"],
                            cwd=ROOT, capture_output=True, text=True).returncode
        if rc != 0:
            print(f"  {iso:4s} leave as {status:16s} (validation exit {rc})")
            continue

        promote.append(iso)
        print(f"  {iso:4s} PROMOTE {status} -> done  (7/7 agents, report present, validation clean)")

    if not promote:
        print("\nnothing to reconcile")
        return 0
    if not a.apply:
        print(f"\n{len(promote)} country(ies) would be promoted; re-run with --apply")
        return 0

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(MANIFEST, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        for iso in promote:
            src = [r for r in rows if r.get("iso") == iso][-1]
            w.writerow({
                "iso": iso, "status": "done",
                "started": first_start.get(iso, ""), "finished": now,
                "rows_before": src.get("rows_before", ""),
                "rows_after": csvcount(ROOT / "data" / iso / "cholera_data_ai.csv"),
                "sources_before": src.get("sources_before", ""),
                "sources_after": csvcount(ROOT / "data" / iso / "metadata_ai.csv"),
                "exit_code": "0", "log": "reconciled",
            })
    print(f"\nmarked done: {' '.join(promote)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
