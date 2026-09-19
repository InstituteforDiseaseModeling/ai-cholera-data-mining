#!/usr/bin/env python3
"""
Repair known data-integrity defects in cholera_data_ai.csv / metadata_ai.csv.

Every repair here is either (a) a mechanical application of a rule already
written down in CLAUDE.md, or (b) a correction of an unambiguous transcription
error. Anything requiring a judgement about what a source actually says is NOT
auto-applied - it is written to data/{ISO}/attribution_review.csv for an agent
or a human to resolve against the source.

Repairs applied
---------------
1. source_label_normalisation
   Rows whose `source` is a sub-label of the metadata entry their
   `source_index` correctly points at (e.g. 12 Kenya rows labelled
   "Kenya <County> County 2015 Outbreak" all citing metadata Index 19,
   "Kenya County Situation Report June 2015"). The index is right; only the
   free-text label drifted. The original label is preserved in
   processing_notes so nothing is lost.

2. presence_row_quarantine
   Rows with no deaths / sCh / cCh at all. CLAUDE.md prohibits these outright.
   They still carry real information ("cholera was present in Uige in 2018"),
   so rather than deleting them they move to cholera_presence_ai.csv.

   NOTE: an earlier version of this docstring claimed these rows were being
   zero-filled into false negatives by the weekly builder. That is NOT true of
   the current builder - py/build_weekly_timeseries.py sets has_count=False for
   a blank sCh and skips those rows explicitly. The real justification is
   narrower: CLAUDE.md prohibits rows with no case value, and coverage analysis
   already discards them as non-informative, so inside cholera_data_ai.csv they
   are dead weight that still reads as data. In cholera_presence_ai.csv the same
   evidence becomes usable for gap classification.

3. multiyear_downweight / high_cfr_downweight
   CLAUDE.md caps multi-year aggregates and high-CFR rows at
   confidence_weight <= 0.7. Applied mechanically.

4. date_transcription_fix
   Explicitly enumerated, individually justified date corrections.

5. duplicate_merge
   Identical (location, period, counts) rows from two sources are collapsed to
   one, with the second source recorded in processing_notes as cross-validation
   rather than discarded.

Usage:
    python py/repair_data_integrity.py --dry-run     # show what would change
    python py/repair_data_integrity.py --apply       # write changes + backups
"""

import argparse
import csv
import json
import shutil
from collections import defaultdict
from datetime import datetime, date
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

MULTIYEAR_MAX_DAYS = 760
MAX_CONF_MULTIYEAR = 0.7
MAX_CONF_HIGH_CFR = 0.7
CFR_HIGH = 15.0
CFR_SMALL_DENOM = 25

PRESENCE_COLUMNS = [
    "Location", "TL", "TR", "evidence", "source_index", "source",
    "confidence_weight", "processing_notes", "source_database", "moved_from_row",
]

# --------------------------------------------------------------------------
# (iso, source_index) pairs where the index is verified correct and the row
# label is merely a narrower sub-label of the cited source. Auto-normalisable.
#
# Pairs NOT listed here are left alone and reported for review - including
# cases where the cited source cannot plausibly support the row (e.g. AGO
# index 31 is a 2023 multi-country situation report cited by rows dated 2008
# and 2010, and KEN index 16 is a Homa Bay report cited by a Migori row).
# Silently rewriting those labels would launder a bad citation into an
# apparently valid one.
# --------------------------------------------------------------------------
SUBLABEL_OK = {
    ("AGO", "7"),   # 1974 row vs source dated exactly 1974-01-01..1974-12-31
    ("AGO", "9"),   # 1977 row vs source dated exactly 1977-01-01..1977-12-31
    ("AGO", "16"),  # Soyo/Zaire 2012 row vs a Sitata report naming Soyo, Zaire Province
    ("ETH", "2"),   # 2015-2022 spatiotemporal study; rows inside that window
    ("AGO", "10"),  # per-year labels under "WHO Global Health Data - Angola 1989-1996"
    ("BFA", "11"),  # accent/truncation drift on the same Plateforme Cholera factsheet
    ("KEN", "18"),  # per-county labels under "Trans Nzoia and West Pokot Counties 2015-2017"
    ("KEN", "19"),  # per-county labels under "Kenya County Situation Report June 2015"
    ("KEN", "20"),  # per-region labels under "Kenya Regional Molecular Epidemiology 2009-2010"
    ("KEN", "21"),  # per-camp labels under "Dadaab Refugee Camp Detailed Outbreak 2015-2017"
    # ("ETH", "12") was allowlisted and has been REMOVED. Metadata index 12 is
    # an OCHA flash update covering 8-20 June 2023, but the row citing it covers
    # all of 2023 with 30,000 cases. A June flash update cannot substantiate a
    # full-year total, so "normalising" the label produced a precisely wrong
    # citation from a merely vague one. It now goes to attribution_review.csv.
    ("ETH", "13"),  # paraphrase of "Retrospective Analysis of Cholera AWD Outbreaks in Ethiopia"
}

