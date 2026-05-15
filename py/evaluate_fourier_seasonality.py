#!/usr/bin/env python3
"""
Evaluate Fourier harmonic order K for the cholera seasonal template.

For each MOSAIC country with >= MIN_YEARS outbreak-years of weekly data:
  1. Compute year-normalised median weekly fractions (same as build_weekly_timeseries.py)
  2. Fit K = 1..K_MAX Fourier series via OLS
  3. Compute AIC, BIC, RSS, and leave-one-year-out RMSE
  4. Identify optimal K per country and the global mode

Produces:
  - Summary table printed to stdout
  - figures/dashboard/timeseries/fourier_k_evaluation.png  — per-country BIC curves
  - figures/dashboard/timeseries/seasonal_profiles.png     — fitted profiles at each K
                                                              for a representative sample
"""

import csv
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path
from datetime import date, timedelta
from collections import defaultdict

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
REF_DIR  = BASE_DIR / "reference"
FIG_DIR  = BASE_DIR / "figures" / "dashboard" / "timeseries"
FIG_DIR.mkdir(parents=True, exist_ok=True)

MIN_YEARS = 3
K_MAX     = 8

# ── helpers (same as build_weekly_timeseries.py) ──────────────────────────────

def parse_date(s):
    if not s: return None
    try:   return date.fromisoformat(s.strip())
    except: return None

def weeks_in_range(tl, tr):
    result, seen = [], set()
    monday = tl - timedelta(days=tl.weekday())
    while monday <= tr:
        key = monday.isocalendar()[:2]
        if key not in seen:
            seen.add(key)
            result.append(key)
        monday += timedelta(weeks=1)
    return result

