#!/usr/bin/env python3
"""
Effective surveillance gap analysis across ALL data layers (JHU + WHO + AI).

Why this exists alongside py/analyze_baseline_gaps_optimized.py
---------------------------------------------------------------
The baseline analyser reads only cholera_data_jhu.csv and cholera_data_who.csv.
That is the right input for measuring what the AI layer *added*, but it is the
wrong input for deciding where to search next: it reports gaps the AI layer has
already filled, so a re-run spends its query budget re-discovering known data.
This module computes the gaps that actually remain.

It also fixes two defects in the baseline analyser's coverage maths:

  1. Day counting used ``max(existing, days_covered)`` per month, so two
     10-day observations covering different halves of a month recorded 10
     covered days instead of 20. Coverage is now the union of covered days.

  2. Every row counted as coverage regardless of content, including rows with
     no case value at all. Coverage is now classified:
       informative  - any row that tells us something, including a documented zero
       positive     - a row with sCh>0, cCh>0 or deaths>0

Outputs (written to ./reference/):
    effective_surveillance_gaps_detailed.csv   consolidated gap periods >= min-days
    effective_surveillance_gaps_annual.csv     years with >= 6 months missing
    effective_surveillance_gaps_coverage.csv   per-country coverage summary
    effective_surveillance_recency.csv         latest observation per country vs today

Usage:
    python py/analyze_effective_gaps.py
    python py/analyze_effective_gaps.py --layers JHU WHO        # baseline only
    python py/analyze_effective_gaps.py --min-gap-days 30
"""

import argparse
import calendar
import csv
import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
REF = ROOT / "reference"

START = date(1970, 1, 1)

# Matches the note left by py/convert_who_to_workflow.py on a week the WHO
# dashboard reported zero cases. Older who.csv files record that as blank
# count columns, so the note is the only surviving evidence the week was
# actually covered.
WHO_ZERO_RE = re.compile(r"WHO dashboard data:\s*0(\.0)?\s*cases", re.I)

LAYER_FILES = {
    "JHU": "cholera_data_jhu.csv",
    "WHO": "cholera_data_who.csv",
    "AI": "cholera_data_ai.csv",
}