# --------------------------------------------------------------------------
# Individually justified date corrections.
#
# Keyed on a CONTENT signature (iso, Location, source_index, current TL, current
# TR), never a row number. Row numbers are not stable across passes: --apply
# rewrites the file shorter, so a literal ("SOM", 17) key silently points at a
# different row on the next run and "fixes" it with an authoritative-looking
# audit trail. Matching on content makes a re-run a no-op once applied.
# --------------------------------------------------------------------------
DATE_FIXES = [
    {
        "iso": "SOM", "location": "AFR::SOM", "source_index": "16",
        "match_tl": "1997-11-30", "match_tr": "1997-04-15",
        "set_tl": "1996-11-30", "set_tr": "1997-04-15",
        "why": ("The cited WHO Disease Outbreak News (URL slug 1997_04_15a-en) "
                "was PUBLISHED 1997-04-15, which is also this row's "
                "reporting_date, so TR was already correct. The impossible "
                "value is TL: WHO's own text says 'since the first case on 30 "
                "November 1997' in a document issued five months earlier. The "
                "9 May 1997 follow-up DON reports 4,437 cases for the same wave "
                "'since the end of November 1997 to 7 May 1997', which only "
                "parses with a November 1996 onset. Period corrected to "
                "1996-11-30..1997-04-15."),
    },
]


# Geography conflict check.
#
# An earlier version treated any capitalised word in a source title as a place
# name, so "Spatiotemporal dynamics of cholera epidemics in Ethiopia" read as a
# location conflict against an Afar row. It now consults the real ADM1 list from
# reference/country_profiles.json, and only fires when the title names an actual
# administrative unit of that country which the row's Location does not contain.
_PROFILES = None


def _adm1_units(iso):
    global _PROFILES
    if _PROFILES is None:
        pth = ROOT / "reference" / "country_profiles.json"
        _PROFILES = json.loads(pth.read_text())["countries"] if pth.exists() else {}
    p = _PROFILES.get(iso, {})
    units = list(p.get("adm1", []))
    for lst in (p.get("adm1_legacy") or {}).values():
        units.extend(lst)
    return [u for u in units if len(u) > 3]


def _geo_conflict(iso, location, source_title):
    loc = location.lower().replace("_", " ")
    title = source_title.lower()
    named = [u for u in _adm1_units(iso) if u.lower() in title]
    if not named:
        return None
    if loc.count("::") >= 2 and not any(u.lower() in loc for u in named):
        return (f"source title names {named[:3]}, which does not match the row's "
                f"Location {location!r}")
    return None


def _parse_range(text):
    """Parse a metadata Date_Range into (start, end, granularity)."""
    import re as _re
    t = (text or "").strip()
    m = _re.match(r"^(\d{4})-(\d{2})-(\d{2})\s*(?:to|-|..)\s*(\d{4})-(\d{2})-(\d{2})$", t)
    if m:
        a = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        b = date(int(m.group(4)), int(m.group(5)), int(m.group(6)))
        return a, b, "day"
    m = _re.match(r"^(\d{4})\s*[-\u2013]\s*(\d{4})$", t)
    if m:
        return date(int(m.group(1)), 1, 1), date(int(m.group(2)), 12, 31), "year"
    m = _re.match(r"^(\d{4})$", t)
    if m:
        y = int(m.group(1))
        return date(y, 1, 1), date(y, 12, 31), "year"
    return None, None, None