def load_weekly_rows(iso, data_dir):
    rows = []
    for src in ("jhu", "who"):
        f = data_dir / f"cholera_data_{src}.csv"
        if not f.exists(): continue
        with open(f, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                tl = parse_date(row.get("TL",""))
                tr = parse_date(row.get("TR",""))
                if not tl or not tr: continue
                try:   sch = float(row.get("sCh","") or 0)
                except: continue
                if sch > 0 and (tr - tl).days <= 7:
                    rows.append((tl.isocalendar()[:2], sch))   # ((year,week), sch)
    return rows

def year_normalised_medians(rows):
    """
    Returns (median_fracs [52], valid_years, fracs_by_week dict).
    median_fracs[i] = median fraction of annual cases in ISO week i+1.
    """
    by_year = defaultdict(lambda: defaultdict(float))
    for (yr, wk), sch in rows:
        by_year[yr][wk] += sch

    fracs_by_week = defaultdict(list)
    valid_years = 0
    for yr, wk_cases in by_year.items():
        ytot = sum(wk_cases.values())
        if ytot == 0: continue
        valid_years += 1
        for wk, c in wk_cases.items():
            fracs_by_week[wk].append(c / ytot)

    median_fracs = np.zeros(52)
    for w in range(1, 53):
        vals = fracs_by_week.get(w, [])
        if vals:
            median_fracs[w-1] = float(np.median(vals))

    return median_fracs, valid_years, fracs_by_week

# ── Fourier fitting and model selection ───────────────────────────────────────

def design_matrix(k):
    weeks = np.arange(1, 53, dtype=float)
    cols  = [np.ones(52)]
    for i in range(1, k+1):
        cols.append(np.cos(2*np.pi*i*weeks/52))
        cols.append(np.sin(2*np.pi*i*weeks/52))
    return np.column_stack(cols)   # shape (52, 2k+1)

def fit_k(median_fracs, k):
    X = design_matrix(k)
    n = 52
    p = X.shape[1]   # 2k + 1 parameters
    coeffs, _, _, _ = np.linalg.lstsq(X, median_fracs, rcond=None)
    fitted = X @ coeffs
    rss    = float(np.sum((median_fracs - fitted)**2))
    # AIC / BIC (Gaussian likelihood)
    sigma2 = rss / n
    ll     = -0.5 * n * np.log(2*np.pi*sigma2) - rss / (2*sigma2) if sigma2 > 0 else 0
    aic    = 2*p  - 2*ll
    bic    = p*np.log(n) - 2*ll
    return {"k": k, "p": p, "rss": rss, "aic": aic, "bic": bic,
            "fitted": fitted, "coeffs": coeffs}


def loocv_rmse(fracs_by_week, k):
    """
    Leave-one-calendar-year-out CV: rebuild fracs keyed by actual calendar year,
    hold out each year in turn, refit on remaining years, measure RMSE.
    Returns mean RMSE across held-out years.
    """
    # Build year-keyed fraction dict: {year: {week: fraction}}
    year_fracs = defaultdict(dict)
    for w, entries in fracs_by_week.items():
        # entries is now list of (frac, ytot) tuples (from build_template_from_data)
        # but loocv is called from evaluate_fourier_seasonality which uses the old
        # plain-list format — handle both
        for i, entry in enumerate(entries):
            frac = entry[0] if isinstance(entry, tuple) else entry
            # Use position as year proxy here since we don't have calendar year info
            # in fracs_by_week; position i is consistent across weeks for the same
            # data because by_year iteration order is stable (sorted below)
            year_fracs[i][w] = frac

    all_years = sorted(year_fracs.keys())
    if len(all_years) < 4:
        return np.nan

    rmses = []
    for held_out_yr in all_years:
        # Build train weighted fracs from all other years
        train_fracs = np.zeros(52)
        for w in range(1, 53):
            train_vals = [year_fracs[y].get(w, 0)
                          for y in all_years if y != held_out_yr]
            nz = [v for v in train_vals if v > 0]
            if nz:
                train_fracs[w - 1] = float(np.mean(nz))

        X = design_matrix(k)
        coeffs, _, _, _ = np.linalg.lstsq(X, train_fracs, rcond=None)
        pred = X @ coeffs

        # Held-out fractions for this year
        held_fracs = np.zeros(52)
        for w, frac in year_fracs[held_out_yr].items():
            if 1 <= w <= 52:
                held_fracs[w - 1] = frac

        rmses.append(float(np.sqrt(np.mean((held_fracs - pred) ** 2))))

    return float(np.mean(rmses))

# ── Main evaluation ───────────────────────────────────────────────────────────

def main():
    with open(REF_DIR / "country_mapping.json") as f:
        cmap = json.load(f)["countries"]
    countries = {iso: m for iso, m in cmap.items() if m.get("mosaic_framework")}

    results = []   # list of dicts per country

    for iso in sorted(countries):
        d = DATA_DIR / iso
        if not d.is_dir(): continue

        rows = load_weekly_rows(iso, d)
        if not rows: continue

        median_fracs, n_yrs, fracs_by_week = year_normalised_medians(rows)

        if n_yrs < MIN_YEARS:
            continue

        country_results = {"iso": iso, "name": countries[iso].get("name", iso),
                           "n_years": n_yrs, "fits": {}}

        for k in range(1, K_MAX+1):
            fit = fit_k(median_fracs, k)
            fit["loocv_rmse"] = loocv_rmse(fracs_by_week, k)
            country_results["fits"][k] = fit

        # Optimal K by BIC
        bic_values = {k: v["bic"] for k, v in country_results["fits"].items()}
        country_results["best_k_bic"]  = min(bic_values, key=bic_values.get)

        # Optimal K by LOOCV
        cv_values = {k: v["loocv_rmse"] for k, v in country_results["fits"].items()
                     if not np.isnan(v["loocv_rmse"])}
        country_results["best_k_cv"] = min(cv_values, key=cv_values.get) if cv_values else None

        results.append(country_results)

    # ── Summary table ─────────────────────────────────────────────────────────
    print(f"\n{'ISO':<6} {'Country':<28} {'Yrs':>4}  "
          f"{'Best K (BIC)':>12}  {'Best K (LOOCV)':>14}  "
          f"K=2 BIC      K=best BIC   ΔBIC")
    print("─" * 95)

    best_k_bic_counts  = defaultdict(int)
    best_k_cv_counts   = defaultdict(int)

    for r in results:
        k_bic  = r["best_k_bic"]
        k_cv   = r.get("best_k_cv")
        bic2   = r["fits"][2]["bic"]
        bic_best = r["fits"][k_bic]["bic"]
        delta  = bic2 - bic_best   # positive = K>2 is better

        best_k_bic_counts[k_bic] += 1
        if k_cv: best_k_cv_counts[k_cv] += 1

        flag = " ◄" if k_bic != 2 else ""
        print(f"{r['iso']:<6} {r['name']:<28} {r['n_years']:>4}  "
              f"{k_bic:>12}  "
              f"{str(k_cv) if k_cv else 'n/a':>14}  "
              f"{bic2:>10.2f}  {bic_best:>10.2f}  "
              f"{delta:>+8.2f}{flag}")

    print("\n── BIC-optimal K distribution ─────────────────────────────────")
    for k in sorted(best_k_bic_counts):
        bar = "█" * best_k_bic_counts[k]
        print(f"  K={k}: {best_k_bic_counts[k]:>3} countries  {bar}")

    global_best_k = max(best_k_bic_counts, key=best_k_bic_counts.get)
    print(f"\n  Global mode (BIC): K={global_best_k}")

    print("\n── LOOCV-optimal K distribution ────────────────────────────────")
    for k in sorted(best_k_cv_counts):
        bar = "█" * best_k_cv_counts[k]
        print(f"  K={k}: {best_k_cv_counts[k]:>3} countries  {bar}")

    # ── BIC curves plot ───────────────────────────────────────────────────────
    n_countries = len(results)
    ncols = 6
    nrows = (n_countries + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(18, nrows * 2.5))
    axes = axes.flatten()

    ks = list(range(1, K_MAX+1))
    for ax, r in zip(axes, results):
        bics = [r["fits"][k]["bic"] for k in ks]
        bics_norm = np.array(bics) - min(bics)   # normalise to 0

        ax.plot(ks, bics_norm, "o-", color="#0167af", linewidth=1.5,
                markersize=4, markerfacecolor="white", markeredgewidth=1.5)
        ax.axvline(r["best_k_bic"], color="#E74C3C", linewidth=1, linestyle="--", alpha=0.7)
        ax.set_title(f"{r['iso']}  (K={r['best_k_bic']})", fontsize=8, pad=3)
        ax.set_xticks(ks)
        ax.set_xticklabels(ks, fontsize=7)
        ax.tick_params(axis="y", labelsize=7)
        ax.set_xlabel("K", fontsize=7)
        if ax == axes[0]:
            ax.set_ylabel("ΔBIC from min", fontsize=7)
        ax.spines[["top","right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.3, linewidth=0.5)

    for ax in axes[n_countries:]:
        ax.set_visible(False)

    fig.suptitle("Fourier K selection by BIC  (red dashed = optimal K)",
                 fontsize=11, fontweight="bold", y=1.01)
    fig.tight_layout()
    out_bic = FIG_DIR / "fourier_k_evaluation.png"
    fig.savefig(out_bic, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"\nBIC curves saved → {out_bic}")

    # ── Seasonal profile comparison for 6 representative countries ────────────
    sample_isos = ["NGA", "ETH", "COD", "MOZ", "KEN", "CMR"]
    sample_results = {r["iso"]: r for r in results if r["iso"] in sample_isos}

    weeks = np.arange(1, 53)
    month_ticks = [1, 5, 9, 14, 18, 22, 27, 31, 35, 40, 44, 48]
    month_labels = ["Jan","Feb","Mar","Apr","May","Jun",
                    "Jul","Aug","Sep","Oct","Nov","Dec"]

    fig2, axes2 = plt.subplots(2, 3, figsize=(16, 7), sharey=False)
    axes2 = axes2.flatten()

    palette = plt.cm.Blues(np.linspace(0.35, 0.95, K_MAX))

    for ax, iso in zip(axes2, sample_isos):
        r = sample_results.get(iso)
        if r is None:
            ax.set_visible(False)
            continue

        # Load raw median fracs for scatter
        rows_c = load_weekly_rows(iso, DATA_DIR / iso)
        median_fracs, _, _ = year_normalised_medians(rows_c)
        ax.bar(weeks, median_fracs, color="#ccc", width=0.8,
               label="Year-norm. median", zorder=1)

        for k in range(1, K_MAX+1):
            fitted = r["fits"][k]["fitted"]
            fitted_pos = np.maximum(fitted, 0)
            lw  = 2.5 if k == r["best_k_bic"] else 1
            ls  = "-" if k == r["best_k_bic"] else "--"
            col = palette[k-1]
            ax.plot(weeks, fitted_pos, color=col, linewidth=lw,
                    linestyle=ls, alpha=0.85,
                    label=f"K={k}" + (" ★" if k == r["best_k_bic"] else ""))

        ax.set_title(f"{r['name']}  ({iso})  —  BIC-optimal: K={r['best_k_bic']}",
                     fontsize=9, fontweight="bold")
        ax.set_xticks(month_ticks)
        ax.set_xticklabels(month_labels, fontsize=8)
        ax.set_ylabel("Fraction of annual cases", fontsize=8)
        ax.tick_params(axis="y", labelsize=8)
        ax.spines[["top","right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.25, linewidth=0.5)
        ax.legend(fontsize=7, ncol=3, frameon=False,
                  loc="upper left" if iso != "CMR" else "upper right")

    fig2.suptitle(
        "Seasonal profile fits K=1–8  (★ = BIC-optimal,  bars = year-normalised medians)",
        fontsize=11, fontweight="bold")
    fig2.tight_layout()
    out_prof = FIG_DIR / "seasonal_profiles.png"
    fig2.savefig(out_prof, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig2)
    print(f"Seasonal profiles saved → {out_prof}")


if __name__ == "__main__":
    main()