def parse_date(s):
    s = (s or "").strip()[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def to_num(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def month_iter(start, end):
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def load_observations(iso, layers, end_date):
    """Return list of (TL, TR, layer, is_positive) clipped to [START, end_date]."""
    obs = []
    for layer in layers:
        path = DATA / iso / LAYER_FILES[layer]
        if not path.exists():
            continue
        with open(path, newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                tl, tr = parse_date(r.get("TL")), parse_date(r.get("TR"))
                if not tl or not tr or tl > tr:
                    continue
                # Never let a future-dated row manufacture coverage.
                if tr > end_date:
                    tr = end_date
                if tl < START or tl > tr:
                    continue
                vals = [to_num(r.get(k)) for k in ("sCh", "cCh", "deaths")]
                positive = any(v is not None and v > 0 for v in vals)
                informative = any(v is not None for v in vals)
                if not informative and WHO_ZERO_RE.search(r.get("processing_notes") or ""):
                    # py/convert_who_to_workflow.py historically wrote an empty
                    # cell when the WHO dashboard reported zero, so a week WHO
                    # explicitly covered looks identical to a week it never
                    # touched. The note still says so verbatim. Recognising it
                    # here recovers 622 documented-zero weeks that were being
                    # dropped, which had manufactured 9 phantom 2025-26 gaps.
                    # The converter now emits 0 directly; this keeps already
                    # generated who.csv files correct without regenerating them.
                    informative = True
                if not informative:
                    # A row with no case value tells us nothing about presence or
                    # absence; it must not count as surveillance coverage.
                    continue
                obs.append((tl, tr, layer, positive))
    return obs


def covered_days_by_month(obs):
    """Union of covered days per (year, month), plus which layers contributed."""
    days = defaultdict(set)
    layers = defaultdict(set)
    positive_months = set()
    for tl, tr, layer, positive in obs:
        # Guard against a pathological range blowing up memory.
        if (tr - tl).days > 366 * 60:
            continue
        cur = tl
        while cur <= tr:
            key = (cur.year, cur.month)
            days[key].add(cur.day)
            layers[key].add(layer)
            if positive:
                positive_months.add(key)
            cur += timedelta(days=1)
    return days, layers, positive_months


def analyse(iso, name, layers, end_date, min_gap_days):
    obs = load_observations(iso, layers, end_date)
    days, layer_map, positive_months = covered_days_by_month(obs)

    months = list(month_iter(START, end_date))
    covered_flags = {}
    for (y, m) in months:
        dim = calendar.monthrange(y, m)[1]
        # A month counts as covered when more than half its days are observed.
        covered_flags[(y, m)] = len(days.get((y, m), ())) > dim / 2

    # ---- consolidate contiguous uncovered months into gap periods ----------
    gaps = []
    run_start = None
    for (y, m) in months:
        if not covered_flags[(y, m)]:
            if run_start is None:
                run_start = (y, m)
        elif run_start is not None:
            gaps.append((run_start, (y, m)))
            run_start = None
    if run_start is not None:
        gaps.append((run_start, None))

    detailed = []
    for start_ym, end_ym in gaps:
        gs = date(start_ym[0], start_ym[1], 1)
        if end_ym is None:
            ge = end_date
        else:
            prev_y, prev_m = (end_ym[0], end_ym[1] - 1) if end_ym[1] > 1 else (end_ym[0] - 1, 12)
            ge = date(prev_y, prev_m, calendar.monthrange(prev_y, prev_m)[1])
        if ge > end_date:
            ge = end_date
        n_days = (ge - gs).days + 1
        if n_days < min_gap_days:
            continue
        detailed.append({
            "country": name, "iso_code": iso,
            "gap_start": gs.isoformat(), "gap_end": ge.isoformat(),
            "days": n_days,
            "months": round(n_days / 30.44),
            "years": round(n_days / 365.25, 2),
            "era": ("historical" if ge.year < 2000
                    else "recent" if ge.year >= end_date.year - 2 else "modern"),
        })

    # ---- annual summary ---------------------------------------------------
    annual = []
    for y in range(START.year, end_date.year + 1):
        ms = [(yy, mm) for (yy, mm) in months if yy == y]
        missing = sum(1 for k in ms if not covered_flags[k])
        if missing >= 6:
            annual.append({"country": name, "iso_code": iso, "gap_year": y,
                           "months_missing": missing, "months_in_year": len(ms)})

    # ---- coverage summary -------------------------------------------------
    total = len(months)
    with_data = sum(1 for k in months if covered_flags[k])
    by_layer = defaultdict(int)
    for k in months:
        if covered_flags[k]:
            for lyr in layer_map.get(k, ()):
                by_layer[lyr] += 1
    ai_only = sum(1 for k in months
                  if covered_flags[k] and layer_map.get(k) == {"AI"})

    coverage = {
        "country": name, "iso_code": iso,
        "total_months": total,
        "months_with_data": with_data,
        "months_missing": total - with_data,
        "percent_coverage": round(with_data / total * 100, 1) if total else 0.0,
        "months_jhu": by_layer.get("JHU", 0),
        "months_who": by_layer.get("WHO", 0),
        "months_ai": by_layer.get("AI", 0),
        "months_ai_only": ai_only,
        "months_with_positive_cases": len(positive_months),
        "gap_periods": len(detailed),
    }

    # ---- recency ----------------------------------------------------------
    latest = max((tr for _, tr, _, _ in obs), default=None)
    latest_pos = max((tr for _, tr, _, p in obs if p), default=None)
    recency = {
        "country": name, "iso_code": iso,
        "latest_observation": latest.isoformat() if latest else "",
        "days_stale": (end_date - latest).days if latest else "",
        "latest_positive_observation": latest_pos.isoformat() if latest_pos else "",
        "observations": len(obs),
    }
    return detailed, annual, coverage, recency


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"  {path.relative_to(ROOT)}  ({len(rows)} rows)")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--layers", nargs="+", default=["JHU", "WHO", "AI"],
                    choices=list(LAYER_FILES))
    ap.add_argument("--min-gap-days", type=int, default=7)
    ap.add_argument("--end-date", default=date.today().isoformat(),
                    help="analysis horizon (default: today). Coverage is never "
                         "credited beyond this date.")
    ap.add_argument("--prefix", default="effective")
    args = ap.parse_args()

    end_date = parse_date(args.end_date)
    if not end_date:
        raise SystemExit(f"bad --end-date: {args.end_date}")

    mapping = json.loads((REF / "country_mapping.json").read_text())["countries"]
    mosaic = sorted(k for k, v in mapping.items() if v.get("mosaic_framework"))

    all_detailed, all_annual, all_cov, all_rec = [], [], [], []
    for iso in mosaic:
        d, a, c, r = analyse(iso, mapping[iso]["name"], args.layers, end_date,
                             args.min_gap_days)
        all_detailed += d
        all_annual += a
        all_cov.append(c)
        all_rec.append(r)

    print(f"Effective gap analysis | layers={'+'.join(args.layers)} | "
          f"horizon={end_date} | min gap={args.min_gap_days}d\n")
    write_csv(REF / f"{args.prefix}_surveillance_gaps_detailed.csv", all_detailed,
              ["country", "iso_code", "gap_start", "gap_end", "days", "months", "years", "era"])
    write_csv(REF / f"{args.prefix}_surveillance_gaps_annual.csv", all_annual,
              ["country", "iso_code", "gap_year", "months_missing", "months_in_year"])
    write_csv(REF / f"{args.prefix}_surveillance_gaps_coverage.csv", all_cov,
              list(all_cov[0]))
    write_csv(REF / f"{args.prefix}_surveillance_recency.csv",
              sorted(all_rec, key=lambda r: r["latest_observation"]), list(all_rec[0]))

    mean_cov = sum(c["percent_coverage"] for c in all_cov) / len(all_cov)
    stale = [r for r in all_rec if isinstance(r["days_stale"], int) and r["days_stale"] > 180]
    by_era = defaultdict(int)
    for g in all_detailed:
        by_era[g["era"]] += 1
    print(f"\n  mean coverage      : {mean_cov:.1f}%")
    print(f"  gap periods        : {len(all_detailed)} "
          f"(historical {by_era['historical']}, modern {by_era['modern']}, recent {by_era['recent']})")
    print(f"  AI-only months     : {sum(c['months_ai_only'] for c in all_cov)}")
    print(f"  countries >180d stale: {len(stale)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