def can_normalize(iso, row, meta_entry):
    """(ok, reason) - may this row's label be rewritten to the cited source's name?

    Two things must hold. The row's period must fall inside the source's
    documented Date_Range, which is what rules out AGO rows dated 2008/2010
    citing a situation report covering 2025. And the source title must not name
    a different place than the row, which is what rules out a Migori row citing
    a Homa Bay report. A year-granular Date_Range cannot validate a full-year
    total against a source whose title carries a specific date.
    """
    tl, tr = d(row.get("TL")), d(row.get("TR"))
    rs, re_, gran = _parse_range(meta_entry.get("Date_Range", ""))
    title = (meta_entry.get("Source") or "").strip()

    if rs and tl and tr:
        if tl < rs or tr > re_:
            return False, (f"row period {tl}..{tr} falls outside the cited source's "
                           f"Date_Range {rs}..{re_}")
    elif rs is None:
        return False, f"cited source has an unparseable Date_Range {meta_entry.get('Date_Range')!r}"

    import re as _re
    if gran == "year" and tl and tr and (tr - tl).days > 300 and \
            _re.search(r"\b\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)",
                       title, _re.I):
        return False, ("cited source is dated to a single day but this row covers a "
                       "full year; a dated bulletin cannot substantiate an annual total")

    g = _geo_conflict(iso, row.get("Location", ""), title)
    if g:
        return False, g
    return True, ""


