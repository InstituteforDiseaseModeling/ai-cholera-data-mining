#!/usr/bin/env python3
"""
Deterministic regression gate for the 40 MOSAIC countries.

Rebuilds the outputs that pipeline changes can disturb - into a temporary
directory, never over the tracked files - with the date pinned, and hashes
only the 40 MOSAIC countries' part of each:

  weekly/{ISO}   py/build_weekly_timeseries.py --as-of D --out-dir TMP --no-plots
  gaps/{file}    py/analyze_effective_gaps.py --end-date D --out-dir TMP,
                 rows filtered to the 40 ISO codes (pilot rows never count)
  validate/{ISO} py/validate_quality.py --as-of D --json, findings per country

Usage:
  python3 py/regression_snapshot.py take --as-of 2026-11-18 --out snap_before.json
  python3 py/regression_snapshot.py take --as-of 2026-11-18 --out snap_after.json
  python3 py/regression_snapshot.py compare snap_before.json snap_after.json

Take the reference snapshot from a fixed git worktree at the pre-change
commit (git worktree add <dir> <commit>; run the script inside it), with the
same --as-of, so later data edits on the working branch cannot move the
reference. `compare` exits 1 on any difference and names each changed item.
"""

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def mosaic_isos():
    # Read directly (not via py/scope.py) so the gate runs unchanged at the
    # pre-change reference commit.
    m = json.loads((ROOT / "reference" / "country_mapping.json").read_text())["countries"]
    return sorted(k for k, v in m.items() if v.get("mosaic_framework"))

GAP_FILES = [
    "effective_surveillance_gaps_detailed.csv",
    "effective_surveillance_gaps_annual.csv",
    "effective_surveillance_gaps_coverage.csv",
    "effective_surveillance_recency.csv",
]


# The dashboard runs the builder with `python` (anaconda: numpy, matplotlib);
# the framework `python3` lacks numpy. Override with PIPELINE_PYTHON.
PY = os.environ.get("PIPELINE_PYTHON") or shutil.which("python") or sys.executable


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def take(as_of, out):
    mosaic = set(mosaic_isos())
    snap = {"as_of": as_of, "commit": run(["git", "rev-parse", "HEAD"])[1].strip(),
            "items": {}}
    items = snap["items"]
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        rc, so, se = run([PY, "py/build_weekly_timeseries.py",
                          "--as-of", as_of, "--out-dir", str(tmp / "weekly"), "--no-plots"])
        if rc:
            sys.exit(f"builder failed:\n{se[-2000:]}")
        for iso in sorted(mosaic):
            f = tmp / "weekly" / iso / f"cholera_weekly_{iso}.csv"
            items[f"weekly/{iso}"] = sha(f.read_bytes()) if f.exists() else None

        rc, so, se = run([PY, "py/analyze_effective_gaps.py",
                          "--end-date", as_of, "--out-dir", str(tmp / "gaps")])
        if rc:
            sys.exit(f"gap analysis failed:\n{se[-2000:]}")
        for name in GAP_FILES:
            f = tmp / "gaps" / name
            if not f.exists():
                items[f"gaps/{name}"] = None
                continue
            rows = list(csv.DictReader(open(f, newline="", encoding="utf-8")))
            keep = [r for r in rows if r.get("iso_code") in mosaic]
            buf = io.StringIO()
            if rows:
                w = csv.DictWriter(buf, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(keep)
            items[f"gaps/{name}"] = sha(buf.getvalue().encode())

        vj = tmp / "validate.json"
        rc, so, se = run([PY, "py/validate_quality.py", "--as-of", as_of,
                          "--quiet", "--json", str(vj)])
        if not vj.exists():
            sys.exit(f"validator produced no report (exit {rc}):\n{se[-2000:]}")
        rep = json.loads(vj.read_text())
        by_iso = {}
        for f in rep["findings"]:
            if f.get("iso") in mosaic:
                by_iso.setdefault(f["iso"], []).append(
                    {k: f.get(k) for k in ("severity", "check", "message", "row")})
        for iso in sorted(mosaic):
            items[f"validate/{iso}"] = sha(json.dumps(by_iso.get(iso, []),
                                                      sort_keys=True).encode())
        snap["validate_exit"] = rc

    Path(out).write_text(json.dumps(snap, indent=1, sort_keys=True))
    print(f"snapshot of {len(items)} items at commit {snap['commit'][:10]} "
          f"(as of {as_of}) -> {out}")


def compare(a, b):
    A, B = json.loads(Path(a).read_text()), json.loads(Path(b).read_text())
    if A["as_of"] != B["as_of"]:
        print(f"WARNING: different --as-of ({A['as_of']} vs {B['as_of']}); "
              f"the comparison is not meaningful")
    keys = sorted(set(A["items"]) | set(B["items"]))
    diff = [k for k in keys if A["items"].get(k) != B["items"].get(k)]
    if A.get("validate_exit") != B.get("validate_exit"):
        diff.append(f"validate_exit {A.get('validate_exit')} -> {B.get('validate_exit')}")
    if diff:
        print(f"REGRESSION: {len(diff)} of {len(keys)} items differ:")
        for k in diff:
            print(f"  {k}")
        return 1
    print(f"OK: all {len(keys)} items identical "
          f"({A['commit'][:10]} vs {B['commit'][:10]}, as of {A['as_of']})")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("take")
    t.add_argument("--as-of", required=True)
    t.add_argument("--out", required=True)
    c = sub.add_parser("compare")
    c.add_argument("a")
    c.add_argument("b")
    args = ap.parse_args()
    if args.cmd == "take":
        take(args.as_of, args.out)
        return 0
    return compare(args.a, args.b)


if __name__ == "__main__":
    sys.exit(main())
