#!/usr/bin/env python3
"""
MOSAIC AI cholera data - dataset validator.

Replaces the previous stub, which was hardcoded to ``data/AGO/`` and therefore
only ever validated Angola regardless of the country being audited.

Runs the CLAUDE.md validation rules as executable checks across every MOSAIC
country (or a subset), classifies findings by severity, and exits non-zero when
any ERROR-level finding is present so it can gate a workflow.

Usage:
    python py/validate_quality.py                  # all 40 MOSAIC countries
    python py/validate_quality.py ETH KEN          # specific countries
    python py/validate_quality.py --json out.json  # machine-readable report
    python py/validate_quality.py --quiet          # summary only
    python py/validate_quality.py --warn-as-error  # strict gate

Severities:
    ERROR  Violates a MANDATORY rule in CLAUDE.md. Blocks completion.
    WARN   Outside expected bounds or missing recommended documentation.
    INFO   Advisory context; never blocks.
"""

import argparse
import csv
import json
import math
import re
import sys
import traceback
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
MAPPING = ROOT / "reference" / "country_mapping.json"

DATA_COLUMNS = [
    "Index", "Location", "TL", "TR", "deaths", "sCh", "cCh", "CFR",
    "reporting_date", "source_index", "source", "confidence_weight",
    "processing_notes", "source_database",
]
META_COLUMNS = [
    "Index", "Source", "URL", "Description", "Date_Range", "Data_Type", "Status",
    "Reliability_Level", "Validation_Status", "Search_Technique",
    "Language_Original", "Citation_Depth", "Cross_References",
    "Discovery_Method", "source_database",
]

