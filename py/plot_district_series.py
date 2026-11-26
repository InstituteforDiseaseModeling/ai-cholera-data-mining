#!/usr/bin/env python3
"""
Summary figures for the district (ADM2) weekly series (py/build_district_weekly.py).

  figures/district/district_coverage_overview.png
      district-weeks per country by evidence type, ranked
  figures/district/district_vs_province_annual.png
      annual sum of districts vs the province series, per province-year
  figures/district/countries/district_series_{ISO}.png
      per country: district x week cases (log scale) and evidence type, districts
      grouped by province; districts with no positive week are left out, and at
      most MAX_ROWS districts (by cases) are drawn

Usage: python py/plot_district_series.py [--data-root DIR] [--ref-dir DIR] [--iso ISO ...]
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plot_province_series as pps  # noqa: E402  (palette, rcParams, kind())
import build_district_weekly as bdw  # noqa: E402  (LOCAL_ONLY)

plt = pps.plt
mdates = pps.mdates
BASE = pps.BASE
FIG = BASE / "figures" / "district"
MAX_ROWS = 150


def load(data_root, iso):
    p = data_root / iso / f"cholera_adm2_weekly_{iso}.csv"
    if not p.exists():
        return None
    w = pd.read_csv(p, keep_default_na=False)
    if w.empty:
        return w
    w["sCh"] = pd.to_numeric(w["sCh"], errors="coerce").fillna(0.0)
    span = pd.to_numeric(w["source_span_days"], errors="coerce").fillna(0)
    w["kind"] = [pps.kind(m, s, d) for m, s, d in zip(w.disaggregation_method, w.sCh, span)]
    w["week_start"] = pd.to_datetime(w.week_start)
    return w


def overview(frames, n_units, names):
    rows = []
    for iso, w in frames.items():
        c = w.kind.value_counts() if w is not None and len(w) else pd.Series(dtype=int)
        with_pos = w[w.sCh > 0].adm2_name.nunique() if w is not None and len(w) else 0
        rows.append({"iso": iso, "observed": c.get("observed", 0), "spread": c.get("spread", 0),
                     "spread_long": c.get("spread_long", 0), "zero": c.get("zero", 0),
                     "with_pos": with_pos, "units": n_units.get(iso, 0)})
    d = pd.DataFrame(rows)
    d["pos"] = d.observed + d.spread + d.spread_long
    d = d.sort_values(["observed", "pos"]).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(10, max(6, 0.28 * len(d) + 2)))
    y = np.arange(len(d))
    left = np.zeros(len(d))
    for col, color, hatch, label in (
            ("observed", pps.C_OBS, None, "Reported weekly cases (positive)"),
            ("spread", pps.C_SPREAD, None, "Spread from a reported total of up to 2 years"),
            ("spread_long", pps.C_SPREAD, "////", "Spread from a reported total longer than 2 years"),
            ("zero", pps.C_ZERO, None, "Reported, documented or area-wide zero")):
        ax.barh(y, d[col], left=left, height=0.72, color=color, label=label, hatch=hatch,
                edgecolor=pps.SURFACE, linewidth=1)
        left += d[col].values
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r.iso}  {names.get(r.iso, '')}" for r in d.itertuples()], fontsize=8)
    xmax = max(left.max(), 1)
    for yi, r in zip(y, d.itertuples()):
        ax.text(left[yi] + xmax * 0.01, yi, f"{r.with_pos}/{r.units} districts with cases",
                va="center", fontsize=7, color=pps.INK2)
    ax.set_xlim(0, xmax * 1.25)
    ax.set_xlabel("District-weeks")
    ax.grid(axis="x", color=pps.GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_title("District-level weekly cholera series: district-weeks by evidence type",
                 loc="left", pad=24)
    ax.text(0, 1.012, "Ranked by reported positive district-weeks. DRC is province-level only; "
            "Kenya (local-only line-list data) is not shown.",
            transform=ax.transAxes, fontsize=8, color=pps.INK2)
    ax.legend(loc="lower right", frameon=False, fontsize=8)
    out = FIG / "district_coverage_overview.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out


def versus_province(frames):
    pts = []
    for iso, w in frames.items():
        if w is None or not len(w):
            continue
        pp = BASE / "data" / iso / f"cholera_adm1_weekly_{iso}.csv"
        if not pp.exists():
            continue
        p = pd.read_csv(pp)
        p = p[p.disaggregation_method != "inferred_zero"]
        a = p.groupby(["adm1_name", "year"]).sCh.sum()
        b = w[w.kind != "inferred_zero"].groupby(["adm1_name", "year"]).sCh.sum()
        j = pd.concat([a.rename("prov"), b.rename("dist")], axis=1).dropna()
        j = j[(j.prov > 0) & (j.dist > 0)]
        pts += [(iso, *k, r.prov, r.dist) for k, r in j.iterrows()]
    d = pd.DataFrame(pts, columns=["iso", "adm1", "year", "prov", "dist"])
    d["ratio"] = d.dist / d.prov
    fig, ax = plt.subplots(figsize=(7.5, 7))
    ax.scatter(d.prov, d.dist, s=12, color=pps.C_OBS, alpha=0.5, edgecolor=pps.SURFACE, linewidth=0.5)
    hi = max(d.prov.max(), d.dist.max()) * 1.5
    ax.plot([1, hi], [1, hi], color=pps.INK2, linewidth=1, linestyle="--")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(1, hi)
    ax.set_ylim(1, hi)
    ax.set_xlabel("Province series, cases per year")
    ax.set_ylabel("Sum of districts, cases per year")
    ax.grid(color=pps.GRID, linewidth=0.5)
    ax.set_title("District sums vs province series, per province-year", loc="left", pad=24)
    ax.text(0, 1.015, f"{len(d)} province-years with both > 0; "
            f"{d.ratio.between(0.8, 1.25).mean():.0%} within 0.8-1.25x; median ratio "
            f"{d.ratio.median():.2f}. Dashed: equality.", transform=ax.transAxes, fontsize=8,
            color=pps.INK2)
    out = FIG / "district_vs_province_annual.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out


def country_figure(iso, name, w):
    if w is None or not len(w):
        return None
    w = w[w.week_start.dt.year >= 1970]
    tot = w[w.kind != "inferred_zero"].groupby(["adm1_name", "adm2_name"]).sCh.sum()
    tot = tot[tot > 0]
    if tot.empty:
        return None
    n_all = len(tot)
    tot = tot.nlargest(MAX_ROWS)
    order = sorted(tot.index, key=lambda k: (-tot.groupby(level=0).sum()[k[0]], k[0], -tot[k]))
    row = {k: i for i, k in enumerate(order)}
    w = w[[(a, b) in row for a, b in zip(w.adm1_name, w.adm2_name)]]
    t0 = w.week_start.min() - pd.Timedelta(weeks=26)
    t1 = w.week_start.max() + pd.Timedelta(weeks=26)
    weeks = pd.date_range(t0 - pd.Timedelta(days=t0.weekday()), t1, freq="W-MON")
    col = {d: i for i, d in enumerate(weeks)}
    val = np.full((len(order), len(weeks)), np.nan)
    kd = np.zeros((len(order), len(weeks)), dtype=int)
    code = {"observed": 1, "spread": 2, "spread_long": 5, "zero": 3, "inferred_zero": 4}
    for r in w.itertuples():
        j = col.get(r.week_start)
        if j is None:
            continue
        i = row[(r.adm1_name, r.adm2_name)]
        kd[i, j] = code[r.kind]
        val[i, j] = r.sCh if r.kind != "inferred_zero" else np.nan
    h = max(3.0, 0.11 * len(order))
    fig = plt.figure(figsize=(14, 2 * h + 1.2))
    gs = fig.add_gridspec(2, 2, height_ratios=[h, h], width_ratios=[80, 1], hspace=0.08, wspace=0.015)
    a1 = fig.add_subplot(gs[0, 0])
    a2 = fig.add_subplot(gs[1, 0], sharex=a1)
    cax = fig.add_subplot(gs[0, 1])
    a1.tick_params(labelbottom=False)
    extent = [mdates.date2num(weeks[0]), mdates.date2num(weeks[-1] + pd.Timedelta(days=7)), len(order), 0]
    bounds = [0.5, 3, 10, 30, 100, 300, 1000, 3000, 1e9]
    cmap = pps.ListedColormap(pps.SEQ + [pps.SEQ[-1]])
    a1.imshow(np.where(kd == 3, 1, np.nan), aspect="auto", extent=extent,
              cmap=pps.ListedColormap([pps.GRID]), interpolation="nearest")
    im = a1.imshow(np.where(val > 0, val, np.nan), aspect="auto", extent=extent, cmap=cmap,
                   norm=pps.BoundaryNorm(bounds, cmap.N), interpolation="nearest")
    cb = fig.colorbar(im, cax=cax, ticks=bounds[:-1])
    cb.ax.set_yticklabels(["1", "3", "10", "30", "100", "300", "1k", "3k+"], fontsize=7)
    cb.set_label("Cases / week", fontsize=8, color=pps.INK2)
    cb.outline.set_visible(False)
    kcmap = pps.ListedColormap([pps.C_MISS, pps.C_OBS, pps.C_SPREAD, pps.C_ZERO, pps.C_INFZ, pps.C_SPREAD_LONG])
    a2.imshow(kd, aspect="auto", extent=extent, cmap=kcmap, vmin=-0.5, vmax=5.5, interpolation="nearest")
    labels = [f"{b}  ({a})" for a, b in order]
    fs = 6 if len(order) <= 60 else 4.5
    for ax, lab in ((a1, "Cases"), (a2, "Evidence")):
        ax.set_yticks(np.arange(len(order)) + 0.5)
        ax.set_yticklabels(labels, fontsize=fs)
        ax.set_ylabel(lab)
        ax.set_xlim(extent[0], extent[1])
        prev = None
        for i, (a, _) in enumerate(order):   # province separators
            if prev is not None and a != prev:
                ax.axhline(i, color=pps.INK2, linewidth=0.6)
            prev = a
    sub = f" ({len(order)} of {n_all} districts with cases, by cases)" if n_all > len(order) else ""
    a1.set_title(f"{name} ({iso}): district-level weekly cholera series{sub}", loc="left")
    a2.legend(handles=[pps.Patch(color=pps.C_OBS, label="Reported weekly count"),
                       pps.Patch(color=pps.C_SPREAD, label="Spread from reported total (up to 2 yr)"),
                       pps.Patch(color=pps.C_SPREAD_LONG, label="Spread from reported total (> 2 yr)"),
                       pps.Patch(color=pps.C_ZERO, label="Reported, documented or area-wide zero"),
                       pps.Patch(color=pps.C_INFZ, label="Inferred zero (read as missing)"),
                       pps.Patch(facecolor=pps.C_MISS, edgecolor=pps.GRID, label="No district data")],
              loc="upper center", bbox_to_anchor=(0.5, -0.04 - 0.25 / h), ncol=6, frameon=False, fontsize=8)
    a2.xaxis.set_major_locator(mdates.YearLocator(5 if (t1 - t0).days > 365 * 15 else 1))
    a2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    out = FIG / "countries" / f"district_series_{iso}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=170, bbox_inches="tight")
    plt.close(fig)
    return out


def main():
    global FIG
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=str(BASE / "data"))
    ap.add_argument("--ref-dir", default=str(BASE / "reference" / "subnational"))
    ap.add_argument("--iso", nargs="+")
    ap.add_argument("--fig-dir")
    args = ap.parse_args()
    if args.fig_dir:
        FIG = Path(args.fig_dir)
    FIG.mkdir(parents=True, exist_ok=True)
    units = pd.read_csv(Path(args.ref_dir) / "adm2_units.csv", keep_default_na=False)
    n_units = units.groupby("iso").size().to_dict()
    names = {k: v["name"] for k, v in json.load(open(BASE / "reference" / "country_mapping.json"))["countries"].items()}
    isos = args.iso or sorted(n_units)
    frames = {iso: load(Path(args.data_root), iso) for iso in isos}
    frames = {k: v for k, v in frames.items() if v is not None}
    if not args.iso:
        # Shared figures never include local-only countries (KEN line list).
        shared = {k: v for k, v in frames.items() if k not in bdw.LOCAL_ONLY}
        print(f"  {overview(shared, n_units, names)}")
        print(f"  {versus_province(shared)}")
    for iso in frames:
        p = country_figure(iso, names.get(iso, iso), frames[iso])
        if p:
            print(f"  {p}")


if __name__ == "__main__":
    main()
