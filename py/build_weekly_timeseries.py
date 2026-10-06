#!/usr/bin/env python3
"""
Build national-level weekly cholera time series for all 40 MOSAIC countries.

Method:
  - National rows only: Location == "AFR::{ISO}"
  - Seasonal template: Fourier K selected per country by BIC (K=1..floor(n_yrs/3))
      fitted to case-weighted mean of year-normalised weekly fractions
      * Built from national-level weekly observations only (sub-national used as fallback)
      * Regional pooled fallback for countries with < MIN_YEARS outbreak-years of weekly data
  - Disaggregation rules:
      * sCh == 0 over any interval  → zero-fill every covered ISO week
      * sCh  > 0, already weekly    → direct assignment
      * sCh  > 0, non-weekly        → Fourier template slice + renormalise
  - Evidence before provenance: observed weeks (any source) > aggregates by
    span, finest first, distributing only their residual > inferred zeros.
    Source priority WHO > JHU > AI only breaks ties (see process_country)
  - Sub-weekly rows (daily feeds, 24-hour bulletins) are summed per ISO week

Outputs per country:
  data/{ISO}/cholera_weekly_{ISO}.csv
  figures/dashboard/timeseries/cholera_timeseries_{ISO}.png
"""

import csv
import json
import math
import re
import warnings
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
from pathlib import Path
from datetime import date, timedelta
from collections import defaultdict

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

BASE_DIR   = Path(__file__).parent.parent
DATA_DIR   = BASE_DIR / "data"
REF_DIR    = BASE_DIR / "reference"
FIG_DIR    = BASE_DIR / "figures" / "dashboard" / "timeseries"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# Source colours — matches dashboard heatmap legend
COLORS = {
    "JHU": "#0167af",
    "WHO": "#E74C3C",
    "AI":  "#2ECC71",
}
SOURCE_PRIORITY = {"WHO": 3, "JHU": 2, "AI": 1}

MIN_YEARS = 3   # minimum outbreak-years of weekly data for country-specific template
K_MAX     = 8   # maximum harmonics considered during BIC selection

# All time series start from this date regardless of when source data begins.
SERIES_START = date(1970, 1, 1)
# Upper clip: never emit weeks beyond the current date. Observed surveillance data
# cannot exist for the future; this guards against source rows with future/typo/
# aspirational TR dates (e.g. multi-year "elimination strategy" targets) leaking
# future observed/zero/fourier weeks into the series.
SERIES_END = date.today()
# Confidence ceiling for inferred_zero (explicit 0 without a source-documented absence,
# incl. JHU annual zeros). Keeps the ordering documented_zero (>=0.8) > inferred_zero
# (<=0.6) > assumed_zero (0.5), regardless of the source row's stated weight.
INFERRED_ZERO_MAX = 0.6

# Aggregate-row skip threshold: if this fraction of weeks in a non-weekly row's
# span are already covered by JHU observed weekly data, skip the aggregate row
# entirely. Weekly data and annual summaries in JHU come from different reporting
# streams and cannot be reliably reconciled by subtraction; when weekly coverage
# is sufficient, the aggregate row adds noise rather than signal.
COVERAGE_THRESHOLD = 0.50

# Gap-filling: weeks with no source data between existing observations are labelled
# assumed_zero only for periods this many weeks before the most recent observation.
# Weeks more recent than this are left as NA (could be delayed reporting).
ASSUMED_ZERO_LAG_WEEKS = 52

# ---------------------------------------------------------------------------
# Date / ISO-week utilities
# ---------------------------------------------------------------------------

def parse_date(s):
    if not s: return None
    try:   return date.fromisoformat(s.strip())
    except: return None

def week_monday(d):
    """Return the Monday of the ISO week containing d."""
    return d - timedelta(days=d.weekday())

def weeks_in_range(tl, tr):
    """
    Return list of (iso_year, iso_week) tuples whose Monday falls within [tl, tr].
    Starts from the Monday of the week containing tl.
    """
    result = []
    monday = week_monday(tl)
    while monday <= tr:
        result.append(monday.isocalendar()[:2])
        monday += timedelta(weeks=1)
    return result

def isoweek_bounds(year, week):
    """Return (monday, sunday) for an ISO (year, week)."""
    # ISO week 1 contains Jan 4
    jan4   = date(year, 1, 4)
    w1_mon = jan4 - timedelta(days=jan4.weekday())
    monday = w1_mon + timedelta(weeks=week - 1)
    return monday, monday + timedelta(days=6)

# ---------------------------------------------------------------------------
# Fourier template — BIC-selected K
# ---------------------------------------------------------------------------

def _fourier_design(k):
    """Design matrix for K-harmonic Fourier series over 52 weeks."""
    weeks = np.arange(1, 53, dtype=float)
    cols  = [np.ones(52)]
    for i in range(1, k + 1):
        cols.append(np.cos(2 * np.pi * i * weeks / 52))
        cols.append(np.sin(2 * np.pi * i * weeks / 52))
    return np.column_stack(cols)   # shape (52, 2k+1)


def _fit_one_k(median_fracs, k):
    """Fit a single K, return (fitted_52, bic)."""
    n = 52
    X = _fourier_design(k)
    p = X.shape[1]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        coeffs, _, _, _ = np.linalg.lstsq(X, median_fracs, rcond=None)
    fitted = X @ coeffs
    rss    = float(np.sum((median_fracs - fitted) ** 2))
    sigma2 = rss / n
    ll     = (-0.5 * n * np.log(2 * np.pi * sigma2) - rss / (2 * sigma2)
              if sigma2 > 0 else 0.0)
    bic    = p * np.log(n) - 2 * ll
    return fitted, bic


