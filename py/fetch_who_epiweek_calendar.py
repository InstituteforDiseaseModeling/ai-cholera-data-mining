#!/usr/bin/env python3
"""Cache WHO's epi-week -> calendar-date mapping from its own dashboard service.

Why this exists
---------------
convert_who_to_workflow.py used to turn a WHO *week number* into ISO week N of
that year. WHO's epi-week numbering is not ISO week numbering. For 2026 they are
offset by one, so every 2026 WHO row landed a week early:

    WHO epiwk 17 -> date_wk 2026-04-27 -> ISO week 18   (cases 56)
    WHO epiwk 18 -> date_wk 2026-05-04 -> ISO week 19   (cases 860)

data/NGA/cholera_data_who.csv showed 855 at ISO W18 where the true value was 56.
Measured offset (ISO week - WHO epiwk): 2023 = 0, 2024 = 0, 2025 = 0, 2026 = +1,
uniform across every country checked (NGA, KEN, COD, MOZ), because date_wk is a
property of WHO's calendar and not of the country.

The upstream extract in ees-cholera-mapping carries only
country/year/week/cases_by_week/deaths_by_week - no date - so the dates cannot
be recovered from it. They can be read straight from the dashboard's own
FeatureServer, which is what this does. The result is committed so the converter
works offline and so the mapping is auditable rather than being re-derived
differently on each run.

Usage:
    python py/fetch_who_epiweek_calendar.py            # refresh the cache
    python py/fetch_who_epiweek_calendar.py --check    # verify, write nothing
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone, date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reference" / "who_epiweek_calendar.json"

SERVICE = ("https://services.arcgis.com/5T5nSi527N4F7luB/arcgis/rest/services/"
           "cholera_adm0_week/FeatureServer/0/query")
TIMEOUT = 60


def fetch():
    """Return {(epiyr, epiwk): 'YYYY-MM-DD'} - the Monday WHO assigns to the week."""
    # Page over the real records rather than asking for distinct values.
    # returnDistinctValues collapses every (epiyr, epiwk, date_wk) triple to a
    # single row, so a week carrying two different dates upstream comes back as
    # a 1-1 tie and the "most common" reading becomes arbitrary. With the actual
    # records the correct date dominates by hundreds of rows to a handful.
    seen, offset, page = {}, 0, 2000
    while True:
        params = {
            "where": "epiwk IS NOT NULL AND date_wk IS NOT NULL",
            "outFields": "epiyr,epiwk,date_wk",
            "returnGeometry": "false",
            "resultOffset": str(offset),
            "resultRecordCount": str(page),
            "orderByFields": "epiyr,epiwk",
            "f": "json",
        }
        url = SERVICE + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
            payload = json.loads(r.read().decode())
        if "error" in payload:
            raise RuntimeError(f"service error: {payload['error']}")
        feats = payload.get("features", [])
        for f in feats:
            a = f["attributes"]
            yr, wk, dw = a.get("epiyr"), a.get("epiwk"), a.get("date_wk")
            if yr is None or wk is None or not isinstance(dw, (int, float)):
                continue
            d = datetime.fromtimestamp(dw / 1000, tz=timezone.utc).date()
            monday = d - timedelta(days=d.weekday())
            key = f"{int(yr)}-{int(wk):02d}"
            seen.setdefault(key, Counter())[monday.isoformat()] += 1
        offset += len(feats)
        if not payload.get("exceededTransferLimit") or not feats:
            break
    print(f"  read {offset} records from the service")

    cal, disputed = {}, []
    for key, counts in seen.items():
        best, n = counts.most_common(1)[0]
        cal[key] = best
        if len(counts) > 1:
            total = sum(counts.values())
            disputed.append((key, dict(counts), f"{n}/{total}"))
    if disputed:
        print(f"  note: {len(disputed)} epi-week(s) had inconsistent date_wk "
              f"values upstream; took the most common after normalising to the "
              f"week's Monday")
        weak = [d for d in disputed if int(d[2].split('/')[0]) * 2 <= int(d[2].split('/')[1])]
        for key, counts, margin in sorted(disputed)[:5]:
            print(f"    {key}: {counts}  (chose {margin})")
        if weak:
            print(f"    WARNING: {len(weak)} week(s) had no clear majority: "
                  f"{[d[0] for d in weak][:8]}")
    return cal


def offsets(cal):
    """ISO week minus WHO epiwk, per year - the thing that was wrong."""
    out = {}
    for key, ds in cal.items():
        yr, wk = key.split("-")
        iso_wk = date.fromisoformat(ds).isocalendar()[1]
        diff = iso_wk - int(wk)
        # ignore the year-boundary wrap (week 52/53 -> ISO week 1)
        if abs(diff) > 40:
            continue
        out.setdefault(int(yr), {}).setdefault(diff, 0)
        out[int(yr)][diff] += 1
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="compare against the cached file, write nothing")
    a = ap.parse_args()

    try:
        cal = fetch()
    except Exception as e:                                  # noqa: BLE001
        print(f"FAILED to reach the WHO service: {e}", file=sys.stderr)
        return 2
    if not cal:
        print("service returned no usable rows", file=sys.stderr)
        return 2

    print(f"fetched {len(cal)} epi-week entries")
    for yr, counts in sorted(offsets(cal).items()):
        note = "  <- WHO week N is ISO week N+1" if counts.get(1) else ""
        print(f"  {yr}: ISO-week minus epiwk -> {counts}{note}")

    payload = {
        "description": "WHO epidemiological week -> week-start date, read from "
                       "the date_wk field of WHO's cholera_adm0_week "
                       "FeatureServer. WHO epi-weeks are NOT ISO weeks; in 2026 "
                       "they are offset by one.",
        "source": SERVICE,
        "fetched_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "weeks": dict(sorted(cal.items())),
    }

    if a.check:
        if not OUT.exists():
            print(f"no cache at {OUT.relative_to(ROOT)}")
            return 1
        old = json.loads(OUT.read_text()).get("weeks", {})
        diff = {k: (old.get(k), v) for k, v in cal.items() if old.get(k) != v}
        gone = sorted(set(old) - set(cal))
        print(f"\ncached {len(old)} entries; {len(diff)} differ, {len(gone)} missing upstream")
        for k, (o, n) in list(diff.items())[:10]:
            print(f"  {k}: cached {o} -> service {n}")
        return 1 if diff else 0

    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"\nWrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
