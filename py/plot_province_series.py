#!/usr/bin/env python3
"""
Summary figures for the province (ADM1) weekly series (py/build_province_weekly.py).

  figures/province/province_coverage_overview.png
      province-weeks per country by evidence type, ranked
  figures/province/province_vs_national_annual.png
      annual sum of provinces vs the national series, per country-year
  figures/province/countries/province_series_{ISO}.png
      per country: national weekly series; province x week cases (log scale);
      province x week evidence type (reported / spread from a multi-week total /
      zero / missing)

Usage: python py/plot_province_series.py [--data-root DIR] [--iso ISO ...]
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.dates as mdates  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import ListedColormap, LinearSegmentedColormap, BoundaryNorm  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
FIG = BASE / "figures" / "province"

# Reference palette (dataviz skill): categorical slots 1-2, neutral grays for
# zero/absent, single-hue blue sequential ramp for magnitude.
SURFACE = "#fcfcfb"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
C_OBS, C_SPREAD = "#2a78d6", "#eb6834"
C_SPREAD_LONG = "#f5b393"   # same hue as C_SPREAD, lighter step: sub-category of "spread"
C_ZERO, C_INFZ, C_MISS = "#9e9c95", "#d9d7d1", "#ffffff"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "font.size": 9, "axes.titlesize": 11, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False,
})


LONG_DAYS = 731   # spreads from totals longer than this are shown hatched


def kind(m, s, span=0):
    """Evidence category of one province-week."""
    if m == "inferred_zero":
        return "inferred_zero"
    if m.startswith("fourier"):   # a spread week can be 0 where the template weight is 0
        return "spread_long" if span > LONG_DAYS else "spread"
    if s == 0:
        return "zero"
    return "observed"


def load(data_root, iso):
    p = data_root / iso / f"cholera_adm1_weekly_{iso}.csv"
    if not p.exists():
        return None
    w = pd.read_csv(p, keep_default_na=False)
    if w.empty:
        return w
    w["sCh"] = pd.to_numeric(w["sCh"], errors="coerce").fillna(0.0)
    span = pd.to_numeric(w.get("source_span_days", 0), errors="coerce").fillna(0)
    w["kind"] = [kind(m, s, d) for m, s, d in zip(w.disaggregation_method, w.sCh, span)]
    w["week_start"] = pd.to_datetime(w.week_start)
    return w


def overview(frames, units, names):
    rows = []
    for iso in sorted(units):
        w = frames.get(iso)
        c = w.kind.value_counts() if w is not None and len(w) else pd.Series(dtype=int)
        n_with = w.adm1_name.nunique() if w is not None and len(w) else 0
        rows.append({"iso": iso, "observed": c.get("observed", 0), "spread": c.get("spread", 0),
                     "spread_long": c.get("spread_long", 0),
                     "zero": c.get("zero", 0), "n_with": n_with, "units": units[iso]})
    d = pd.DataFrame(rows)
    d["pos"] = d.observed + d.spread + d.spread_long
    d = d.sort_values(["observed", "pos"], ascending=True).reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(10, 11))
    y = np.arange(len(d))
    left = np.zeros(len(d))
    for col, color, hatch, label in (
            ("observed", C_OBS, None, "Reported weekly cases (positive)"),
            ("spread", C_SPREAD, None, "Spread from a reported total of up to 2 years"),
            ("spread_long", C_SPREAD, "////", "Spread from a reported total longer than 2 years"),
            ("zero", C_ZERO, None, "Reported or documented zero")):
        ax.barh(y, d[col], left=left, height=0.72, color=color, label=label, hatch=hatch,
                edgecolor=SURFACE, linewidth=1)
        left += d[col].values
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r.iso}  {names.get(r.iso, '')}" for r in d.itertuples()], fontsize=8)
    xmax = left.max()
    for yi, r in zip(y, d.itertuples()):
        ax.text(left[yi] + xmax * 0.01, yi, f"{r.n_with}/{r.units} provinces", va="center",
                fontsize=7, color=INK2)
    ax.set_xlim(0, xmax * 1.18)
    ax.set_xlabel("Province-weeks")
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_title("Province-level weekly cholera series: province-weeks by evidence type",
                 loc="left", pad=24)
    ax.text(0, 1.012, "Ranked by reported positive province-weeks. Label: provinces with any "
            "data / current provinces.", transform=ax.transAxes, fontsize=8, color=INK2)
    ax.legend(loc="lower right", frameon=False, fontsize=8)
    out = FIG / "province_coverage_overview.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out, d


def reconciliation(frames, data_root):
    pts = []
    for iso, w in frames.items():
        if w is None or not len(w):
            continue
        nat_p = BASE / "data" / iso / f"cholera_weekly_{iso}.csv"
        if not nat_p.exists():
            continue
        nat = pd.read_csv(nat_p)
        nat = nat[nat.disaggregation_method != "inferred_zero"]
        prov = w[w.kind != "inferred_zero"]
        a = nat.groupby("year").sCh.sum()
        b = prov.groupby("year").sCh.sum()
        j = pd.concat([a.rename("nat"), b.rename("prov")], axis=1).dropna()
        j = j[(j.nat > 0) & (j.prov > 0)]
        for yr, r in j.iterrows():
            pts.append((iso, yr, r.nat, r.prov))
    d = pd.DataFrame(pts, columns=["iso", "year", "nat", "prov"])
    d["ratio"] = d.prov / d.nat
    fig, ax = plt.subplots(figsize=(7.5, 7))
    ax.scatter(d.nat, d.prov, s=14, color=C_OBS, alpha=0.55, edgecolor=SURFACE, linewidth=0.5)
    lo, hi = 1, max(d.nat.max(), d.prov.max()) * 1.5
    ax.plot([lo, hi], [lo, hi], color=INK2, linewidth=1, linestyle="--")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel("National series, cases per year")
    ax.set_ylabel("Sum of provinces, cases per year")
    ax.grid(color=GRID, linewidth=0.5)
    within = d.ratio.between(0.8, 1.25).mean()
    ax.set_title("Province sums vs national series, per country-year", loc="left", pad=24)
    ax.text(0, 1.015, f"{len(d)} country-years with both > 0; {within:.0%} within 0.8-1.25x; "
            f"median ratio {d.ratio.median():.2f}. Dashed: equality.",
            transform=ax.transAxes, fontsize=8, color=INK2)
    big = d[(d.nat > 2000) & (d.ratio < 0.1)].nlargest(5, "nat")
    for k, r in enumerate(big.sort_values("prov").itertuples()):
        ax.annotate(f"{r.iso} {r.year}", (r.nat, r.prov), fontsize=7, color=INK2,
                    xytext=(-50, -14 - 4 * k), textcoords="offset points",
                    arrowprops={"arrowstyle": "-", "color": GRID, "linewidth": 0.6})
    out = FIG / "province_vs_national_annual.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out, d


def country_figure(iso, name, w, unit_list, data_root):
    if w is None or not len(w):
        return None
    w = w[w.week_start.dt.year >= 1970]
    t0 = w.week_start.min() - pd.Timedelta(weeks=26)
    t1 = w.week_start.max() + pd.Timedelta(weeks=26)
    weeks = pd.date_range(t0 - pd.Timedelta(days=t0.weekday()), t1, freq="W-MON")
    col = {d: i for i, d in enumerate(weeks)}
    with_data = w.groupby("adm1_name").sCh.sum().sort_values(ascending=False)
    units = list(with_data.index) + sorted(u for u in unit_list if u not in with_data.index)
    row = {u: i for i, u in enumerate(units)}

    val = np.full((len(units), len(weeks)), np.nan)
    kd = np.zeros((len(units), len(weeks)), dtype=int)   # 0 missing
    code = {"observed": 1, "spread": 2, "spread_long": 5, "zero": 3, "inferred_zero": 4}
    for r in w.itertuples():
        j = col.get(r.week_start)
        if j is None:
            continue
        i = row[r.adm1_name]
        kd[i, j] = code[r.kind]
        val[i, j] = r.sCh if r.kind != "inferred_zero" else np.nan

    nat_p = BASE / "data" / iso / f"cholera_weekly_{iso}.csv"
    nat = pd.read_csv(nat_p, parse_dates=["week_start"]) if nat_p.exists() else None

    h = max(3.0, 0.16 * len(units))
    fig = plt.figure(figsize=(14, 1.6 + 2 * h + 1.0))
    gs = fig.add_gridspec(3, 2, height_ratios=[1.6, h, h], width_ratios=[80, 1],
                          hspace=0.12, wspace=0.015)
    a0 = fig.add_subplot(gs[0, 0])
    a1 = fig.add_subplot(gs[1, 0], sharex=a0)
    a2 = fig.add_subplot(gs[2, 0], sharex=a0)
    cax = fig.add_subplot(gs[1, 1])
    for ax in (a0, a1):
        ax.tick_params(labelbottom=False)
    extent = [mdates.date2num(weeks[0]), mdates.date2num(weeks[-1] + pd.Timedelta(days=7)),
              len(units), 0]

    if nat is not None:
        n = nat[(nat.week_start >= weeks[0]) & (nat.week_start <= weeks[-1])]
        n = n[n.disaggregation_method != "inferred_zero"]
        a0.fill_between(n.week_start, n.sCh, step="post", color=INK2, alpha=0.35, linewidth=0)
        a0.step(n.week_start, n.sCh, where="post", color=INK2, linewidth=0.6)
    a0.set_ylabel("National\ncases / week")
    a0.grid(axis="y", color=GRID, linewidth=0.5)
    a0.set_title(f"{name} ({iso}): province-level weekly cholera series", loc="left")

    # cases, log scale; zero = gray, missing = white
    bounds = [0.5, 3, 10, 30, 100, 300, 1000, 3000, 1e9]
    cmap = ListedColormap(SEQ + [SEQ[-1]])
    shown = np.where(val > 0, val, np.nan)
    a1.imshow(np.where(kd == 0, 1, np.nan), aspect="auto", extent=extent,
              cmap=ListedColormap([C_MISS]), interpolation="nearest")
    a1.imshow(np.where((kd == 3), 1, np.nan), aspect="auto", extent=extent,
              cmap=ListedColormap([GRID]), interpolation="nearest")
    im = a1.imshow(shown, aspect="auto", extent=extent, cmap=cmap,
                   norm=BoundaryNorm(bounds, cmap.N), interpolation="nearest")
    a1.set_yticks(np.arange(len(units)) + 0.5)
    a1.set_yticklabels(units, fontsize=7)
    cb = fig.colorbar(im, cax=cax, ticks=bounds[:-1])
    cb.ax.set_yticklabels(["1", "3", "10", "30", "100", "300", "1k", "3k+"], fontsize=7)
    cb.set_label("Cases / week", fontsize=8, color=INK2)
    cb.outline.set_visible(False)
    a1.set_ylabel("Cases")

    kcmap = ListedColormap([C_MISS, C_OBS, C_SPREAD, C_ZERO, C_INFZ, C_SPREAD_LONG])
    a2.imshow(kd, aspect="auto", extent=extent, cmap=kcmap, vmin=-0.5, vmax=5.5,
              interpolation="nearest")
    a2.set_yticks(np.arange(len(units)) + 0.5)
    a2.set_yticklabels(units, fontsize=7)
    a2.set_ylabel("Evidence")
    a2.legend(handles=[Patch(color=C_OBS, label="Reported weekly count"),
                       Patch(color=C_SPREAD, label="Spread from reported total (up to 2 yr)"),
                       Patch(color=C_SPREAD_LONG, label="Spread from reported total (> 2 yr)"),
                       Patch(color=C_ZERO, label="Reported or documented zero"),
                       Patch(color=C_INFZ, label="Inferred zero (read as missing)"),
                       Patch(facecolor=C_MISS, edgecolor=GRID, label="No province data")],
              loc="upper center", bbox_to_anchor=(0.5, -0.06 - 0.25 / h), ncol=6,
              frameon=False, fontsize=8)
    for ax in (a1, a2):
        ax.set_xlim(extent[0], extent[1])
        for i in range(len(units) + 1):
            ax.axhline(i, color=SURFACE, linewidth=0.4)
    a2.xaxis.set_major_locator(mdates.YearLocator(5 if (t1 - t0).days > 365 * 15 else 1))
    a2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    out = FIG / "countries" / f"province_series_{iso}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=170, bbox_inches="tight")
    plt.close(fig)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=str(BASE / "data"))
    ap.add_argument("--ref-dir", default=str(BASE / "reference" / "subnational"))
    ap.add_argument("--iso", nargs="+")
    ap.add_argument("--fig-dir", help="write figures here instead of figures/province")
    args = ap.parse_args()
    global FIG
    if args.fig_dir:
        FIG = Path(args.fig_dir)
    data_root = Path(args.data_root)
    units = pd.read_csv(Path(args.ref_dir) / "adm1_units.csv")
    unit_lists = units.groupby("iso").adm1_name.apply(list).to_dict()
    cmap = json.load(open(BASE / "reference" / "country_mapping.json"))["countries"]
    names = {k: v["name"] for k, v in cmap.items()}
    isos = args.iso or sorted(k for k, v in cmap.items() if v.get("mosaic_framework"))
    FIG.mkdir(parents=True, exist_ok=True)

    frames = {iso: load(data_root, iso) for iso in isos}
    if not args.iso:
        o, _ = overview(frames, {i: len(unit_lists.get(i, [])) for i in isos}, names)
        print(f"  {o}")
        r, d = reconciliation(frames, data_root)
        print(f"  {r}  ({len(d)} country-years)")
    for iso in isos:
        p = country_figure(iso, names.get(iso, iso), frames[iso], unit_lists.get(iso, []), data_root)
        if p:
            print(f"  {p}")


if __name__ == "__main__":
    main()