def load(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rdr = csv.DictReader(fh)
        return list(rdr), list(rdr.fieldnames or [])


def num(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def d(s):
    s = (s or "").strip()
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def repair_country(iso, changes, apply):
    cdir = DATA / iso
    dpath, mpath = cdir / "cholera_data_ai.csv", cdir / "metadata_ai.csv"
    if not dpath.exists():
        return

    rows, fields = load(dpath)
    if not rows:
        return
    meta_rows, _ = load(mpath) if mpath.exists() else ([], [])
    meta = {(m.get("Index") or "").strip(): (m.get("Source") or "").strip() for m in meta_rows}
    meta_rows_by_idx = {(m.get("Index") or "").strip(): m for m in meta_rows}

    # Track this country's changes separately: the caller's `changes` list is
    # global, so using it to decide whether to rewrite would rewrite all 40
    # files (and back them all up) as soon as any one country changed.
    local = []

    def log(kind, row, detail):
        entry = {"iso": iso, "kind": kind, "row": row, "detail": detail}
        changes.append(entry)
        local.append(entry)

    keep, presence, review = [], [], []
    seen = {}

    for i, r in enumerate(rows, start=2):
        loc = (r.get("Location") or "").strip()
        dd, ss, cc = num(r.get("deaths")), num(r.get("sCh")), num(r.get("cCh"))
        cw = num(r.get("confidence_weight"))
        si = (r.get("source_index") or "").strip()
        src = (r.get("source") or "").strip()
        tl, tr = d(r.get("TL")), d(r.get("TR"))

        # -- 4. date transcription fixes -------------------------------------
        for fix in DATE_FIXES:
            if (fix["iso"] != iso or fix["location"] != loc
                    or fix["source_index"] != si
                    or (r.get("TL") or "").strip() != fix["match_tl"]
                    or (r.get("TR") or "").strip() != fix["match_tr"]):
                continue
            r["TL"], r["TR"] = fix["set_tl"], fix["set_tr"]
            log("date_transcription_fix", i,
                f"TL {fix['match_tl']}->{fix['set_tl']}, "
                f"TR {fix['match_tr']}->{fix['set_tr']}. {fix['why']}")
            tl, tr = d(r.get("TL")), d(r.get("TR"))
            break

        # -- 1. source label normalisation -----------------------------------
        if si and si in meta and src and src != meta[si]:
            ok, why = can_normalize(iso, r, meta_rows_by_idx.get(si, {}))
            if (iso, si) in SUBLABEL_OK and ok:
                notes = r.get("processing_notes") or ""
                marker = f"Original row label: '{src}'."
                if marker not in notes:
                    r["processing_notes"] = (notes.rstrip() + " " + marker).strip()
                r["source"] = meta[si]
                log("source_label_normalisation", i,
                    f"source '{src}' -> '{meta[si]}' (index {si} verified; original label preserved)")
            else:
                # Identify the row by its stable Index + content, NOT by line
                # number: the data file is rewritten shorter in this same pass,
                # so a recorded line number is stale the moment it is written
                # and sends a reviewer to the wrong row or to no row at all.
                review.append({
                    "data_Index": (r.get("Index") or "").strip(),
                    "Location": loc, "TL": r.get("TL"), "TR": r.get("TR"),
                    "source_index": si, "row_source_label": src,
                    "metadata_source": meta.get(si, "<index missing from metadata>"),
                    "issue": (why or "row source label does not match the cited metadata Index"),
                    "action_required": ("verify against the source which entry actually "
                                        "supports this row, then correct source_index or "
                                        "source - do not simply relabel"),
                    "resolution": "",
                })
                log("attribution_flagged_for_review", i,
                    f"source '{src}' vs metadata[{si}] '{meta.get(si, '')}' - not auto-repaired")

        # -- 2. presence-only row quarantine ---------------------------------
        if dd is None and ss is None and cc is None:
            presence.append({
                "Location": loc, "TL": r.get("TL"), "TR": r.get("TR"),
                "evidence": "presence_confirmed_count_unknown",
                "source_index": si, "source": r.get("source"),
                "confidence_weight": r.get("confidence_weight"),
                "processing_notes": r.get("processing_notes"),
                "source_database": r.get("source_database"),
                "moved_from_row": i,
            })
            log("presence_row_quarantine", i,
                f"{loc} {r.get('TL')}..{r.get('TR')} has no deaths/sCh/cCh -> "
                f"cholera_presence_ai.csv (prohibited in the data file; non-informative "
                f"for coverage, but usable evidence for gap classification)")
            continue

        # -- 3a. multi-year aggregate downweight -----------------------------
        is_zero = (dd == 0 and ss == 0)
        if tl and tr and (tr - tl).days > MULTIYEAR_MAX_DAYS and not is_zero:
            if cw is not None and cw > MAX_CONF_MULTIYEAR:
                r["confidence_weight"] = f"{MAX_CONF_MULTIYEAR}"
                yrs = (tr - tl).days / 365.25
                log("multiyear_downweight", i,
                    f"{yrs:.1f}-year aggregate: confidence_weight {cw} -> {MAX_CONF_MULTIYEAR}")
                cw = MAX_CONF_MULTIYEAR

        # -- 3b. high-CFR downweight -----------------------------------------
        if dd is not None and ss is not None and ss >= CFR_SMALL_DENOM:
            implied = dd / ss * 100
            if implied > CFR_HIGH and cw is not None and cw > MAX_CONF_HIGH_CFR:
                r["confidence_weight"] = f"{MAX_CONF_HIGH_CFR}"
                log("high_cfr_downweight", i,
                    f"implied CFR {implied:.1f}% ({int(dd)}/{int(ss)}): "
                    f"confidence_weight {cw} -> {MAX_CONF_HIGH_CFR}")

        # -- 5. duplicate merge ----------------------------------------------
        key = (loc, r.get("TL"), r.get("TR"), r.get("sCh"), r.get("deaths"), r.get("cCh"))
        if key in seen:
            first_i, first_r = seen[key]
            note = first_r.get("processing_notes") or ""
            add = (f"Cross-validated by independent source '{src}' "
                   f"(index {si}), which reported identical figures.")
            if add not in note:
                first_r["processing_notes"] = (note.rstrip() + " " + add).strip()
            log("duplicate_merge", i,
                f"identical to row {first_i}; merged, second source recorded as "
                f"cross-validation rather than discarded")
            continue
        seen[key] = (i, r)
        keep.append(r)

    # ---- write ------------------------------------------------------------
    if not apply:
        return

    # Rows whose keys are not all in the header would make DictWriter raise
    # AFTER open(...,"w") has already truncated the file. Check first, write
    # second: a ragged row must abort this country, never destroy it.
    def safe_fields(rows, base):
        extra = set()
        for r in rows:
            extra |= {k for k in r if k not in base and k is not None}
        # `None` is DictReader's restkey for a row with more fields than the
        # header - a genuinely ragged row, which we surface rather than drop.
        ragged = [r for r in rows if None in r]
        return list(base) + sorted(extra), ragged

    def atomic_write(path, rows, base_fields):
        out_fields, ragged = safe_fields(rows, base_fields)
        if ragged:
            raise ValueError(
                f"{path.name} has {len(ragged)} ragged row(s) with more fields "
                f"than the header; refusing to rewrite the file. Fix the CSV first.")
        if path.exists():
            shutil.copy2(path, path.parent / f".backup_{path.stem}_{stamp}.csv")
        tmp = path.with_suffix(".csv.tmp")
        with open(tmp, "w", newline="", encoding="utf-8") as fh:
            # lineterminator="\n" keeps LF files as LF. The default "\r\n"
            # silently converted 20 of 26 files to CRLF, which made git show
            # every line as changed and the real edits unreviewable.
            w = csv.DictWriter(fh, fieldnames=out_fields, lineterminator="\n")
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in out_fields})
        tmp.replace(path)

    # Only touch files this country actually changed.
    mutating = [c for c in local if c["kind"] != "attribution_flagged_for_review"]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S%f")

    # Write the quarantine file BEFORE shortening the data file, so a failure
    # here cannot leave a row deleted from one file and absent from the other.
    if presence:
        ppath = cdir / "cholera_presence_ai.csv"
        existing = []
        if ppath.exists():
            existing, _ = load(ppath)
        # Idempotency guard: never re-add a quarantined row that is already here.
        have = {(e.get("Location"), e.get("TL"), e.get("TR"), e.get("source_index"))
                for e in existing}
        fresh = [p for p in presence
                 if (p["Location"], p["TL"], p["TR"], p["source_index"]) not in have]
        # Union the schema with whatever columns a reviewer has added, rather
        # than silently dropping their work (or crashing mid-truncate).
        atomic_write(ppath, existing + fresh, PRESENCE_COLUMNS)

    if mutating:
        atomic_write(dpath, keep, fields)

    rpath = cdir / "attribution_review.csv"
    if review:
        # Preserve any `resolution` a reviewer has already filled in, matched on
        # the stable data Index rather than a line number.
        prior = {}
        if rpath.exists():
            for old in load(rpath)[0]:
                key = (old.get("data_Index"), old.get("source_index"))
                if old.get("resolution", "").strip():
                    prior[key] = old["resolution"]
        for rec in review:
            rec["resolution"] = prior.get((rec["data_Index"], rec["source_index"]), "")
        atomic_write(rpath, review, list(review[0]))
    elif rpath.exists():
        # Every flagged row for this country is gone (resolved or quarantined);
        # a stale review file sends reviewers after rows that no longer exist.
        rpath.rename(rpath.with_suffix(".csv.resolved"))
        log("attribution_review_cleared", 0,
            "no unresolved attribution issues remain; review file archived")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    ap.add_argument("countries", nargs="*")
    ap.add_argument("--log", metavar="PATH", help="write change log as JSON")
    args = ap.parse_args()

    mapping = json.loads((ROOT / "reference" / "country_mapping.json").read_text())["countries"]
    mosaic = sorted(k for k, v in mapping.items() if v.get("mosaic_framework"))
    targets = [c.upper() for c in args.countries] if args.countries else mosaic

    changes = []
    for iso in targets:
        repair_country(iso, changes, apply=args.apply)

    by_kind = defaultdict(list)
    for c in changes:
        by_kind[c["kind"]].append(c)

    mode = "APPLIED" if args.apply else "DRY RUN - no files written"
    print(f"=== repair_data_integrity: {mode} ===\n")
    for kind in sorted(by_kind):
        items = by_kind[kind]
        isos = sorted({c["iso"] for c in items})
        print(f"{kind}: {len(items)} row(s) across {len(isos)} countries ({' '.join(isos)})")
        for c in items[:4]:
            print(f"    {c['iso']} row {c['row']}: {c['detail'][:150]}")
        if len(items) > 4:
            print(f"    ... and {len(items) - 4} more")
        print()

    print(f"TOTAL: {len(changes)} change(s)")
    if args.log:
        Path(args.log).write_text(json.dumps(changes, indent=2))
        print(f"Wrote change log to {args.log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