def fit_fourier_bic(median_fracs, k_max=K_MAX):
    """
    Fit K=1..k_max Fourier series, select by BIC.
    Returns (normalised_weights_52, best_k).
    """
    best_k, best_bic, best_fitted = 1, np.inf, None
    for k in range(1, k_max + 1):
        fitted, bic = _fit_one_k(median_fracs, k)
        if bic < best_bic:
            best_bic, best_k, best_fitted = bic, k, fitted
    fitted_pos = np.maximum(best_fitted, 0.0)
    total = fitted_pos.sum()
    weights = fitted_pos / total if total > 0 else np.full(52, 1 / 52)
    return weights, best_k


def build_template_from_data(data_rows):
    """
    data_rows: list of (tl, tr, sch) tuples — sCh > 0, weekly only.
    Returns (template_52, valid_years, best_k).

    Fixes applied vs naive approach:
      - Week 53 folded into week 52 (prevents silent denominator inflation)
      - Case-weighted mean replaces unweighted median (sparse years no longer
        dominate when their fractions are atypical)
      - K_MAX capped at floor(valid_years / 3) to prevent overfitting when
        only a few outbreak-years of data are available
    """
    cases_by_year_week = defaultdict(float)
    for tl, tr, sch in data_rows:
        if (tr - tl).days <= 7 and sch > 0:
            y, w = tl.isocalendar()[:2]
            w = min(w, 52)          # fold week 53 into week 52
            cases_by_year_week[(y, w)] += sch

    if not cases_by_year_week:
        return np.full(52, 1 / 52), 0, 1

    by_year = defaultdict(dict)
    for (y, w), c in cases_by_year_week.items():
        by_year[y][w] = c

    # Store (fraction, year_total) so we can compute a case-weighted mean
    fracs_by_week = defaultdict(list)   # week → [(frac, ytot), ...]
    valid_years   = 0
    for y, wk_cases in by_year.items():
        ytot = sum(wk_cases.values())
        if ytot == 0:
            continue
        valid_years += 1
        for w, c in wk_cases.items():
            fracs_by_week[w].append((c / ytot, ytot))

    # Case-weighted mean: years with more cases exert proportionally more influence
    weighted_fracs = np.zeros(52)
    for w in range(1, 53):
        entries = fracs_by_week.get(w, [])
        if entries:
            fracs = np.array([f for f, _ in entries])
            wts   = np.array([wt for _, wt in entries])
            weighted_fracs[w - 1] = float(np.average(fracs, weights=wts))

    # Cap K at floor(valid_years / 3) to prevent overfitting on sparse data
    k_cap = max(1, valid_years // 3)
    weights, best_k = fit_fourier_bic(weighted_fracs, k_max=min(K_MAX, k_cap))
    return weights, valid_years, best_k


def load_all_weekly_rows(iso, data_dir, national_only=False):
    """
    Load weekly (≤7 day) non-zero rows from JHU + WHO for template building.
    national_only=True: restrict to AFR::{iso} rows (avoids sub-national bias).
    national_only=False: include all geographic levels (used for regional/continental pools).
    """
    national_code = f"AFR::{iso}"
    rows = []
    for src in ("jhu", "who"):
        f = data_dir / f"cholera_data_{src}.csv"
        if not f.exists():
            continue
        with open(f, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if national_only and row.get("Location", "").strip() != national_code:
                    continue
                tl = parse_date(row.get("TL", ""))
                tr = parse_date(row.get("TR", ""))
                if not tl or not tr:
                    continue
                try:
                    sch = float(row.get("sCh", "") or 0)
                except ValueError:
                    continue
                rows.append((tl, tr, sch))
    return rows


def build_all_templates(country_map):
    """
    Build BIC-selected Fourier templates for all MOSAIC countries.
    Falls back to regional pooled template for countries with < MIN_YEARS.
    Returns dict: {iso: (template_52, method_str)}
      method_str encodes both scope and K, e.g. "country_k4", "regional_West Africa_k3"
    """
    # Per-country templates — national rows preferred; sub-national as fallback
    per_country = {}
    for iso in sorted(country_map):
        d = DATA_DIR / iso
        if not d.is_dir():
            continue
        rows = load_all_weekly_rows(iso, d, national_only=True)
        tmpl, n_yrs, k = build_template_from_data(rows)
        if n_yrs < MIN_YEARS:
            # Not enough national-only data; include sub-national rows as fallback
            rows = load_all_weekly_rows(iso, d, national_only=False)
            tmpl, n_yrs, k = build_template_from_data(rows)
        per_country[iso] = (tmpl, n_yrs, k, country_map[iso].get("subregion", "Africa"))

    # Regional pooled templates (for fallback)
    regional_rows = defaultdict(list)
    for iso, (_, n_yrs, _k, subregion) in per_country.items():
        if n_yrs >= MIN_YEARS:
            regional_rows[subregion].extend(
                load_all_weekly_rows(iso, DATA_DIR / iso)
            )

    regional_templates = {}
    for subregion, rows in regional_rows.items():
        tmpl, _, k = build_template_from_data(rows)
        regional_templates[subregion] = (tmpl, k)

    # Continental fallback
    all_rows = []
    for iso in per_country:
        all_rows.extend(load_all_weekly_rows(iso, DATA_DIR / iso))
    continental, _, k_cont = build_template_from_data(all_rows)

    # Assign final templates
    templates = {}
    for iso, (tmpl, n_yrs, k, subregion) in per_country.items():
        if n_yrs >= MIN_YEARS:
            templates[iso] = (tmpl, f"country_k{k}")
        elif subregion in regional_templates:
            reg_tmpl, reg_k = regional_templates[subregion]
            templates[iso] = (reg_tmpl, f"regional_{subregion}_k{reg_k}")
        else:
            templates[iso] = (continental, f"continental_k{k_cont}")

    return templates

# ---------------------------------------------------------------------------
# Per-country national weekly series
# ---------------------------------------------------------------------------

def load_national_rows(iso, src, data_dir):
    """
    Load all rows where Location == "AFR::{iso}" exactly.
    Returns list of dicts with keys: tl, tr, sch, deaths, confidence, source_db.
    """
    national_code = f"AFR::{iso}"
    rows = []
    f = data_dir / f"cholera_data_{src}.csv"
    if not f.exists():
        return rows
    with open(f, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("Location", "").strip() != national_code:
                continue
            tl = parse_date(row.get("TL", ""))
            tr = parse_date(row.get("TR", ""))
            if not tl or not tr:
                continue
            # Distinguish a blank sCh (no count reported → no information) from an
            # explicit 0 (a reported/documented zero). A blank must NOT be treated
            # as a zero observation.
            raw_sch = (row.get("sCh", "") or "").strip()
            has_count = raw_sch != ""
            try:    sch = float(raw_sch) if has_count else 0.0
            except: sch, has_count = 0.0, False
            deaths_raw = row.get("deaths", "").strip()
            try:    deaths = float(deaths_raw) if deaths_raw else None
            except: deaths = None
            # Deaths above cases is impossible (6 JHU COD weekly rows in 2015-16,
            # e.g. 148 cases / 495 deaths - likely cumulative deaths). Treat the
            # deaths as missing rather than propagate them; the source is untouched.
            if deaths is not None and has_count and deaths > sch:
                deaths = None
            try:    conf = float(row.get("confidence_weight", "") or 0.9)
            except: conf = 0.9
            # Evidence type for zero-rows, parsed from processing_notes. Only a
            # source-confirmed absence may be labelled documented_zero.
            #
            # Read the row's OWN canonical label — the first "Evidence type: X"
            # sentence, which add_observation.py's add-zero writes at insert
            # time — in preference to a bare substring scan. A bare scan reads
            # the whole note, including later agents' adjudication prose, so a
            # row saying "UPGRADE TO Documented_Absence REJECTED ... stays
            # Inferred_Absence" was being graded documented_zero: the exact
            # inverse of the adjudication. That silently discarded deliberate
            # absence grading (12 rows in TGO, 1 each in ERI and NER, all of
            # them over-claiming). Rows with no canonical token fall back to the
            # original substring behaviour.
            note = (row.get("processing_notes", "") or "").lower()
            _canon = re.search(r"evidence type:\s*([a-z_]+)", note)
            _tok = _canon.group(1) if _canon else note
            if   "documented_absence" in _tok: evidence = "documented"
            elif "inferred_absence"   in _tok: evidence = "inferred"
            elif "surveillance_gap"   in _tok: evidence = "gap"
            elif _canon:                       evidence = "none"
            elif "documented_absence" in note: evidence = "documented"
            elif "inferred_absence"   in note: evidence = "inferred"
            elif "surveillance_gap"   in note: evidence = "gap"
            else:                              evidence = "none"
            rows.append({"tl": tl, "tr": tr, "sch": sch, "has_count": has_count,
                         "evidence": evidence, "deaths": deaths, "conf": conf,
                         "primary": "primary: false" not in note})
    return rows


def _midpoint_week(r):
    """ISO (year, week) containing the midpoint of a row's [TL, TR] span."""
    return (r["tl"] + (r["tr"] - r["tl"]) / 2).isocalendar()[:2]


def _sum_subweekly(rows):
    """
    Collapse sub-weekly rows (span < 6 days) of ONE source into per-ISO-week
    totals. Daily feeds (JHU daily rows, MoH "last 24 hours" bulletins, WHO
    WER 5-day windows) report successive non-overlapping counts, so the week's
    value is their SUM - the old builder kept only the largest single day.

    Exact (TL, TR) duplicates are collapsed to one row (max sCh). Rows whose
    half-open span [TL, max(TR, TL+1)) overlaps an already-kept row are dropped
    so nested restatements are not double-counted; the half-open form lets the
    "TL = day, TR = next day" 24-hour convention chain without overlapping.
    Each row is credited to the ISO week holding its midpoint.

    Returns {week_key: {"sch", "deaths", "conf"}} and the number dropped.
    """
    by_span = {}
    for r in rows:
        k = (r["tl"], r["tr"])
        if k not in by_span or r["sch"] > by_span[k]["sch"]:
            by_span[k] = r
    kept, dropped, last_end = [], 0, None
    for r in sorted(by_span.values(), key=lambda r: (r["tl"], -(r["tr"] - r["tl"]).days)):
        end = max(r["tr"], r["tl"] + timedelta(days=1))
        if last_end is not None and r["tl"] < last_end:
            dropped += 1
            continue
        kept.append(r)
        last_end = end
    dropped += len(rows) - len(by_span)
    weeks = {}
    for r in kept:
        w = weeks.setdefault(_midpoint_week(r), {"sch": 0.0, "deaths": None, "confs": []})
        w["sch"] += r["sch"]
        if r["deaths"] is not None:
            w["deaths"] = (w["deaths"] or 0.0) + r["deaths"]
        w["confs"].append(r["conf"])
    return ({k: {"sch": v["sch"], "deaths": v["deaths"],
                 "conf": sum(v["confs"]) / len(v["confs"])} for k, v in weeks.items()},
            dropped)


def _decumulate(rows):
    """
    Convert cumulative reporting chains into increments, within ONE source.

    Situation reports and bulletins mostly give totals "since 1 January" or
    "since the outbreak began": NGA 2010 has Jan 1 -> Aug 19 = 4,665,
    -> Aug 25 = 6,437, ... -> Oct 22 = 40,000, -> Dec 31 = 44,456. Each later
    row restates the earlier ones. A row B is replaced by the increment over
    the latest row A that starts within 3 days of B, ends before B, and has
    0 < A.sCh <= B.sCh: span (A.TR, B.TR], count B.sCh - A.sCh. Non-monotone
    pairs (conflicting reports) are left as they are. A zero increment carries
    no usable information and is dropped rather than turned into a zero.

    Rows with identical (TL, TR) are conflicting restatements of one period;
    only the largest is kept, so the increment is taken against the same row
    that is placed (otherwise Jan-Mar 100 and 120 + Jan-Jun 250 gave 230).
    """
    best = {}
    for r in rows:
        k = (r["tl"], r["tr"])
        if k not in best or (r["sch"], r["conf"]) > (best[k]["sch"], best[k]["conf"]):
            best[k] = r
    rows = list(best.values())
    out = []
    for b in rows:
        b["chain_tl"] = b["tl"]   # cumulative series are identified by their start date
        prev = [a for a in rows
                if a is not b and abs((a["tl"] - b["tl"]).days) <= 3
                and a["tr"] < b["tr"] and 0 < a["sch"] <= b["sch"]]
        if not prev:
            out.append(b)
            continue
        a = max(prev, key=lambda a: (a["tr"], a["sch"]))
        inc = b["sch"] - a["sch"]
        if inc <= 0:
            continue
        nb = dict(b)
        nb["tl"] = a["tr"] + timedelta(days=1)
        nb["sch"] = inc
        if b["deaths"] is not None and a["deaths"] is not None:
            nb["deaths"] = max(b["deaths"] - a["deaths"], 0.0)
        else:
            nb["deaths"] = None
        nb["span"] = (nb["tr"] - nb["tl"]).days
        # Rank by how specific the original statement was, not the derived
        # increment: CMR 1983's AI annual (4,534) became a May-Dec increment and
        # outranked JHU's official annual (55).
        nb["order_span"] = b.get("order_span", b["span"])
        nb["increment"] = True
        nb["chain_tl"] = b["tl"]
        out.append(nb)
    return out


def process_country(iso, template_info, diag=None):
    """
    Build the national weekly time series dict for one country.
    Returns dict: {(iso_year, iso_week): entry_dict}
    where entry_dict has: sch, deaths, source, confidence, method, monday, sunday

    Evidence beats provenance. Every week is filled by the most direct evidence
    available from ANY source, and source priority (WHO > JHU > AI) only breaks
    ties between equally direct evidence:

      1. observed      weekly rows (6-7 day span), or the SUM of a source's
                       sub-weekly rows in that week; a source's own weekly row
                       beats its daily sum; across sources, WHO > JHU > AI.
      2. aggregates    multi-week rows, shortest span first (a month before a
                       year before a decade). Positive rows distribute only the
                       RESIDUAL - their total minus what finer evidence already
                       placed inside their span - over still-empty weeks, so
                       nested or cumulative rows cannot inflate the series.
                       A positive row whose span is >= COVERAGE_THRESHOLD
                       observed is skipped. Documented zeros fill empty weeks.
      3. inferred_zero weakest; fills only weeks nothing else reached.

    The previous version ranked by source first, so a JHU annual total spread by
    the Fourier template overrode AI weekly observations of the same weeks, and
    overlapping aggregates each spread their FULL total (the larger per week
    kept): AGO 2006 summed to 118,764 against WHO's 67,257.

    Method labels are unchanged ("observed", "documented_zero", "fourier_*",
    "inferred_zero", "assumed_zero"); MOSAIC-pkg's process_AI_cholera_data()
    filters on them.
    """
    template, tmpl_method = template_info
    d = DATA_DIR / iso
    merged = {}   # {(year, week): entry}
    if diag is None:
        diag = {}
    diag.update(subweekly_dropped=0, residual_skipped=0, coverage_skipped=0)

    rows = []
    for src_name, src_label in [("who", "WHO"), ("jhu", "JHU"), ("ai", "AI")]:
        for r in load_national_rows(iso, src_name, d):
            if not r["has_count"]:
                continue   # blank sCh = no count reported = no information
            r["source"] = src_label
            r["span"] = (r["tr"] - r["tl"]).days
            rows.append(r)

    # JHU marks duplicate reports it did not select as "Primary: False". Where a
    # primary JHU row covers the same period, the non-primary one is a restated
    # duplicate: AGO's non-primary 2007-05-10..12-31 row carries the full 2007
    # annual total (18,422) and, being finer than the annual row, doubled 2007.
    # Only a primary row of comparable span (within 2x) covering at least half
    # of the non-primary row makes it a duplicate; a primary ANNUAL row does not
    # make non-primary WEEKLY rows duplicates - they are the only weekly detail.
    jhu_primary = [r for r in rows if r["source"] == "JHU" and r["primary"]]

    def _end(x):   # half-open end, so TR = TL + 1 daily rows chain without overlap
        return max(x["tr"], x["tl"] + timedelta(days=1))

    def _dup_of_primary(r):
        span = max(r["span"], 1)
        for p in jhu_primary:
            ov = (min(_end(p), _end(r)) - max(p["tl"], r["tl"])).days
            if ov >= 0.5 * (_end(r) - r["tl"]).days and max(p["span"], 1) <= 2 * span \
                    and span <= 2 * max(p["span"], 1):
                return True
        return False
    n_before = len(rows)
    rows = [r for r in rows if not (r["source"] == "JHU" and not r["primary"]
                                    and _dup_of_primary(r))]
    diag["jhu_nonprimary_dropped"] = n_before - len(rows)

    def entry(key, sch, deaths, source, conf, method, origin=None, chain=None):
        # _origin = the [TL, TR] span of the row that filled this week; Tier 2
        # uses it to tell weeks filled by rows nested inside an aggregate's own
        # span (parts of its total) from weeks taken by rows reaching outside it.
        mon, sun = isoweek_bounds(*key)
        return {"sch": sch, "deaths": deaths, "source": source,
                "confidence": conf, "method": method, "monday": mon, "sunday": sun,
                "_origin": origin or (mon, sun), "_chain": chain}

    # ── Tier 1: observed weeks ──────────────────────────────────────────────
    candidates = defaultdict(dict)   # key -> {source: entry}
    for label in ("WHO", "JHU", "AI"):
        src_rows = [r for r in rows if r["source"] == label]
        for r in (r for r in src_rows if 6 <= r["span"] <= 7):
            key = r["tl"].isocalendar()[:2]
            prev = candidates[key].get(label)
            if prev is None or prev.get("_daily") or r["sch"] > prev["sch"]:
                candidates[key][label] = entry(key, r["sch"], r["deaths"], label,
                                               r["conf"], "observed")
        sums, dropped = _sum_subweekly([r for r in src_rows if r["span"] < 6])
        diag["subweekly_dropped"] += dropped
        for key, v in sums.items():
            if label in candidates[key]:
                continue   # the source's own weekly row beats its daily sum
            e = entry(key, v["sch"], v["deaths"], label, v["conf"], "observed")
            e["_daily"] = True
            candidates[key][label] = e
    for key, by_src in candidates.items():
        best = max(by_src.values(), key=lambda e: SOURCE_PRIORITY[e["source"]])
        best.pop("_daily", None)
        merged[key] = best
    observed_keys = set(merged)

    # ── Tier 2: aggregates, finest span first ───────────────────────────────
    def agg_order(r):
        # Spans within a factor of ~1.5 count as equally specific; only clearly
        # finer evidence (a month vs a year) wins on span alone. Otherwise an
        # AI Nov-2021..Oct-2022 season (353 d) outranked JHU's official 2021
        # annual row (364 d) and put 1,406 cases into a year JHU reports as 2.
        span = r.get("order_span", r["span"])
        bucket = int(math.log(max(span, 1)) / math.log(1.5))
        kind = 0 if r["sch"] == 0 else 1   # documented zero before positive on ties
        return (bucket, -SOURCE_PRIORITY[r["source"]], kind, -r["conf"], span)

    aggregates = [r for r in rows if r["span"] > 7 and r["sch"] == 0
                  and r["evidence"] == "documented"]
    for label in ("WHO", "JHU", "AI"):
        aggregates += _decumulate([r for r in rows if r["source"] == label
                                   and r["span"] > 7 and r["sch"] > 0])
    for r in sorted(aggregates, key=agg_order):
        weeks = weeks_in_range(r["tl"], r["tr"])
        if not weeks:
            continue
        if r["sch"] == 0:
            # Same Monday-inside-span rule as positive rows: a 2016 zero must
            # not claim 2015-W53 (Monday 28 Dec 2015).
            for key in [k for k in weeks if isoweek_bounds(*k)[0] >= r["tl"]] or weeks:
                if key not in merged:
                    merged[key] = entry(key, 0.0, 0.0, r["source"], r["conf"],
                                        "documented_zero", (r["tl"], r["tr"]))
            continue

        covered = sum(1 for k in weeks if k in observed_keys) / len(weeks)
        if covered >= COVERAGE_THRESHOLD:
            diag["coverage_skipped"] += 1
            continue
        # Only weeks whose Monday is inside the span (no Jan-1 spillover into
        # the previous ISO year's last week).
        # A short increment starting mid-week may hold no Monday; then use the
        # week containing it.
        in_span = [k for k in weeks if isoweek_bounds(*k)[0] >= r["tl"]] or weeks
        eligible = [k for k in in_span if k not in merged]
        if not eligible:
            # A short increment of a cumulative chain (sitreps every 2-3 days)
            # often lands in a week an earlier increment of the same chain
            # already filled; add to it rather than drop the cases.
            if r.get("increment"):
                # Only weeks filled by the SAME cumulative series (same source,
                # start within 3 days); adding to weeks another row of that
                # source filled double-counted (AGO 2006 rose to 76,975).
                def same_chain(c):
                    return (c is not None and c[0] == r["source"]
                            and abs((c[1] - r["chain_tl"]).days) <= 3)
                chain = [k for k in in_span if merged[k]["method"].startswith("fourier")
                         and same_chain(merged[k].get("_chain"))]
                if chain:
                    for k in chain:
                        merged[k]["sch"] += r["sch"] / len(chain)
                        if r["deaths"] is not None:
                            merged[k]["deaths"] = (merged[k]["deaths"] or 0.0) + r["deaths"] / len(chain)
                    diag["increments_merged"] = diag.get("increments_merged", 0) + 1
                    continue
            diag["residual_skipped"] += 1
            continue
        def tmpl(keys):
            return template[[min(w, 52) - 1 for _, w in keys]]   # clamp week 53 → 52
        # 3-day tolerance: an observed ISO week straddling Dec 31 belongs to
        # the calendar-year total it mostly falls in.
        tol = timedelta(days=3)
        nested = [k for k in weeks if k in merged
                  and merged[k]["_origin"][0] >= r["tl"] - tol
                  and merged[k]["_origin"][1] <= r["tr"] + tol]
        taken = {k for k in in_span if k in merged and k not in nested}
        # Weeks taken by rows reaching outside this span keep their values, and
        # this row keeps only its seasonal share of the weeks NOT taken. Weeks
        # filled by rows nested inside the span are parts of this total, so they
        # are subtracted (the residual). Without the share, MWI's Nov-2011..
        # Oct-2012 season (1,806) - whose 2012 weeks were taken by JHU's 2012
        # annual row - dumped 1,560 cases into the last two weeks of 2011.
        w_all = tmpl(in_span)
        w_free = tmpl([k for k in in_span if k not in taken]) if len(taken) < len(in_span) else np.zeros(0)
        # Fall back to week counts when the template gives the free weeks no
        # weight (the fitted template is clipped at 0); otherwise the whole
        # count would vanish.
        if w_all.sum() > 0 and w_free.sum() > 0:
            share = w_free.sum() / w_all.sum()
        else:
            share = (len(in_span) - len(taken)) / len(in_span)
        amount = r["sch"] * share - sum(merged[k]["sch"] for k in nested)
        # Tolerance: float residue (~1e-15) must not turn intended
        # inferred_zero weeks into fourier_* weeks MOSAIC reads as data.
        if amount <= 1e-6 * max(r["sch"], 1.0):
            # Finer evidence already accounts for this total, so the row asserts
            # the rest of its span is empty. Claim those weeks as inferred_zero
            # so a lower-confidence row for the same span cannot override it
            # (MOSAIC-pkg treats inferred_zero weeks as missing, not as zeros).
            diag["residual_skipped"] += 1
            for key in eligible:
                merged[key] = entry(key, 0.0, 0.0, r["source"],
                                    min(r["conf"], INFERRED_ZERO_MAX), "inferred_zero",
                                    (r["tl"], r["tr"]))
            continue
        d_res = None
        if r["deaths"] is not None:
            d_res = max(r["deaths"] * share - sum(merged[k]["deaths"] or 0.0 for k in nested), 0.0)
        residual = amount
        w_elig = tmpl(eligible)

        wt_sum = w_elig.sum()
        weights = (np.ones(len(eligible)) / len(eligible)) if wt_sum <= 0 else w_elig / wt_sum

        # Confidence scales with the number of weeks being disaggregated.
        n_elig = len(eligible)
        conf_factor = 0.9 if n_elig <= 4 else 0.8 if n_elig <= 13 else 0.7 if n_elig <= 26 else 0.5
        for key, wt in zip(eligible, weights):
            # Deaths and cases residuals are computed separately, so cap the
            # week's deaths at its cases (133 weeks had deaths > sCh).
            merged[key] = entry(key, residual * float(wt),
                                min(d_res * float(wt), residual * float(wt))
                                if d_res is not None else None,
                                r["source"], r["conf"] * conf_factor,
                                f"fourier_{tmpl_method}", (r["tl"], r["tr"]),
                                (r["source"], r["chain_tl"]) if "chain_tl" in r else None)

    # ── Tier 3: inferred zeros ──────────────────────────────────────────────
    # An explicit 0 without a source-confirmed absence (inferred, surveillance
    # gap or untagged, incl. JHU annual zeros) only fills what nothing else did.
    inferred = [r for r in rows if r["span"] > 7 and r["sch"] == 0
                and r["evidence"] != "documented"]
    for r in sorted(inferred, key=agg_order):
        wks = weeks_in_range(r["tl"], r["tr"])
        for key in [k for k in wks if isoweek_bounds(*k)[0] >= r["tl"]] or wks:
            if key not in merged:
                merged[key] = entry(key, 0.0, 0.0, r["source"],
                                    min(r["conf"], INFERRED_ZERO_MAX), "inferred_zero",
                                    (r["tl"], r["tr"]))

    # ── Clip to [SERIES_START, SERIES_END] (drop pre-1970 and future weeks) ──
    series_start_monday = week_monday(SERIES_START)
    series_end_monday   = week_monday(SERIES_END)
    merged = {k: v for k, v in merged.items()
              if series_start_monday <= v["monday"] <= series_end_monday}

    # ── Assumed-zero gap fill ──────────────────────────────────────────────
    # For historical periods: any ISO week that lies between the series start
    # (or earliest sourced observation, whichever is later) and the cutoff but
    # has NO source entry is labelled assumed_zero (confidence 0.5).
    # Weeks within ASSUMED_ZERO_LAG_WEEKS of the most recent observation are
    # left as NA to avoid masking delayed reporting.
    if merged:
        mondays     = [e["monday"] for e in merged.values()]
        earliest    = max(min(mondays), series_start_monday)
        latest      = max(mondays)
        cutoff      = latest - timedelta(weeks=ASSUMED_ZERO_LAG_WEEKS)

        current = earliest
        while current <= cutoff:
            key = current.isocalendar()[:2]
            if key not in merged:
                mon, sun = isoweek_bounds(*key)
                merged[key] = {
                    "sch":        0.0,
                    "deaths":     0.0,
                    "source":     "none",
                    "confidence": 0.5,
                    "method":     "assumed_zero",
                    "monday":     mon,
                    "sunday":     sun,
                    "_origin":    (mon, sun),
                }
            current += timedelta(weeks=1)

    return merged

# ---------------------------------------------------------------------------
# Write CSV
# ---------------------------------------------------------------------------

WEEKLY_COLS = [
    "iso_code", "year", "iso_week", "week_start", "week_end",
    "sCh", "deaths", "source", "confidence_weight", "disaggregation_method",
]

def write_weekly_csv(iso, series):
    out = DATA_DIR / iso / f"cholera_weekly_{iso}.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=WEEKLY_COLS)
        writer.writeheader()
        for (yr, wk), e in sorted(series.items()):
            sch_val    = round(e["sch"],    4) if e["sch"]    is not None else ""
            deaths_val = round(e["deaths"], 4) if e["deaths"] is not None else ""
            writer.writerow({
                "iso_code": iso,
                "year": yr,
                "iso_week": wk,
                "week_start": e["monday"].isoformat(),
                "week_end":   e["sunday"].isoformat(),
                "sCh":    sch_val,
                "deaths": deaths_val,
                "source": e["source"],
                "confidence_weight": round(e["confidence"], 3),
                "disaggregation_method": e["method"],
            })
    return out

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------

plt.rcParams.update({
    "font.family":        "sans-serif",
    "font.size":          10,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          True,
    "axes.grid.axis":     "y",
    "grid.alpha":         0.25,
    "grid.linewidth":     0.6,
    "figure.facecolor":   "white",
    "axes.facecolor":     "white",
    "xtick.major.size":   4,
    "ytick.major.size":   3,
})


def _draw_bars(ax, x, vals, srcs, meths, bar_width=5.5):
    """Draw coloured bars on ax, skipping assumed_zero (always sCh=0)."""
    for xi, yi, src, meth in zip(x, vals, srcs, meths):
        if meth == "assumed_zero" or yi is None:
            continue
        alpha = 0.85 if meth == "observed" else 0.45
        ax.bar(xi, yi, width=bar_width, color=COLORS[src], alpha=alpha,
               linewidth=0, align="edge")


def _style_xaxis(ax):
    ax.xaxis.set_major_locator(mdates.YearLocator(5))
    ax.xaxis.set_minor_locator(mdates.YearLocator(1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(axis="x", which="minor", length=2, color="#aaa")
    ax.tick_params(axis="x", which="major", length=5)


def _fmt_yaxis(ax):
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: f"{int(v):,}" if v >= 1 else ("0" if v == 0 else f"{v:.1f}")))


def plot_weekly_series(iso, series, country_name, template_method):
    if not series:
        return

    # Sort and build arrays
    items   = sorted(series.items())
    mondys  = [e["monday"]           for _, e in items]
    schs    = [e["sch"]              for _, e in items]
    deaths  = [e.get("deaths")       for _, e in items]   # may be None
    srcs    = [e["source"]           for _, e in items]
    meths   = [e["method"]           for _, e in items]

    x         = mdates.date2num(mondys)
    bar_width = 5.5
    x_min     = mdates.date2num(SERIES_START)
    x_max     = mdates.date2num((mondys[-1] + timedelta(weeks=4)) if mondys else SERIES_START)

    has_deaths = any(d is not None and d > 0 for d in deaths)

    # ── Figure: two panels if deaths data exists, one panel otherwise ──────
    if has_deaths:
        fig, (ax_top, ax_bot) = plt.subplots(
            2, 1, figsize=(22, 7.5), sharex=True,
            gridspec_kw={"height_ratios": [3, 1.5], "hspace": 0.08},
        )
    else:
        fig, ax_top = plt.subplots(figsize=(22, 4.5))
        ax_bot = None
    fig.patch.set_facecolor("white")

    # ── Top panel: suspected cases ─────────────────────────────────────────
    _draw_bars(ax_top, x, schs, srcs, meths, bar_width)
    _style_xaxis(ax_top)
    _fmt_yaxis(ax_top)
    ax_top.set_ylabel("Suspected cases / week", fontsize=10)
    ax_top.set_xlim(x_min, x_max)
    if any(v > 0 for v in schs):
        ax_top.set_ylim(0, max(schs) * 1.12)

    # ── Bottom panel: reported deaths ──────────────────────────────────────
    if ax_bot is not None:
        _draw_bars(ax_bot, x, deaths, srcs, meths, bar_width)
        _style_xaxis(ax_bot)
        _fmt_yaxis(ax_bot)
        ax_bot.set_ylabel("Deaths / week", fontsize=10)
        ax_bot.set_xlim(x_min, x_max)
        nonnull = [d for d in deaths if d is not None]
        if nonnull and max(nonnull) > 0:
            ax_bot.set_ylim(0, max(nonnull) * 1.15)
        ax_bot.set_xlabel("")

    # ── Legend — shared, drawn on top panel ───────────────────────────────
    obs_srcs    = {e["source"] for e in series.values() if e["method"] == "observed"}
    disagg_srcs = {e["source"] for e in series.values()
                   if e["method"] not in ("observed", "documented_zero", "assumed_zero")}
    legend_items = []
    for src_label in ("JHU", "WHO", "AI"):
        color = COLORS[src_label]
        if src_label in obs_srcs:
            legend_items.append(mpatches.Patch(
                facecolor=color, alpha=0.85, label=f"{src_label} (observed)"))
        if src_label in disagg_srcs:
            legend_items.append(mpatches.Patch(
                facecolor=color, alpha=0.45, label=f"{src_label} (Fourier disaggregated)"))
    ax_top.legend(handles=legend_items, loc="upper right", fontsize=9,
                  frameon=False, ncol=len(legend_items))

    # ── Subtitle & title on top panel ─────────────────────────────────────
    n_obs      = sum(1 for m in meths if m == "observed")
    n_disagg   = sum(1 for m in meths if m.startswith("fourier"))
    n_doc_zero = sum(1 for m in meths if m == "documented_zero")
    n_assumed  = sum(1 for m in meths if m == "assumed_zero")
    src_counts = {s: sum(1 for ss in srcs if ss == s) for s in ("JHU", "WHO", "AI")}
    src_parts  = [f"{s}: {n} wks" for s, n in src_counts.items() if n > 0]

    _km = re.search(r'_k(\d+)$', template_method)
    _k_str = f"K={_km.group(1)}" if _km else ""
    if template_method.startswith("country"):
        tmpl_label = f"country-specific seasonal template ({_k_str})"
    elif template_method.startswith("regional_"):
        region = re.sub(r'_k\d+$', '', template_method).replace("regional_", "")
        tmpl_label = f"regional seasonal template — {region} ({_k_str})"
    else:
        tmpl_label = f"continental seasonal template ({_k_str})"

    sub = (f"Observed: {n_obs}  |  Fourier disaggregated: {n_disagg}  |  "
           f"Documented zero: {n_doc_zero}  |  Assumed zero: {n_assumed}  |  "
           f"{tmpl_label}  |  " + "  ".join(src_parts))
    ax_top.text(0.0, 1.01, sub, transform=ax_top.transAxes,
                fontsize=8, color="#888", va="bottom", ha="left")
    ax_top.set_title(
        f"{country_name}  ({iso})  —  Weekly Cholera Surveillance",
        fontsize=13, fontweight="bold", color="#222", pad=22, loc="left",
    )

    fig.tight_layout()
    out = FIG_DIR / f"cholera_timeseries_{iso}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_country_map():
    with open(REF_DIR / "country_mapping.json") as f:
        raw = json.load(f)
    return {
        iso: meta
        for iso, meta in raw["countries"].items()
        if meta.get("mosaic_framework")
    }


def main():
    country_map = load_country_map()
    iso_to_name = {
        iso: meta.get("name", iso) for iso, meta in country_map.items()
    }

    print(f"Building seasonal templates for {len(country_map)} countries…")
    templates = build_all_templates(country_map)

    n_country  = sum(1 for _, (_, m) in templates.items() if m.startswith("country"))
    n_regional = sum(1 for _, (_, m) in templates.items() if m.startswith("regional"))
    n_cont     = sum(1 for _, (_, m) in templates.items() if m.startswith("continental"))
    print(f"  Country-specific: {n_country}  |  Regional: {n_regional}  "
          f"|  Continental fallback: {n_cont}")

    csvs, plots = [], []
    for iso in sorted(country_map):
        d = DATA_DIR / iso
        if not d.is_dir():
            continue

        template_info = templates.get(iso)
        if template_info is None:
            continue

        diag = {}
        series = process_country(iso, template_info, diag)
        if not series:
            print(f"  {iso}: no data")
            continue

        n_weeks  = len(series)
        n_nonzero = sum(1 for e in series.values() if e["sch"] > 0)
        tmpl_meth = template_info[1]

        csv_path = write_weekly_csv(iso, series)
        csvs.append(csv_path)

        fig_path = plot_weekly_series(
            iso, series,
            country_name=iso_to_name.get(iso, iso),
            template_method=tmpl_meth,
        )
        plots.append(fig_path)

        print(f"  {iso}: {n_weeks} weeks total, {n_nonzero} non-zero  "
              f"[template: {tmpl_meth}]  (sub-weekly dropped {diag['subweekly_dropped']}, "
              f"aggregates skipped: residual {diag['residual_skipped']}, "
              f"coverage {diag['coverage_skipped']}; JHU non-primary dropped "
              f"{diag['jhu_nonprimary_dropped']})")

    print(f"\nDone.  {len(csvs)} CSVs and {len(plots)} plots written.")
    print(f"  CSVs:  data/{{ISO}}/cholera_weekly_{{ISO}}.csv")
    print(f"  Plots: figures/dashboard/timeseries/")


if __name__ == "__main__":
    main()
