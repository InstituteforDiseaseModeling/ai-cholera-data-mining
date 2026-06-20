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
  - Source priority (high→low): WHO > JHU > AI
  - JHU weekly observed rows take precedence over JHU non-weekly disaggregated rows

Outputs per country:
  data/{ISO}/cholera_weekly_{ISO}.csv
  figures/dashboard/timeseries/cholera_timeseries_{ISO}.png
"""

import csv
import json
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
            try:    conf = float(row.get("confidence_weight", "") or 0.9)
            except: conf = 0.9
            # Evidence type for zero-rows, parsed from processing_notes. Only a
            # source-confirmed absence may be labelled documented_zero.
            note = (row.get("processing_notes", "") or "").lower()
            if   "documented_absence" in note: evidence = "documented"
            elif "inferred_absence"   in note: evidence = "inferred"
            elif "surveillance_gap"   in note: evidence = "gap"
            else:                              evidence = "none"
            rows.append({"tl": tl, "tr": tr, "sch": sch, "has_count": has_count,
                         "evidence": evidence, "deaths": deaths, "conf": conf})
    return rows


def process_country(iso, template_info):
    """
    Build the national weekly time series dict for one country.
    Returns dict: {(iso_year, iso_week): entry_dict}
    where entry_dict has: sch, deaths, source, confidence, method, monday, sunday
    """
    template, tmpl_method = template_info
    d = DATA_DIR / iso
    merged = {}   # {(year, week): entry}

    def try_insert(key, entry):
        existing = merged.get(key)
        if existing is None:
            merged[key] = entry
            return
        if SOURCE_PRIORITY[entry["source"]] > SOURCE_PRIORITY[existing["source"]]:
            merged[key] = entry
        # Same source: prefer by method quality, then higher sCh.
        # Rank: observed > documented_zero > fourier(positive) > inferred_zero.
        elif SOURCE_PRIORITY[entry["source"]] == SOURCE_PRIORITY[existing["source"]]:
            def _mrank(m):
                if m == "observed":         return 4
                if m == "documented_zero":  return 3
                if m.startswith("fourier"): return 2
                if m == "inferred_zero":    return 1
                return 0
            re_, rx_ = _mrank(entry["method"]), _mrank(existing["method"])
            if re_ > rx_ or (re_ == rx_ and entry["sch"] > existing["sch"]):
                merged[key] = entry

    # Process sources lowest→highest priority so higher-priority writes last
    for src_name, src_label in [("ai", "AI"), ("jhu", "JHU"), ("who", "WHO")]:
        rows = load_national_rows(iso, src_name, d)

        # Separate weekly and non-weekly
        weekly     = [r for r in rows if (r["tr"] - r["tl"]).days <= 7]
        non_weekly = [r for r in rows if (r["tr"] - r["tl"]).days  > 7]

        # 1. Assign weekly rows directly
        weekly_covered = set()
        for r in weekly:
            if not r["has_count"]:
                continue   # blank sCh = no count reported; not an observation
            key = r["tl"].isocalendar()[:2]
            weekly_covered.add(key)
            mon, sun = isoweek_bounds(*key)
            try_insert(key, {
                "sch":    r["sch"],
                "deaths": r["deaths"],
                "source": src_label,
                "confidence": r["conf"],
                "method": "observed",
                "monday": mon,
                "sunday": sun,
            })

        # 2. Disaggregate non-weekly rows
        for r in non_weekly:
            if not r["has_count"]:
                continue   # blank sCh = no count = no information; do NOT emit a zero
            weeks = weeks_in_range(r["tl"], r["tr"])

            if r["sch"] == 0:
                # Only a source-confirmed absence is a documented_zero; an explicit 0
                # without such evidence (inferred/surveillance-gap/untagged, incl. JHU
                # annual zeros) is a weaker inferred_zero.
                zero_method = "documented_zero" if r["evidence"] == "documented" else "inferred_zero"
                for key in weeks:
                    if src_label == "JHU" and key in weekly_covered:
                        continue   # don't let annual zeros overwrite weekly observed
                    mon, sun = isoweek_bounds(*key)
                    try_insert(key, {
                        "sch":    0.0,
                        "deaths": 0.0,
                        "source": src_label,
                        "confidence": r["conf"],
                        "method": zero_method,
                        "monday": mon,
                        "sunday": sun,
                    })
            else:
                # Coverage threshold: if ≥50% of this row's span is already
                # covered by observed weekly data, skip the aggregate entirely.
                # JHU weekly and annual rows come from different reporting
                # streams and cannot be reconciled by subtraction; when weekly
                # coverage is sufficient the aggregate adds noise not signal.
                if weeks:
                    covered_frac = sum(1 for k in weeks if k in weekly_covered) / len(weeks)
                    if covered_frac >= COVERAGE_THRESHOLD:
                        continue

                # Fourier disaggregation — only fill weeks not already observed,
                # and only weeks whose Monday falls within the row's date span
                # (prevents year-boundary spillover of Jan 1 rows into Dec of
                # the preceding ISO year).
                eligible = [k for k in weeks
                            if not (src_label == "JHU" and k in weekly_covered)
                            and isoweek_bounds(*k)[0] >= r["tl"]]
                if not eligible:
                    continue

                wk_nums  = [min(w, 52) for _, w in eligible]  # clamp week 53 → 52
                weights  = template[[w - 1 for w in wk_nums]]
                wt_sum   = weights.sum()
                if wt_sum <= 0:
                    weights = np.ones(len(eligible)) / len(eligible)
                else:
                    weights = weights / wt_sum

                # Confidence scales with disaggregation window length:
                # longer windows = more uncertainty in weekly distribution
                n_elig = len(eligible)
                if n_elig <= 4:
                    conf_factor = 0.9    # monthly or shorter
                elif n_elig <= 13:
                    conf_factor = 0.8    # quarterly
                elif n_elig <= 26:
                    conf_factor = 0.7    # half-year
                else:
                    conf_factor = 0.5    # annual or multi-year

                for key, wt in zip(eligible, weights):
                    mon, sun = isoweek_bounds(*key)
                    try_insert(key, {
                        "sch":    r["sch"] * float(wt),
                        "deaths": r["deaths"] * float(wt) if r["deaths"] is not None else None,
                        "source": src_label,
                        "confidence": r["conf"] * conf_factor,
                        "method": f"fourier_{tmpl_method}",
                        "monday": mon,
                        "sunday": sun,
                    })

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

        series = process_country(iso, template_info)
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
              f"[template: {tmpl_meth}]")

    print(f"\nDone.  {len(csvs)} CSVs and {len(plots)} plots written.")
    print(f"  CSVs:  data/{{ISO}}/cholera_weekly_{{ISO}}.csv")
    print(f"  Plots: figures/dashboard/timeseries/")


if __name__ == "__main__":
    main()
