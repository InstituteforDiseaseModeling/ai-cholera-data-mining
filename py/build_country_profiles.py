#!/usr/bin/env python3
"""
Build ./reference/country_profiles.json from the part A/B source dicts.

This file replaces the workflow-orchestrator's phantom "internal database of
all 40 MOSAIC framework countries". Before this existed, every per-country
search parameter (provinces, neighbours, languages, ministry sites) came from
model recall and was unverifiable and silently variable between runs.

Usage:
    python py/build_country_profiles.py            # build + validate
    python py/build_country_profiles.py --check    # validate only, non-zero exit on error
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from country_profiles_data_a import PROFILES_A  # noqa: E402
from country_profiles_data_b import PROFILES_B  # noqa: E402

ROOT = Path(__file__).parent.parent
MAPPING = ROOT / "reference" / "country_mapping.json"
OUT = ROOT / "reference" / "country_profiles.json"

REQUIRED_FIELDS = [
    "name", "iso2", "subregion", "adm1", "major_cities",
    "neighbors", "search_languages", "disease_terms", "health_domains", "season",
]

# Non-MOSAIC neighbours that legitimately appear in `neighbors` for regional
# context queries. Agents must NOT collect data for these - see the scope
# restriction in CLAUDE.md - but may search them for cross-border evidence.
OUT_OF_SCOPE_NEIGHBORS = {"DJI", "SDN", "DZA", "LBY", "LSO", "EGY", "MAR", "TUN", "ESH"}


def load_mosaic_isos():
    mapping = json.loads(MAPPING.read_text())["countries"]
    return sorted(k for k, v in mapping.items() if v.get("mosaic_framework")), mapping


def validate(profiles, mosaic_isos, mapping):
    errors, warnings = [], []
    have = set(profiles)
    want = set(mosaic_isos)

    for iso in sorted(want - have):
        errors.append(f"{iso}: MOSAIC country missing from profiles")
    for iso in sorted(have - want):
        errors.append(f"{iso}: profile present but not a MOSAIC framework country")

    all_iso3 = set(mapping)
    for iso, p in sorted(profiles.items()):
        for f in REQUIRED_FIELDS:
            if f not in p:
                errors.append(f"{iso}: missing field '{f}'")
            elif isinstance(p[f], list) and not p[f]:
                errors.append(f"{iso}: field '{f}' is empty")
            elif isinstance(p[f], str) and not p[f].strip():
                errors.append(f"{iso}: field '{f}' is blank")

        if p.get("name") and mapping.get(iso, {}).get("name"):
            # Names may differ in accents/short form; only flag wholly different names.
            a = p["name"].lower().replace("'", "")
            b = mapping[iso]["name"].lower().replace("'", "")
            if not (a[:4] in b or b[:4] in a):
                warnings.append(f"{iso}: profile name '{p['name']}' vs mapping '{mapping[iso]['name']}'")

        if len(p.get("iso2", "")) != 2:
            errors.append(f"{iso}: iso2 must be 2 characters, got {p.get('iso2')!r}")

        for n in p.get("neighbors", []):
            if n not in all_iso3 and n not in OUT_OF_SCOPE_NEIGHBORS:
                errors.append(f"{iso}: neighbor {n!r} is not a known ISO3 code")
            if n == iso:
                errors.append(f"{iso}: lists itself as a neighbor")

        if len(set(p.get("adm1", []))) != len(p.get("adm1", [])):
            errors.append(f"{iso}: duplicate entries in adm1")

        # adm1_legacy is optional: superseded administrative names, keyed by the
        # era they applied to. The baseline record starts in 1970, so for any
        # country that has redrawn its map (AGO 2024, BFA 2025, BDI 2025,
        # ETH 2023, MLI 2023) most historical reporting uses names that are not
        # in the current adm1 list at all.
        legacy = p.get("adm1_legacy") or {}
        if legacy and not isinstance(legacy, dict):
            errors.append(f"{iso}: adm1_legacy must be a dict keyed by era")
        for era, units in legacy.items():
            if not isinstance(units, list) or not units:
                errors.append(f"{iso}: adm1_legacy['{era}'] must be a non-empty list")

    # Neighbour symmetry: if A borders B and both are in scope, B should border A.
    for iso, p in sorted(profiles.items()):
        for n in p.get("neighbors", []):
            if n in profiles and iso not in profiles[n].get("neighbors", []):
                warnings.append(f"neighbor asymmetry: {iso} lists {n}, but {n} does not list {iso}")

    return errors, warnings


def main():
    check_only = "--check" in sys.argv
    profiles = {**PROFILES_A, **PROFILES_B}
    mosaic_isos, mapping = load_mosaic_isos()

    overlap = set(PROFILES_A) & set(PROFILES_B)
    if overlap:
        print(f"FAIL: ISO codes defined in both part A and part B: {sorted(overlap)}")
        return 1

    errors, warnings = validate(profiles, mosaic_isos, mapping)

    for w in warnings:
        print(f"  WARN  {w}")
    for e in errors:
        print(f"  ERROR {e}")

    if errors:
        print(f"\nFAIL: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1

    n_adm1 = sum(len(p["adm1"]) for p in profiles.values())
    n_legacy = sum(len(u) for p in profiles.values()
                   for u in (p.get("adm1_legacy") or {}).values())
    n_cities = sum(len(p["major_cities"]) for p in profiles.values())
    n_domains = sum(len(p["health_domains"]) for p in profiles.values())
    langs = sorted({lg for p in profiles.values() for lg in p["search_languages"]})

    payload = {
        "metadata": {
            "description": "Per-country search-targeting profiles for MOSAIC AI cholera data collection",
            "generated_by": "py/build_country_profiles.py",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "countries": len(profiles),
            "adm1_units": n_adm1,
            "adm1_legacy_units": n_legacy,
            "major_cities": n_cities,
            "health_domains": n_domains,
            "search_languages": langs,
            "health_domains_verified": False,
            "notes": (
                "health_domains are candidate URLs and are NOT verified by this "
                "builder. Run py/verify_country_profiles.py to URL-check them and "
                "write reference/country_profiles_domain_status.json. "
                "neighbors may include non-MOSAIC countries for regional-context "
                "queries only - data collection remains restricted to the 40 "
                "MOSAIC framework countries."
            ),
        },
        "countries": {k: profiles[k] for k in sorted(profiles)},
    }

    if check_only:
        print(f"OK: {len(profiles)} countries valid ({len(warnings)} warning(s))")
        return 0

    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    print(f"  countries        : {len(profiles)}")
    print(f"  ADM1 units       : {n_adm1}")
    print(f"  legacy ADM1 units: {n_legacy}")
    print(f"  major cities     : {n_cities}")
    print(f"  health domains   : {n_domains} (unverified)")
    print(f"  search languages : {' '.join(langs)}")
    print(f"  warnings         : {len(warnings)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
