#!/usr/bin/env python3
"""
Build national-level weekly cholera time series for all 40 MOSAIC countries.

Method:
  - National rows only: Location == "AFR::{ISO}"
  - Seasonal template: Fourier K=2 fitted to year-normalised weekly medians
      * Built from ALL weekly observations (national + sub-national) to maximise signal
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
    result, seen = [], set()
    monday = week_monday(tl)
    while monday <= tr:
        key = monday.isocalendar()[:2]  # (year, week)
        if key not in seen:
            seen.add(key)
            result.append(key)
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
# Fourier K=2 template
# ---------------------------------------------------------------------------

def fit_fourier_k2(median_fracs):
    """
    Fit a K=2 Fourier series to a 52-element array of median weekly fractions.
    Returns a normalised weight array of length 52 (index 0 = week 1).
    """
    weeks = np.arange(1, 53, dtype=float)
    X = np.column_stack([
        np.ones(52),
        np.cos(2 * np.pi * weeks / 52),
        np.sin(2 * np.pi * weeks / 52),
        np.cos(4 * np.pi * weeks / 52),
        np.sin(4 * np.pi * weeks / 52),
    ])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        coeffs, _, _, _ = np.linalg.lstsq(X, median_fracs, rcond=None)
    fitted = np.maximum(X @ coeffs, 0.0)
    total  = fitted.sum()
    return fitted / total if total > 0 else np.full(52, 1 / 52)


def build_template_from_data(data_rows):
    """
    data_rows: list of (tl, tr, sch) tuples — any geographic level, sCh > 0, weekly only.
    Returns (template_52, valid_years).
    """
    cases_by_year_week = defaultdict(float)
    for tl, tr, sch in data_rows:
        if (tr - tl).days <= 7 and sch > 0:
            y, w = tl.isocalendar()[:2]
            cases_by_year_week[(y, w)] += sch

    if not cases_by_year_week:
        return np.full(52, 1 / 52), 0

    # Group by year
    by_year = defaultdict(dict)
    for (y, w), c in cases_by_year_week.items():
        by_year[y][w] = c

    fracs_by_week = defaultdict(list)
    valid_years   = 0
    for y, wk_cases in by_year.items():
        ytot = sum(wk_cases.values())
        if ytot == 0:
            continue
        valid_years += 1
        for w, c in wk_cases.items():
            fracs_by_week[w].append(c / ytot)

    median_fracs = np.zeros(52)
    for w in range(1, 53):
        vals = fracs_by_week.get(w, [])
        if vals:
            median_fracs[w - 1] = float(np.median(vals))

    return fit_fourier_k2(median_fracs), valid_years


def load_all_weekly_rows(iso, data_dir):
    """
    Load all weekly (≤7 day) non-zero rows (any geographic level) from JHU + WHO
    for template building.
    """
    rows = []
    for src in ("jhu", "who"):
        f = data_dir / f"cholera_data_{src}.csv"
        if not f.exists():
            continue
        with open(f, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
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
    Build Fourier K=2 templates for all MOSAIC countries.
    Falls back to regional pooled template for countries with < MIN_YEARS.
    Returns dict: {iso: (template_52, method_str)}
    """
    # Per-country templates
    per_country = {}
    for iso in sorted(country_map):
        d = DATA_DIR / iso
        if not d.is_dir():
            continue
        rows = load_all_weekly_rows(iso, d)
        tmpl, n_yrs = build_template_from_data(rows)
        per_country[iso] = (tmpl, n_yrs, country_map[iso].get("subregion", "Africa"))

    # Regional pooled templates (for fallback)
    regional_rows = defaultdict(list)
    for iso, (_, n_yrs, subregion) in per_country.items():
        if n_yrs >= MIN_YEARS:
            regional_rows[subregion].extend(
                load_all_weekly_rows(iso, DATA_DIR / iso)
            )

    regional_templates = {}
    for subregion, rows in regional_rows.items():
        tmpl, _ = build_template_from_data(rows)
        regional_templates[subregion] = tmpl

    # Continental fallback
    all_rows = []
    for iso in per_country:
        all_rows.extend(load_all_weekly_rows(iso, DATA_DIR / iso))
    continental, _ = build_template_from_data(all_rows)

    # Assign final templates
    templates = {}
    for iso, (tmpl, n_yrs, subregion) in per_country.items():
        if n_yrs >= MIN_YEARS:
            templates[iso] = (tmpl, "country")
        elif subregion in regional_templates:
            templates[iso] = (regional_templates[subregion], f"regional_{subregion}")
        else:
            templates[iso] = (continental, "continental")

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
            try:
                sch    = float(row.get("sCh", "") or 0)
                deaths_raw = row.get("deaths", "").strip()
                deaths = float(deaths_raw) if deaths_raw else None
                conf   = float(row.get("confidence_weight", "") or 1.0)
            except ValueError:
                sch, deaths, conf = 0.0, None, 0.9
            rows.append({"tl": tl, "tr": tr, "sch": sch,
                         "deaths": deaths, "conf": conf})
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
        # Same source: prefer observed over disaggregated; else higher sCh
        elif SOURCE_PRIORITY[entry["source"]] == SOURCE_PRIORITY[existing["source"]]:
            if entry["method"] == "observed" and existing["method"] != "observed":
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
            weeks = weeks_in_range(r["tl"], r["tr"])

            if r["sch"] == 0:
                for key in weeks:
                    if src_label == "JHU" and key in weekly_covered:
                        continue   # don't let annual zeros overwrite weekly observed
                    mon, sun = isoweek_bounds(*key)
                    try_insert(key, {
                        "sch":    0.0,
                        "deaths": 0.0,
                        "source": src_label,
                        "confidence": r["conf"],
                        "method": "zero_fill",
                        "monday": mon,
                        "sunday": sun,
                    })
            else:
                # Fourier disaggregation — skip weeks already covered by observed weekly
                eligible = [k for k in weeks
                            if not (src_label == "JHU" and k in weekly_covered)]
                if not eligible:
                    continue

                wk_nums  = [min(w, 52) for _, w in eligible]  # clamp week 53 → 52
                weights  = template[[w - 1 for w in wk_nums]]
                wt_sum   = weights.sum()
                if wt_sum <= 0:
                    weights = np.ones(len(eligible)) / len(eligible)
                else:
                    weights = weights / wt_sum

                for key, wt in zip(eligible, weights):
                    mon, sun = isoweek_bounds(*key)
                    try_insert(key, {
                        "sch":    r["sch"] * float(wt),
                        "deaths": r["deaths"] * float(wt) if r["deaths"] is not None else None,
                        "source": src_label,
                        "confidence": r["conf"] * 0.7,
                        "method": f"fourier_{tmpl_method}",
                        "monday": mon,
                        "sunday": sun,
                    })

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
    "axes.facecolor":     "#f8f9fa",
    "xtick.major.size":   4,
    "ytick.major.size":   3,
})


