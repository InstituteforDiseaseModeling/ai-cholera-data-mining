#!/usr/bin/env python3
"""
Checks for the district (ADM2) weekly series and its reference tables.
Exits non-zero on any ERROR.

  reference/subnational/adm2_units.csv     current districts, each under a current province
  reference/subnational/adm2_aliases.csv   every (province, raw district) in the data -> district
  data/{ISO}/cholera_adm2_weekly_{ISO}.csv built by py/build_district_weekly.py

Usage: python py/validate_district_series.py [ISO ...]
"""

import csv
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_district_weekly as bdw  # noqa: E402
import build_province_weekly as bpw  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
METHODS = {"observed", "documented_zero", "inferred_zero"}
EVIDENCE = {"direct", "rollup", "rollup_partial", "area", "linelist"}
errors, warns = [], []


def main():
    units, by_prov = bdw.load_units(bdw.SUB_DIR / "adm2_units.csv")
    bdw.SLOT_TABLE[:] = bdw.load_slot_districts(bdw.SUB_DIR / "adm2_slot_districts.csv")
    al1 = bpw.load_aliases(bdw.SUB_DIR / "adm1_aliases.csv")
    al2 = bdw.load_aliases(bdw.SUB_DIR / "adm2_aliases.csv")
    adm1 = bpw.load_units(bdw.SUB_DIR / "adm1_units.csv")
    targets = [a.upper() for a in sys.argv[1:]] or sorted(units)

    for iso in targets:
        if iso in bdw.EXCLUDE:
            if (BASE / "data" / iso / f"cholera_adm2_weekly_{iso}.csv").exists():
                errors.append(f"{iso}: district series exists for an excluded country")
            continue
        codes = Counter(u["adm2_code"] for u in units[iso].values() if u["adm2_code"])
        for c, n in codes.items():
            if n > 1:
                errors.append(f"{iso}: adm2_code {c} used {n} times")
        for k, u in units[iso].items():
            if u["adm1_name"] not in adm1.get(iso, {}):
                errors.append(f"{iso}: district {u['adm2_name']!r} has parent {u['adm1_name']!r}, "
                              f"not a current province")
            if not re.fullmatch(r"[A-Za-z0-9 '\-().,/]+", u["adm2_name"]):
                errors.append(f"{iso}: district name not ASCII-standard: {u['adm2_name']!r}")

    for (iso, prov, raw, child), rows in al2.items():
        if iso not in targets:
            continue
        for a in rows:
            if a["status"] not in bpw.STATUSES:
                errors.append(f"{iso}: alias {prov}/{raw}/{child} has invalid status {a['status']!r}")
            elif a["status"] in bpw.ASSIGNING | bpw.PART:
                if not bdw.unit_for(units, iso, a["adm2_name"], prov):
                    errors.append(f"{iso}: alias {prov}/{raw}/{child} -> {a['adm2_name']!r} "
                                  f"not a (unique) current district")
            elif a["adm2_name"]:
                errors.append(f"{iso}: alias {prov}/{raw} status {a['status']} must not name a district")
        if len(rows) > 1:
            spans = sorted((r["_from"], r["_to"]) for r in rows)
            for (a0, a1), (b0, b1) in zip(spans, spans[1:]):
                if b0 <= a1:
                    errors.append(f"{iso}: alias {prov}/{raw}/{child} eras overlap")

    # every district string in the data has an alias row
    for iso in targets:
        if iso in bdw.EXCLUDE or iso not in units:
            continue
        missing = set()
        for src in ("jhu", "jhu_archive", "who", "ai"):
            f = BASE / "data" / iso / f"cholera_data_{src}.csv"
            if not f.exists():
                continue
            for r in csv.DictReader(open(f, newline="", encoding="utf-8")):
                p = r.get("Location", "").strip().split("::")
                if len(p) < 3 or p[1] != iso:
                    continue
                try:
                    tl = date.fromisoformat(r["TL"])
                except ValueError:
                    continue
                prov, plvl, st, _ = bpw.resolve(al1, iso, p, tl)
                raw, _ci, single = bdw.district_of(p, prov, plvl, iso, al2, by_prov, tl)
                if raw is None and len(p) == 3 and plvl == "part" and iso in ("UGA", "MWI"):
                    missing.add((prov, p[2]))   # a district in the slot with no alias
                elif raw and not single and not (al2.get((iso, prov or "", raw, ""))
                                                 or al2.get((iso, "", raw, ""))):
                    missing.add((prov, raw))
        if missing:
            errors.append(f"{iso}: {len(missing)} (province, district) pairs have no alias row, "
                          f"e.g. {sorted(missing, key=str)[:4]}")

    for iso in targets:
        p = BASE / "data" / iso / f"cholera_adm2_weekly_{iso}.csv"
        if iso in bdw.EXCLUDE or not p.exists():
            continue
        keys = Counter()
        for r in csv.DictReader(open(p, newline="", encoding="utf-8")):
            keys[(r["adm1_name"], r["adm2_name"], r["year"], r["iso_week"])] += 1
            if r["adm1_name"] + bdw.SEP + r["adm2_name"] not in units[iso]:
                errors.append(f"{iso}: series unit {r['adm1_name']}/{r['adm2_name']} not in adm2_units.csv")
            m = r["disaggregation_method"]
            if m not in METHODS and not m.startswith("fourier_"):
                errors.append(f"{iso}: invalid method {m!r}")
            if r["evidence"] not in EVIDENCE:
                errors.append(f"{iso}: invalid evidence {r['evidence']!r}")
            if r["evidence"] == "area" and r["sCh"] and float(r["sCh"]) != 0:
                errors.append(f"{iso}: area evidence on a non-zero week ({r['adm2_name']} {r['week_start']})")
            mon = date.fromisoformat(r["week_start"])
            if mon.isocalendar()[:2] != (int(r["year"]), int(r["iso_week"])) or mon.weekday() != 0:
                errors.append(f"{iso}: week_start {r['week_start']} disagrees with year/week")
            s = float(r["sCh"]) if r["sCh"] else None
            if s is None or s < 0:
                errors.append(f"{iso}: bad sCh {r['sCh']!r}")
        dups = [k for k, n in keys.items() if n > 1]
        if dups:
            errors.append(f"{iso}: {len(dups)} duplicate district-weeks, e.g. {dups[:2]}")
        rec = BASE / "data" / iso / f"cholera_adm2_reconciliation_{iso}.csv"
        if rec.exists():
            over = sum(1 for r in csv.DictReader(open(rec, newline="", encoding="utf-8"))
                       if r["province_method"] == "observed" and r["province_sCh"]
                       and float(r["province_sCh"]) > 0
                       and float(r["districts_sCh"]) > 2 * float(r["province_sCh"]) + 10)
            if over:
                warns.append(f"{iso}: {over} observed province-weeks where districts sum to > 2x the province")

    for w in warns[:40]:
        print("WARN ", w)
    for e in errors[:200]:
        print("ERROR", e)
    print(f"\n{len(errors)} errors, {len(warns)} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