VALID_SOURCE_DB = {"JHU", "WHO", "AI"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LOCATION_RE = re.compile(r"^AFR::[A-Z]{3}(::[^:]+)*$")

# Location segments that are not geographic administrative units. CLAUDE.md
# prohibits these outright - they describe programmes or demographics, not a
# place where people contracted cholera.
# Matched against "::"-delimited Location SEGMENTS, not the whole string, and
# anchored at segment start. Substring matching over the whole Location made
# "age_" fire on "Serowe_Village_East" ("vill-age_") and would have blocked
# legitimate admin units named *_Village_*, *Heritage_*, *Portage_*.
PROHIBITED_LOCATION_TOKENS = [
    "vaccination", "ocv_campaign", "ocv campaign", "ocv", "oral_cholera_vaccine",
    "immunization", "immunisation", "training", "health_worker", "demographics",
    "age_group", "age_band", "laboratory", "surveillance", "population",
    "capacity", "strategy", "wash", "funding", "coverage", "beneficiaries",
    "doses", "treatment_center", "treatment_centre", "ctc_beds", "attack_rate",
]

# Epidemiological bounds from CLAUDE.md Stage 2.
#
# CLAUDE.md distinguishes "flag for manual review" from "automatically reject".
# High CFR is explicitly in the *flag* category ("Flag for manual review if CFR
# outside 0.5-10%"), and only CFR > 100% is in the *reject* category. Pre-ORS
# historical epidemics (1970s-80s West Africa) and remote conflict settings
# genuinely reached 20-30%, so a high CFR is not by itself an error. What IS an
# error is carrying a high CFR at high confidence: CLAUDE.md requires such rows
# to be downweighted and their context documented.
CFR_WARN_HIGH = 15.0        # flag for manual review above this
CFR_SMALL_DENOM = 25        # below this many cases a CFR is not informative
CFR_MAX_CONFIDENCE = 0.7    # max confidence_weight permitted above CFR_WARN_HIGH
MAX_OUTBREAK_DAYS = 760     # ~2 years + slack, per "1 week to 104 weeks"
MULTIYEAR_MAX_CONFIDENCE = 0.7  # CLAUDE.md: multi-year aggregates get <=0.7

# Evidence labels for zero rows. A zero backed by a WHO statement of "no cases
# reported" is epidemiologically different from a zero inferred from silence;
# the downstream weekly builder ranks them documented > inferred > assumed, so
# an unlabelled zero is indistinguishable from missing data.
ZERO_EVIDENCE_TYPES = ["Documented_Absence", "Inferred_Absence", "Surveillance_Gap"]
ZERO_EVIDENCE_RE = re.compile("|".join(ZERO_EVIDENCE_TYPES), re.I)


def today():
    return date.today()


def parse_date(s):
    s = (s or "").strip()
    if not DATE_RE.match(s):
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def to_num(s):
    s = (s or "").strip()
    if s == "":
        return None
    try:
        v = float(s)
    except (ValueError, TypeError):
        return "BAD"
    # nan/inf are floats and would otherwise survive every downstream guard and
    # then crash on int(v). A pandas round-trip with a non-default na_rep emits
    # them, so this is a reachable input, not a theoretical one.
    if not math.isfinite(v):
        return "BAD"
    return v


def to_index(s):
    """Parse a CSV index field. Returns int or None.

    str.isdigit() is True for characters int() rejects ('2', '1'), so gating
    on isdigit() and then calling int() crashes on a pasted footnote marker.
    """
    s = (s or "").strip()
    try:
        return int(s)
    except (ValueError, TypeError):
        return None


class Report:
    def __init__(self):
        self.findings = []

    def add(self, severity, iso, check, message, row=None):
        self.findings.append({
            "severity": severity, "iso": iso, "check": check,
            "message": message, "row": row,
        })

    def error(self, *a, **k):
        self.add("ERROR", *a, **k)

    def warn(self, *a, **k):
        self.add("WARN", *a, **k)

    def info(self, *a, **k):
        self.add("INFO", *a, **k)

    def counts(self):
        return Counter(f["severity"] for f in self.findings)


def read_csv(path):
    """Return (rows, error). Each row carries `_line`, its true physical line.

    Rows are tagged with csv's own line counter rather than an enumerate()
    index, so a field containing an embedded newline does not silently shift
    every subsequent row number in the report.
    """
    if not path.exists():
        return None, f"file not found: {path.relative_to(ROOT)}"
    try:
        raw = path.read_bytes()
    except Exception as e:  # noqa: BLE001
        return None, f"unreadable: {e}"
    if not raw.strip():
        return None, "file is empty (0 bytes). An empty file silently disables " \
                     "every check that depends on it"
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            rdr = csv.DictReader(fh)
            rows = []
            for r in rdr:
                r["_line"] = rdr.reader.line_num
                rows.append(r)
            fields = rdr.fieldnames
    except Exception as e:  # noqa: BLE001 - surface any parse failure verbatim
        return None, f"parse error: {e}"

    if not fields:
        return None, "file has no header row"

    # An unterminated quote makes csv swallow subsequent lines into one field.
    # Comparing parsed records against physical lines is the only cheap way to
    # notice that records were destroyed rather than merely malformed.
    physical = raw.count(b"\n")
    if raw and not raw.endswith(b"\n"):
        physical += 1
    embedded = sum((r.get("processing_notes") or "").count("\n") +
                   (r.get("Description") or "").count("\n") for r in rows)
    expected = len(rows) + 1 + embedded  # records + header + wrapped newlines
    if physical > expected:
        return rows, (f"CSV parsed {len(rows)} records from {physical} physical "
                      f"lines (expected ~{expected}); an unterminated quote has "
                      f"probably merged or destroyed records")
    return rows, None


def validate_country(iso, rep):
    cdir = DATA / iso
    data_path = cdir / "cholera_data_ai.csv"
    meta_path = cdir / "metadata_ai.csv"

    meta_rows, err = read_csv(meta_path)
    if err:
        rep.error(iso, "metadata_readable", err)
    # meta_rows is None only when the file could not yield records at all.
    # Previously this fell through to `if meta_rows:` and silently skipped every
    # dual-reference check, so a truncated metadata file turned validation OFF
    # and the country exited clean.
    meta_missing = not meta_rows
    meta_rows = meta_rows or []

    data_rows, err = read_csv(data_path)
    if err:
        rep.error(iso, "data_readable", err)
    if data_rows is None:
        return {"rows": 0, "sources": 0}

    if not data_rows:
        rep.error(iso, "data_empty",
                  "cholera_data_ai.csv has a header but no records; an empty "
                  "file passes every row-level check vacuously")

    # ---- metadata structure & index integrity -------------------------------
    meta_index = {}
    if meta_missing:
        rep.error(iso, "metadata_unusable",
                  "no usable metadata_ai.csv, so dual-reference integrity "
                  "cannot be checked at all; every source_index in the data "
                  "file is unverifiable")
    else:
        header = [k for k in meta_rows[0] if k != "_line"]
        missing_cols = [c for c in META_COLUMNS if c not in header]
        if missing_cols:
            rep.error(iso, "metadata_columns", f"missing columns: {missing_cols}")
        extra_cols = [c for c in header if c not in META_COLUMNS]
        if extra_cols:
            rep.warn(iso, "metadata_extra_columns",
                     f"unexpected columns {extra_cols}; CLAUDE.md requires "
                     f"approval for additional columns")

        seen_idx = set()
        for m in meta_rows:
            i = m["_line"]
            raw = (m.get("Index") or "").strip()
            if not raw:
                rep.error(iso, "metadata_index_blank", "metadata row has blank Index", row=i)
                continue
            n = to_index(raw)
            if n is None:
                rep.error(iso, "metadata_index_nonint",
                          f"Index {raw!r} is not an integer", row=i)
                continue
            if n in seen_idx:
                rep.error(iso, "metadata_index_duplicate",
                          f"Index {n} appears more than once", row=i)
            seen_idx.add(n)
            # Keyed on int, so '01' and '1' resolve to the same source rather
            # than producing a phantom orphan plus a phantom index gap.
            meta_index[n] = (m.get("Source") or "").strip()

            url = (m.get("URL") or "").strip()
            if not url:
                rep.warn(iso, "metadata_url_blank",
                         f"Index {n} ({m.get('Source','')[:40]}) has no URL", row=i)

            lvl = (m.get("Reliability_Level") or "").strip()
            if lvl and not re.search(r"Level\s*[1-4]", lvl):
                rep.warn(iso, "metadata_reliability_unparseable",
                         f"Index {n}: Reliability_Level {lvl!r} does not name a "
                         f"level 1-4, so confidence bands cannot be checked", row=i)

            sdb = (m.get("source_database") or "").strip()
            if sdb and sdb not in VALID_SOURCE_DB:
                rep.error(iso, "metadata_source_database",
                          f"Index {n}: source_database {sdb!r} not in {sorted(VALID_SOURCE_DB)}", row=i)

        if seen_idx:
            nums = sorted(seen_idx)
            gaps = [n for n in range(1, nums[-1] + 1) if n not in seen_idx]
            if gaps:
                rep.error(iso, "metadata_index_gaps",
                          f"Index sequence has holes: {gaps[:12]}"
                          f"{'...' if len(gaps) > 12 else ''}. CLAUDE.md: "
                          f"'No index numbers can be duplicated or missing'")

    # ---- data structure -----------------------------------------------------
    if data_rows:
        header = [k for k in data_rows[0] if k != "_line"]
        missing_cols = [c for c in DATA_COLUMNS if c not in header]
        if missing_cols:
            rep.error(iso, "data_columns", f"missing columns: {missing_cols}")
        extra_cols = [c for c in header if c not in DATA_COLUMNS]
        if extra_cols:
            rep.warn(iso, "data_extra_columns",
                     f"unexpected columns {extra_cols}; CLAUDE.md requires "
                     f"approval for additional columns")
        if header[:len(DATA_COLUMNS)] != DATA_COLUMNS and not missing_cols:
            rep.warn(iso, "data_column_order",
                     "column order differs from the specified order")

    seen_rows = {}
    used_sources = set()
    seen_data_idx = set()
    t = today()

    for r in data_rows:
        i = r["_line"]
        loc = (r.get("Location") or "").strip()
        notes_raw = r.get("processing_notes") or ""

        # -- the data file's own Index column ---------------------------------
        draw = (r.get("Index") or "").strip()
        if not draw:
            rep.error(iso, "data_index_blank", "data row has blank Index", row=i)
        else:
            dn = to_index(draw)
            if dn is None:
                rep.error(iso, "data_index_nonint",
                          f"Index {draw!r} is not an integer", row=i)
            elif dn in seen_data_idx:
                rep.error(iso, "data_index_duplicate",
                          f"Index {dn} appears more than once", row=i)
            else:
                seen_data_idx.add(dn)
        tl, tr = parse_date(r.get("TL")), parse_date(r.get("TR"))
        rd = parse_date(r.get("reporting_date"))

        # -- location ---------------------------------------------------------
        if not loc:
            rep.error(iso, "location_blank", "Location is blank", row=i)
        else:
            if not LOCATION_RE.match(loc):
                rep.error(iso, "location_format",
                          f"Location {loc!r} does not match AFR::ISO[::unit...]", row=i)
            parts = loc.split("::")
            if len(parts) >= 2 and parts[1] != iso:
                rep.error(iso, "location_iso_mismatch",
                          f"Location {loc!r} does not belong to {iso}", row=i)
            # Match per SEGMENT, anchored at segment start, so a token cannot
            # fire on a substring inside a legitimate place name.
            for seg in parts[2:]:
                segl = seg.strip().lower().replace(" ", "_")
                hit = next((tok for tok in PROHIBITED_LOCATION_TOKENS
                            if segl == tok or segl.startswith(tok + "_")
                            or segl.endswith("_" + tok)), None)
                if hit:
                    rep.error(iso, "location_prohibited",
                              f"Location {loc!r} has a non-geographic segment "
                              f"{seg!r} (matched {hit!r})", row=i)
                    break

        # -- dates ------------------------------------------------------------
        if tl is None:
            rep.error(iso, "TL_invalid", f"TL {r.get('TL')!r} is not YYYY-MM-DD", row=i)
        if tr is None:
            rep.error(iso, "TR_invalid", f"TR {r.get('TR')!r} is not YYYY-MM-DD", row=i)
        if tl and tr and tl > tr:
            rep.error(iso, "TL_after_TR", f"TL {tl} is after TR {tr}", row=i)
        if tr and tr > t:
            rep.error(iso, "TR_in_future", f"TR {tr} is in the future (today {t})", row=i)
        if tl and tl > t:
            rep.error(iso, "TL_in_future", f"TL {tl} is in the future (today {t})", row=i)
        if rd and tr and rd < tr:
            rep.warn(iso, "reporting_before_TR",
                     f"reporting_date {rd} precedes TR {tr}", row=i)
        if rd and rd > t:
            rep.error(iso, "reporting_in_future", f"reporting_date {rd} is in the future", row=i)
        if not (r.get("reporting_date") or "").strip():
            rep.warn(iso, "reporting_date_blank",
                     "reporting_date is blank; CLAUDE.md requires it and the "
                     "temporal-ordering rule cannot be checked without it", row=i)
        elif rd is None:
            rep.error(iso, "reporting_date_invalid",
                      f"reporting_date {r.get('reporting_date')!r} is not YYYY-MM-DD", row=i)
        if tl and tr and (tr - tl).days == 0:
            rep.warn(iso, "period_single_day",
                     f"period is a single day ({tl}); CLAUDE.md flags outbreak "
                     f"durations under two weeks for manual review", row=i)

        # -- counts -----------------------------------------------------------
        deaths, sch, cch = to_num(r.get("deaths")), to_num(r.get("sCh")), to_num(r.get("cCh"))
        for name, v in (("deaths", deaths), ("sCh", sch), ("cCh", cch)):
            if v == "BAD":
                rep.error(iso, f"{name}_nonnumeric", f"{name}={r.get(name)!r} is not numeric", row=i)
            elif isinstance(v, float):
                if v < 0:
                    rep.error(iso, f"{name}_negative", f"{name}={v} is negative", row=i)
                elif v != int(v):
                    rep.warn(iso, f"{name}_noninteger", f"{name}={v} is not an integer", row=i)

        num = lambda v: v if isinstance(v, float) else None  # noqa: E731
        d, s, c = num(deaths), num(sch), num(cch)

        # The `s > 0` guard used to suppress these exactly where they matter
        # most: deaths=500 with sCh=0 is both a mathematical impossibility and
        # the false-zero pattern the weekly builder misreads as a documented
        # absence, yet it passed silently.
        if d is not None and s is not None and d > s:
            rep.error(iso, "deaths_exceed_cases",
                      f"deaths={int(d)} > sCh={int(s)}"
                      + (" - a zero case count with deaths is both impossible "
                         "and reads downstream as a documented absence" if s == 0 else ""),
                      row=i)
        if c is not None and s is not None and c > s:
            rep.error(iso, "confirmed_exceed_suspected", f"cCh={int(c)} > sCh={int(s)}", row=i)
        if d is not None and s is None and c is not None and d > c:
            rep.error(iso, "deaths_exceed_confirmed",
                      f"deaths={int(d)} > cCh={int(c)} with no sCh recorded", row=i)

        if d is None and s is None and c is None:
            rep.error(iso, "no_quantitative_value",
                      "row has no deaths, sCh or cCh - CLAUDE.md prohibits rows "
                      "without a case value or documented zero. Such rows also risk "
                      "being zero-filled into false negatives downstream; move them "
                      "to cholera_presence_ai.csv", row=i)

        # A zero row: every count that IS present is 0, and at least one is
        # present. Requiring an explicit deaths=0 misclassified real rows -
        # e.g. a documented absence recorded as sCh=0 with deaths left blank
        # was treated as a non-zero multi-year aggregate and simultaneously
        # escaped the zero-row evidence checks.
        present = [v for v in (d, s, c) if v is not None]
        is_zero = bool(present) and all(v == 0 for v in present)

        # confidence_weight is needed by the period and CFR rules below.
        cw = to_num(r.get("confidence_weight"))
        if cw == "BAD":
            rep.error(iso, "confidence_nonnumeric",
                      f"confidence_weight={r.get('confidence_weight')!r} is not numeric", row=i)
            cw = None
        elif cw is None:
            rep.error(iso, "confidence_blank", "confidence_weight is blank", row=i)
        elif not (0.1 <= cw <= 1.0):
            rep.error(iso, "confidence_out_of_range",
                      f"confidence_weight={cw} outside 0.1-1.0", row=i)

        # -- multi-year aggregation ------------------------------------------
        # Multi-year ZERO rows are mandated by the Agent 3 spec ("create ONE entry
        # for entire multi-year periods"), so they are not flagged. Multi-year
        # rows carrying counts are aggregates and must be downweighted.
        if tl and tr and (tr - tl).days > MAX_OUTBREAK_DAYS and not is_zero:
            span_years = (tr - tl).days / 365.25
            if cw is not None and cw > MULTIYEAR_MAX_CONFIDENCE:
                # WARN, not ERROR. CLAUDE.md phrases this as "should receive
                # confidence_weight <=0.7", scoped to aggregated CFR entries -
                # a recommendation, not a rejection rule. Blocking on it made
                # the validator stricter than the spec it claims to encode.
                rep.warn(iso, "multiyear_confidence_high",
                         f"{span_years:.1f}-year aggregate ({tl}..{tr}) carries "
                         f"confidence_weight={cw}; CLAUDE.md recommends "
                         f"<={MULTIYEAR_MAX_CONFIDENCE} for multi-year aggregates", row=i)
            else:
                rep.warn(iso, "multiyear_aggregate",
                         f"counts span {span_years:.1f} years ({tl}..{tr}); verify the "
                         f"source really reports a period total and not a single year",
                         row=i)

        # -- CFR --------------------------------------------------------------
        cfr = to_num(r.get("CFR"))
        if cfr == "BAD":
            rep.error(iso, "CFR_nonnumeric", f"CFR={r.get('CFR')!r} is not numeric", row=i)
        elif isinstance(cfr, float):
            if not (0 <= cfr <= 100):
                rep.error(iso, "CFR_out_of_range", f"CFR={cfr} outside 0-100", row=i)
            if d is not None and s is not None and s > 0:
                expected = d / s * 100
                if abs(expected - cfr) > 0.6:
                    rep.warn(iso, "CFR_inconsistent",
                             f"CFR={cfr} but deaths/sCh implies {expected:.2f}", row=i)
        if d is not None and s is not None and s >= CFR_SMALL_DENOM:
            implied = d / s * 100
            # CLAUDE.md puts high CFR in the "flag for manual review" bucket and
            # auto-rejects only CFR > 100%, explicitly allowing ~20% in
            # humanitarian settings. Treating it as blocking invented a rule the
            # spec does not state - and one an agent could not satisfy, since
            # the error demanded "documented context" that the code never read.
            if implied > CFR_WARN_HIGH:
                documented = bool(re.search(
                    r"conflict|humanitarian|famine|displace|remote|no treatment|"
                    r"treatment access|pre-ORS|siege|refugee", notes_raw, re.I))
                msg = (f"implied CFR {implied:.1f}% ({int(d)}/{int(s)}) exceeds "
                       f"{CFR_WARN_HIGH}%; verify deaths and cases share a "
                       f"denominator and period")
                if cw is not None and cw > CFR_MAX_CONFIDENCE and not documented:
                    rep.warn(iso, "CFR_high_undocumented_at_high_confidence",
                             msg + f". confidence_weight={cw} with no humanitarian "
                                   f"or historical context in processing_notes - "
                                   f"downweight to <={CFR_MAX_CONFIDENCE} or document why", row=i)
                else:
                    rep.warn(iso, "CFR_high_flagged_for_review", msg, row=i)

        # -- dual-reference indexing -----------------------------------------
        si_raw = (r.get("source_index") or "").strip()
        si = to_index(si_raw)
        src = (r.get("source") or "").strip()
        if not si_raw:
            rep.error(iso, "source_index_blank", "source_index is blank", row=i)
        elif si is None:
            rep.error(iso, "source_index_nonint",
                      f"source_index {si_raw!r} is not an integer", row=i)
        elif not meta_missing and si not in meta_index:
            rep.error(iso, "source_index_orphan",
                      f"source_index {si} has no matching metadata Index", row=i)
        elif si is not None:
            used_sources.add(si)
            if src and meta_index.get(si) and src != meta_index[si]:
                rep.error(iso, "source_name_mismatch",
                          f"source {src!r} != metadata Index {si} Source "
                          f"{meta_index[si]!r}", row=i)
        if not src:
            rep.error(iso, "source_blank", "source is blank", row=i)

        # -- provenance -------------------------------------------------------
        sdb = (r.get("source_database") or "").strip()
        if sdb not in VALID_SOURCE_DB:
            rep.error(iso, "source_database_invalid",
                      f"source_database {sdb!r} not in {sorted(VALID_SOURCE_DB)}", row=i)

        # -- documentation ----------------------------------------------------
        notes = r.get("processing_notes") or ""
        if "Source states" not in notes and "Source confirms" not in notes:
            rep.warn(iso, "notes_missing_quote",
                     "processing_notes lacks the mandated \"Source states: '...'\" "
                     "quote supporting the interpretation", row=i)
        if is_zero:
            if not notes.strip():
                rep.error(iso, "zero_row_undocumented",
                          "zero-transmission row has empty processing_notes; evidence "
                          "type and surveillance status are mandatory", row=i)
            elif not ZERO_EVIDENCE_RE.search(notes):
                rep.warn(iso, "zero_row_no_evidence_type",
                         f"zero row lacks an evidence label ({'/'.join(ZERO_EVIDENCE_TYPES)}); "
                         f"without one, a documented absence cannot be distinguished "
                         f"from an unobserved gap downstream", row=i)

        # -- duplicates -------------------------------------------------------
        key = (loc, r.get("TL"), r.get("TR"), r.get("sCh"), r.get("deaths"), r.get("cCh"))
        if key in seen_rows:
            rep.error(iso, "duplicate_row",
                      f"duplicates row {seen_rows[key]} (same location, period and counts)", row=i)
        else:
            seen_rows[key] = i

    # ---- national vs subnational double-counting ---------------------------
    # Grouping on an exact (TL, TR) match only caught the trivial case. The real
    # double-counting risk is a provincial row nested inside a national period -
    # e.g. national 2017 full-year alongside provincial Mar-Jun 2017 - which an
    # exact-match key never sees. Group by overlap instead.
    nat, sub = [], []
    for r in data_rows:
        loc = (r.get("Location") or "").strip()
        if not loc.startswith(f"AFR::{iso}"):
            continue
        tl_, tr_ = parse_date(r.get("TL")), parse_date(r.get("TR"))
        if not tl_ or not tr_:
            continue
        (nat if loc.count("::") == 1 else sub).append((r["_line"], r, tl_, tr_))

    overlaps = defaultdict(lambda: {"nat": [], "sub": []})
    for ni, nr, ntl, ntr in nat:
        hits = [(si, sr) for si, sr, stl, str_ in sub
                if stl <= ntr and str_ >= ntl]
        if hits:
            key = (nr.get("TL"), nr.get("TR"))
            overlaps[key]["nat"].append((ni, nr))
            overlaps[key]["sub"].extend(hits)

    for (tl, tr), grp in sorted(overlaps.items()):
        if grp["nat"] and grp["sub"]:
            seen_lines, uniq = set(), []
            for pair in grp["nat"] + grp["sub"]:
                if pair[0] not in seen_lines:
                    seen_lines.add(pair[0])
                    uniq.append(pair)
            grp = {"nat": grp["nat"], "sub": grp["sub"]}
            rows = [str(x) for x in sorted(seen_lines)]
            # Require an explicit double-counting statement. A bare mention of
            # "national" is not evidence of anything - it matches
            # "international", "sub-national" and most narrative prose.
            documented = all(
                re.search(r"do not sum|national total|provincial subset|"
                          r"includes provinces not individually listed|"
                          r"not additive|primary count",
                          (r.get("processing_notes") or ""), re.I)
                for _, r in grp["nat"] + grp["sub"]
            )
            sev = rep.info if documented else rep.warn
            sev(iso, "national_subnational_overlap",
                f"period {tl}..{tr} has both national and sub-national rows "
                f"(rows {','.join(rows)}); processing_notes must state which level "
                f"is primary to prevent double-counting"
                + (" - documented" if documented else ""))

    # ---- orphaned metadata --------------------------------------------------
    for idx, name in sorted(meta_index.items()):
        if idx not in used_sources:
            rep.info(iso, "metadata_unused",
                     f"metadata Index {idx} ({name[:50]}) is not referenced by any data row")

    return {"rows": len(data_rows), "sources": len(meta_index)}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("countries", nargs="*", help="ISO3 codes (default: all MOSAIC countries)")
    ap.add_argument("--json", metavar="PATH", help="write machine-readable report")
    ap.add_argument("--quiet", action="store_true", help="summary table only")
    ap.add_argument("--warn-as-error", action="store_true", help="treat WARN as blocking")
    ap.add_argument("--show-info", action="store_true", help="include INFO findings in output")
    ap.add_argument("--traceback", action="store_true",
                    help="print tracebacks for per-country validator crashes")
    args = ap.parse_args()

    mapping = json.loads(MAPPING.read_text())["countries"]
    mosaic = sorted(k for k, v in mapping.items() if v.get("mosaic_framework"))

    targets = [c.upper() for c in args.countries] if args.countries else mosaic
    bad_scope = [c for c in targets if c not in mosaic]
    if bad_scope:
        print(f"ERROR: not MOSAIC framework countries: {bad_scope}", file=sys.stderr)
        return 2

    rep = Report()
    stats = {}
    crashed = []
    for iso in targets:
        # Isolate per country. Previously one malformed row anywhere raised out
        # of the loop, discarded every accumulated finding, printed nothing, and
        # exited 1 - indistinguishable from an ordinary validation failure.
        try:
            stats[iso] = validate_country(iso, rep)
        except Exception as e:  # noqa: BLE001
            crashed.append(iso)
            stats[iso] = {"rows": 0, "sources": 0}
            rep.error(iso, "validator_crashed",
                      f"{type(e).__name__}: {e} (validation for this country is "
                      f"incomplete; findings below exclude it)")
            if args.traceback:
                traceback.print_exc()

    by_iso = defaultdict(list)
    for f in rep.findings:
        by_iso[f["iso"]].append(f)

    if not args.quiet:
        for iso in targets:
            fs = [f for f in by_iso[iso]
                  if f["severity"] != "INFO" or args.show_info]
            if not fs:
                continue
            print(f"\n=== {iso} ({stats[iso]['rows']} rows, {stats[iso]['sources']} sources) ===")
            for f in fs:
                loc = f" row {f['row']}" if f["row"] else ""
                print(f"  [{f['severity']:5s}] {f['check']}{loc}: {f['message']}")

    counts = rep.counts()
    # Key by (severity, check): a single check can legitimately emit findings at
    # more than one severity, so collapsing to the check name alone would report
    # one severity label for a mixed group.
    by_check = Counter((f["severity"], f["check"]) for f in rep.findings
                       if f["severity"] != "INFO" or args.show_info)

    print("\n" + "=" * 72)
    print(f"Validated {len(targets)} countries | "
          f"{sum(s['rows'] for s in stats.values())} data rows | "
          f"{sum(s['sources'] for s in stats.values())} metadata sources")
    print(f"ERROR {counts['ERROR']}   WARN {counts['WARN']}   INFO {counts['INFO']}")
    if by_check:
        print("\nFindings by check:")
        order = {"ERROR": 0, "WARN": 1, "INFO": 2}
        for (sev, check), n in sorted(by_check.items(),
                                      key=lambda kv: (order[kv[0][0]], -kv[1])):
            isos = sorted({f["iso"] for f in rep.findings
                           if f["check"] == check and f["severity"] == sev})
            shown = " ".join(isos[:8]) + ("..." if len(isos) > 8 else "")
            print(f"  {n:5d}  [{sev:5s}] {check:34s} {shown}")

    if args.json:
        out = Path(args.json)
        out.write_text(json.dumps({
            "generated_at": datetime.now().isoformat(),
            "countries": targets,
            "stats": stats,
            "summary": dict(counts),
            "findings": rep.findings,
        }, indent=2))
        print(f"\nWrote {out}")

    if crashed:
        print(f"\nVALIDATOR CRASHED on {len(crashed)} country(ies): {' '.join(crashed)}")
        print("Their results are incomplete. Re-run with --traceback for detail.")
        return 2  # distinct from 1 so CI can tell a crash from a failed check

    blocking = counts["ERROR"] + (counts["WARN"] if args.warn_as_error else 0)
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