def plot_weekly_series(iso, series, country_name, template_method):
    if not series:
        return

    # Sort and build arrays
    items  = sorted(series.items())
    mondys = [e["monday"] for _, e in items]
    schs   = [e["sch"]    for _, e in items]
    srcs   = [e["source"] for _, e in items]
    meths  = [e["method"] for _, e in items]

    # Convert to matplotlib date numbers
    x = mdates.date2num(mondys)
    any_nonzero = any(v > 0 for v in schs)

    fig, ax = plt.subplots(figsize=(22, 4.5))
    fig.patch.set_facecolor("white")

    bar_width = 5.5   # days (slight gap between weeks)

    for xi, yi, src, meth in zip(x, schs, srcs, meths):
        is_observed = meth == "observed"
        alpha  = 0.85 if is_observed else 0.45
        color  = COLORS[src]
        ax.bar(xi, yi, width=bar_width, color=color, alpha=alpha,
               linewidth=0, align="edge")

    # X-axis: one minor tick per year, major every 5 years
    ax.xaxis.set_major_locator(mdates.YearLocator(5))
    ax.xaxis.set_minor_locator(mdates.YearLocator(1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(axis="x", which="minor", length=2, color="#aaa")
    ax.tick_params(axis="x", which="major", length=5)

    # Y-axis
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: f"{int(v):,}" if v >= 1 else ("0" if v == 0 else f"{v:.1f}")))
    ax.set_ylabel("Suspected cases / week", fontsize=10)

    if any_nonzero:
        max_val = max(schs)
        ax.set_ylim(0, max_val * 1.12)

    # Set x limits tightly
    if mondys:
        x_min = mdates.date2num(mondys[0]  - timedelta(weeks=2))
        x_max = mdates.date2num(mondys[-1] + timedelta(weeks=2))
        ax.set_xlim(x_min, x_max)

    # Title
    ax.set_title(
        f"{country_name}  ({iso})  —  Weekly Cholera Cases",
        fontsize=13, fontweight="bold", color="#222", pad=10, loc="left",
    )

    # Subtitle: data summary
    n_obs   = sum(1 for m in meths if m == "observed")
    n_disagg = sum(1 for m in meths if m != "observed" and m != "zero_fill")
    n_zero  = sum(1 for m in meths if m == "zero_fill")
    src_counts = {s: sum(1 for ss in srcs if ss == s) for s in ("JHU","WHO","AI")}
    src_parts  = [f"{s}: {n} wks" for s, n in src_counts.items() if n > 0]
    sub = (f"Observed: {n_obs}  |  Fourier disaggregated: {n_disagg}  |  "
           f"Zero-fill: {n_zero}  |  Template: {template_method}  |  "
           + "  ".join(src_parts))
    ax.text(0.01, 1.01, sub, transform=ax.transAxes,
            fontsize=8, color="#666", va="bottom")

    # Legend
    legend_items = []
    for src_label, color in COLORS.items():
        if src_counts.get(src_label, 0) > 0:
            legend_items.append(
                mpatches.Patch(facecolor=color, alpha=0.85,
                               label=f"{src_label} (observed)"))
            # Only add disaggregated patch if AI data exists and was disaggregated
            if src_label == "AI" and n_disagg > 0:
                legend_items.append(
                    mpatches.Patch(facecolor=color, alpha=0.4,
                                   label="AI (Fourier disaggregated)"))
    ax.legend(handles=legend_items, loc="upper right", fontsize=9,
              frameon=True, framealpha=0.9, edgecolor="#ddd",
              ncol=len(legend_items))

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

    n_country  = sum(1 for _, (_, m) in templates.items() if m == "country")
    n_regional = sum(1 for _, (_, m) in templates.items() if m.startswith("regional"))
    n_cont     = sum(1 for _, (_, m) in templates.items() if m == "continental")
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
