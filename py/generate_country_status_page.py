#!/usr/bin/env python3
"""Build the country run-status table.

Writes two things from one shared fragment:
  dashboard/country_status.html   standalone page
  dashboard/dashboard.html        injected between the COUNTRY-STATUS markers

and, below it in both, a separate "Pilot countries" section (between the
PILOT-COUNTRIES markers in the dashboard) for countries outside the 40 that
were processed because they were named (reference/pipeline_countries.json,
pilot=true; currently Nepal). Both country sets come from py/scope.py:
mosaic_isos() for the table and every total, pilot_isos() for the pilot
section. Nothing iterates over data/* directories, so a pilot's files can
never enter the 40-country table or its totals.

The table answers one question: what has the pipeline done to each country?
Data-quality questions (how much of a series is a real measurement rather than a
model fill) belong on a separate evidence page, not here.

It replaces the `status` column of dashboard/completion_checklist.csv, which was
derived from whether a country's output files exist. Every country has files
from an earlier pipeline run, so that column read COMPLETED for all 40 while the
current re-run had finished four.

Sources:
  reference/run_manifest.csv                        run state, timings, deltas
  data/{ISO}/search_log_agent_{1..7}.txt            which agents actually ran
  data/{ISO}/search_report.txt                      evidence of a full pass
  reference/effective_surveillance_recency.csv      last observation / positive
  data/{ISO}/cholera_data_ai.csv, metadata_ai.csv   current data description

Everything is scoped under .cs-wrap and prefixed cs- so the fragment cannot
disturb the production dashboard's own styles or scripts.

Usage:
    python py/generate_country_status_page.py
"""

import csv
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "py"))
import scope  # noqa: E402  (mosaic_isos() for the table, pilot_isos() for the pilot section)
from stamp_figure_versions import pilot_figure_version  # noqa: E402

OUT_PAGE = ROOT / "dashboard" / "country_status.html"
DASHBOARD = ROOT / "dashboard" / "dashboard.html"
MARK_START = "<!-- COUNTRY-STATUS:START -->"
MARK_END = "<!-- COUNTRY-STATUS:END -->"
PILOT_START = "<!-- PILOT-COUNTRIES:START -->"
PILOT_END = "<!-- PILOT-COUNTRIES:END -->"
PILOT_REF = ROOT / "reference" / "pilot"

AGENT_NAMES = {
    1: "Baseline collection",
    2: "Geographic expansion",
    3: "Zero-transmission validation",
    4: "Obscure sources",
    5: "Cross-reference integration",
    6: "Gap context",
    7: "Quality audit",
}

QUAL_ORDER = {"running now": 0, "refreshed this cycle": 1, "awaiting refresh": 3}

DOT_NOTE = {"now": "ran in the current refresh",
            "prev": "ran in an earlier cycle",
            "never": "has never run"}

# (header, sort type, tooltip, extra css class)
# The tooltips replace a glossary at the foot of the page: a reader who wonders
# what a column means looks at the column, not at prose several screens below.
COLUMNS = [
    ("ISO", "text", "ISO 3166-1 alpha-3 country code.", ""),
    ("Country", "text",
     "The 40 MOSAIC framework countries. Data collection is restricted to "
     "these; no others are processed.", ""),
    ("Pipeline state", "num",
     "<b>Complete</b> means all seven agents have run for this country and it "
     "passed its validation gate — true of all 40. The line beneath "
     "describes the current refresh cycle: <i>running now</i>, <i>refreshed "
     "this cycle</i>, <i>refreshing, n of 7</i> (interrupted part-way; "
     "everything collected is kept and it resumes rather than restarting), or "
     "<i>awaiting refresh</i> (not yet revisited, existing data stands). "
     "Sorts by refresh progress, not alphabetically.", ""),
    ("Agents run", "num",
     "The seven search agents in order. <b>Green</b> ran in the current "
     "refresh; <b>grey</b> ran in an earlier cycle, so the work exists but is "
     "not recent; <b>outline</b> has never run. Hover a square for that "
     "agent's role.", ""),
    ("Last run", "text",
     "When the pipeline last finished working on this country, and in green "
     "the number of observations that run added. Where a country has not been "
     "revisited in the current cycle this is the date of its previous full "
     "pass, which has no recorded delta.", ""),
    ("Last observation", "text",
     "End date of the most recent observation on file, from any source. Hover "
     "a value for the most recent observation that reported at least one "
     "<i>case</i> — the two can be years apart, because a recent record of "
     "absence makes a country look current when nothing positive has been "
     "measured for a long time.", "cs-tip-right"),
    ("Current data", "num",
     "Observations and distinct cited sources now held in the AI layer, and "
     "the period they span. This is the AI enhancement only; it sits alongside "
     "the JHU and WHO baseline data rather than replacing it. Sorts by "
     "observation count.", "cs-tip-right"),
]

FRAGMENT_CSS = """
<style>
.cs-wrap { font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
           color:#1a1a1a; }
.cs-wrap .cs-intro { color:#6b6b6b; margin:0 0 .4rem; font-size:.95rem; }
.cs-wrap .cs-hint { color:#6b6b6b; font-size:.83rem; margin:.9rem 0 0; }
.cs-wrap table.cs-table { border-collapse:collapse; width:100%; font-size:.9rem;
                          margin-top:.7rem; background:none; }
.cs-wrap .cs-table th, .cs-wrap .cs-table td {
    padding:.42rem .5rem; border-bottom:1px solid #e6e6e6; text-align:left;
    white-space:nowrap; background:none; }
.cs-wrap .cs-table th {
    font-size:.74rem; text-transform:uppercase; letter-spacing:.03em;
    color:#6b6b6b; font-weight:600; position:relative; cursor:pointer;
    -webkit-user-select:none; user-select:none; border-bottom:1px solid #d5d5d5; }
.cs-wrap .cs-table th:hover .cs-lbl { color:#1a1a1a; }
.cs-wrap .cs-arw { margin-left:.25rem; font-size:.7rem; }
/* Hover box on the heading, in place of a glossary at the foot of the page. */
.cs-wrap .cs-tip {
    display:none; position:absolute; top:100%; left:0; z-index:60;
    width:19rem; margin-top:.3rem; padding:.6rem .7rem;
    background:#1f2430; color:#f2f2f2; border-radius:6px;
    font-size:.79rem; font-weight:400; line-height:1.45;
    text-transform:none; letter-spacing:0; white-space:normal;
    box-shadow:0 8px 22px rgba(0,0,0,.22); }
.cs-wrap .cs-tip.cs-tip-right { left:auto; right:0; }
.cs-wrap .cs-tip b { color:#fff; }
.cs-wrap .cs-table th:hover .cs-tip { display:block; }
.cs-wrap .cs-iso { font-weight:600; }
.cs-wrap .cs-dt { color:#6b6b6b; font-variant-numeric:tabular-nums; font-size:.86rem; }
.cs-wrap .cs-desc { font-size:.86rem; }
.cs-wrap .cs-delta { color:#12602c; font-weight:600; }
.cs-wrap .cs-table th .cs-delta { text-transform:none; letter-spacing:0; }
.cs-wrap .cs-pill { display:inline-block; padding:.05rem .45rem; border-radius:10px;
                    font-size:.78rem; }
.cs-wrap .cs-pill.ok   { background:#e7f4ec; color:#12602c; }
.cs-wrap .cs-pill.run  { background:#e7eefb; color:#15407f; }
.cs-wrap .cs-pill.warn { background:#fdf1e2; color:#8a5200; }
.cs-wrap .cs-pill.wait { background:#f2f2f2; color:#555; }
.cs-wrap .cs-qual { display:block; font-size:.74rem; margin-top:.1rem; }
.cs-wrap .cs-qual.ok { color:#12602c; } .cs-wrap .cs-qual.run { color:#15407f; }
.cs-wrap .cs-qual.warn { color:#8a5200; } .cs-wrap .cs-qual.wait { color:#6b6b6b; }
.cs-wrap .cs-dots { display:inline-flex; gap:2px; }
.cs-wrap .cs-dots i { width:16px; height:16px; border-radius:3px; font-style:normal;
                      font-size:.68rem; line-height:16px; text-align:center;
                      cursor:default; }
.cs-wrap .cs-dots i.now   { background:#1b7f3b; color:#fff; }
.cs-wrap .cs-dots i.prev  { background:#d8d8d8; color:#6b6b6b; }
.cs-wrap .cs-dots i.never { background:#fff; color:#c8c8c8;
                            box-shadow:inset 0 0 0 1px #e6e6e6; }
</style>
"""

# Bound to .cs-table only, so it cannot interfere with the dashboard's own
# sortTable(). Values come from each cell's data-sort attribute, so display
# formatting (green deltas, agent squares, "n of 7") never affects ordering.
# Without JS the table still renders in its default order: running, then
# refreshed, then partially refreshed, then awaiting.
SCRIPT = """
<script>
(function () {
  document.querySelectorAll('.cs-table thead th').forEach(function (th) {
    th.addEventListener('click', function () {
      var head = th.parentNode, tb = th.closest('table').tBodies[0];
      var idx = Array.prototype.indexOf.call(head.children, th);
      var num = th.dataset.type === 'num';
      var asc = th.dataset.dir !== 'asc';
      Array.prototype.forEach.call(head.children, function (o) {
        o.removeAttribute('data-dir');
        var a = o.querySelector('.cs-arw'); if (a) a.textContent = '';
      });
      th.dataset.dir = asc ? 'asc' : 'desc';
      var arw = th.querySelector('.cs-arw');
      if (arw) arw.textContent = asc ? '\\u25B2' : '\\u25BC';
      var rows = Array.prototype.slice.call(tb.rows);
      rows.sort(function (a, b) {
        var x = a.cells[idx].getAttribute('data-sort') || '';
        var y = b.cells[idx].getAttribute('data-sort') || '';
        if (num) { return asc ? (parseFloat(x) || 0) - (parseFloat(y) || 0)
                              : (parseFloat(y) || 0) - (parseFloat(x) || 0); }
        return asc ? x.localeCompare(y) : y.localeCompare(x);
      });
      rows.forEach(function (r) { tb.appendChild(r); });
    });
  });
})();
</script>
"""


# --------------------------------------------------------------- collection --

def read_csv(path):
    p = Path(path)
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def count_rows(path):
    return len(read_csv(path))


def agents_run(iso, cycle_start):
    """State of each of the seven agents: 'now' | 'prev' | 'never'.

    Measured against the start of the current re-run cycle, not the country's
    last manifest row. When the account spend limit is exhausted the runner is
    refused in about three seconds per country, which still writes a manifest
    row; measuring from that row reported zero agents for countries that had in
    fact completed five before being cut off.

    'prev' means the log exists from an earlier cycle. All 40 countries have all
    seven, so an empty row would mislead - the work is there, just not recent.

    Legacy renames (search_log_agent_N_legacy_*.txt) keep their old mtime, so
    matching the exact canonical name means seven distinct agents must each have
    run, not that seven files of some kind exist.
    """
    out = []
    for k in range(1, 8):
        f = ROOT / "data" / iso / f"search_log_agent_{k}.txt"
        if not f.exists():
            out.append("never")
        elif cycle_start and f.stat().st_mtime > cycle_start:
            out.append("now")
        else:
            out.append("prev")
    return out


def last_full_pass(iso):
    """When this country last had a complete seven-agent pass, from its files."""
    d = ROOT / "data" / iso
    stamps = [(d / f"search_log_agent_{k}.txt").stat().st_mtime
              for k in range(1, 8) if (d / f"search_log_agent_{k}.txt").exists()]
    rep = d / "search_report.txt"
    if rep.exists():
        stamps.append(rep.stat().st_mtime)
    if len(stamps) < 8:                      # not a full set plus a report
        return None
    return datetime.fromtimestamp(max(stamps))


def data_span(iso):
    rows = read_csv(ROOT / "data" / iso / "cholera_data_ai.csv")
    yrs = [r["TL"][:4] for r in rows if (r.get("TL") or "")[:4].isdigit()]
    yrs += [r["TR"][:4] for r in rows if (r.get("TR") or "")[:4].isdigit()]
    return (min(yrs), max(yrs)) if yrs else ("", "")


def active_countries():
    try:
        ps = subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True).stdout
    except Exception:
        return set()
    out = set()
    for line in ps.splitlines():
        parts = line.split()
        if len(parts) > 2 and line.startswith("claude -p ") \
           and len(parts[2]) == 3 and parts[2].isupper():
            out.add(parts[2])
    return out


def run_context():
    """Manifest-derived state shared by the MOSAIC table and the pilot section."""
    manifest = read_csv(ROOT / "reference" / "run_manifest.csv")
    run, productive = {}, {}
    for r in manifest:
        iso = r.get("iso")
        if not iso:
            continue
        run[iso] = r                         # last row per country wins
        # "Last run" must mean a run that did something. An exhausted spend
        # limit refuses each country in about three seconds and still writes a
        # manifest row; showing that makes an untouched country look freshly
        # processed.
        try:
            moved = int(r.get("rows_after") or 0) != int(r.get("rows_before") or 0)
        except ValueError:
            moved = False
        if r.get("status") == "done" or moved:
            productive[iso] = r

    starts = [r.get("started") for r in manifest if r.get("started")]
    cycle_start = None
    if starts:
        try:
            cycle_start = datetime.strptime(min(starts), "%Y-%m-%d %H:%M:%S").timestamp()
        except ValueError:
            cycle_start = None
    return {"run": run, "productive": productive, "active": active_countries(),
            "cycle_start": cycle_start}


def status_row(iso, name, ctx, rec):
    """One country's pipeline state, agents, last run and AI-layer description."""
    run, productive = ctx["run"], ctx["productive"]
    active, cycle_start = ctx["active"], ctx["cycle_start"]
    st = run.get(iso, {})
    flags = agents_run(iso, cycle_start)
    n_now = sum(1 for f in flags if f == "now")
    had_full = last_full_pass(iso) is not None

    # The state describes the DATA and the qualifier the refresh. Calling a
    # country "Queued" implied it had never been processed, which was wrong
    # for all 40 of them.
    if had_full:
        state, cls = "Complete", "ok"
    elif n_now:
        state, cls = "In progress", "warn"
    else:
        state, cls = "Not yet processed", "wait"

    if iso in active:
        qual, qcls = "running now", "run"
    elif n_now >= 7:
        qual, qcls = "refreshed this cycle", "ok"
    elif n_now:
        qual, qcls = f"refreshing, {n_now} of 7", "warn"
    else:
        qual, qcls = "awaiting refresh", "wait"

    last = productive.get(iso, {})
    try:
        delta = int(last.get("rows_after") or 0) - int(last.get("rows_before") or 0)
    except ValueError:
        delta = 0

    when = (last.get("finished") or "")[:16]
    if not when:
        lfp = last_full_pass(iso)
        when = lfp.strftime("%Y-%m-%d") if lfp else ""
        delta = 0

    lo, hi = data_span(iso)
    r = rec.get(iso, {}) or {}
    return {
        "iso": iso, "name": name,
        "state": state, "cls": cls, "qual": qual, "qcls": qcls,
        "flags": flags, "n_agents": n_now,
        "last_run": when, "delta": delta,
        "last_obs": r.get("latest_observation", ""),
        "last_positive": r.get("latest_positive_observation", ""),
        "obs": count_rows(ROOT / "data" / iso / "cholera_data_ai.csv"),
        "sources": count_rows(ROOT / "data" / iso / "metadata_ai.csv"),
        "span": f"{lo}–{hi}" if lo else "",
        "manifest_status": st.get("status", ""),
    }

def collect():
    """The 40 MOSAIC countries (scope.mosaic_isos()); pilots never appear here."""
    cmap = json.loads((ROOT / "reference" / "country_mapping.json").read_text())["countries"]
    ctx = run_context()
    rec = {r["iso_code"]: r for r in
           read_csv(ROOT / "reference" / "effective_surveillance_recency.csv")}
    return [status_row(iso, cmap[iso].get("name", iso), ctx, rec) for iso in scope.mosaic_isos()]


def weekly_counts(iso):
    """Weeks in a pilot's typed series: (suspected observed, suspected
    undistributed, confirmed observed), from data/{ISO}/cholera_weekly_*.csv."""
    s = read_csv(ROOT / "data" / iso / f"cholera_weekly_{iso}.csv")
    c = read_csv(ROOT / "data" / iso / f"cholera_weekly_confirmed_{iso}.csv")
    meth = [r.get("disaggregation_method", "") for r in s]
    return (sum(1 for m in meth if m == "observed"),
            sum(1 for m in meth if m == "undistributed"),
            sum(1 for r in c if r.get("disaggregation_method", "observed") == "observed"))


def collect_pilots():
    """Pilot countries that have been processed (data/{ISO}/ exists), from
    scope.pilot_isos(). Coverage and recency come from reference/pilot/, which
    analyze_effective_gaps.py writes for pilots instead of the shared files."""
    ctx = run_context()
    rec = {r["iso_code"]: r for r in read_csv(PILOT_REF / "effective_surveillance_recency.csv")}
    cov = {r["iso_code"]: r for r in read_csv(PILOT_REF / "effective_surveillance_gaps_coverage.csv")}
    out = []
    for iso in scope.pilot_isos():
        d = ROOT / "data" / iso
        if not d.is_dir():
            continue
        r = status_row(iso, scope.country_name(iso), ctx, rec)
        # A finished manifest row outranks a matching process: the session that
        # finishes a pilot also publishes the page, so it is still alive then.
        if r["manifest_status"] == "done" and r["qual"] == "running now":
            r["qual"], r["qcls"] = ("refreshed this cycle", "ok") if r["n_agents"] >= 7 \
                else (f"refreshing, {r['n_agents']} of 7", "warn")
        meta = scope.country_meta(iso)
        fig = ROOT / "figures" / "pilot" / iso / f"cholera_timeseries_{iso}.png"
        r.update({
            "subregion": meta.get("subregion", ""),
            "prefix": scope.location_prefix(iso),
            "tag": scope.pilot_tag(iso) or "",
            "presence": count_rows(d / "cholera_presence_ai.csv"),
            "coverage": cov.get(iso, {}),
            "weeks": weekly_counts(iso),
            "figure": f"../figures/pilot/{iso}/{fig.name}" if fig.exists() else "",
            "report": (d / "search_report.txt").exists(),
        })
        out.append(r)
    return out


# ------------------------------------------------------------------ render --

def sort_key(r):
    return (QUAL_ORDER.get(r["qual"], 2), -r["n_agents"], r["iso"])


def state_rank(r):
    """Numeric sort value for the pipeline-state column.

    Alphabetical order there is meaningless - every row begins "Complete" - so
    it sorts on refresh progress instead.
    """
    return QUAL_ORDER.get(r["qual"], 2) * 10 + (7 - r["n_agents"])


def agent_dots(flags):
    out = [f'<i class="{s}" title="Agent {i}: {AGENT_NAMES[i]} &mdash; {DOT_NOTE[s]}">'
           f'{i}</i>' for i, s in enumerate(flags, start=1)]
    return f'<span class="cs-dots">{"".join(out)}</span>'


def fragment(rows):
    """The self-contained table: css, intro, table, script."""
    n_ref = sum(1 for r in rows if r["qual"] == "refreshed this cycle")
    n_part = sum(1 for r in rows if r["qual"].startswith("refreshing"))
    n_wait = sum(1 for r in rows if r["qual"] == "awaiting refresh")
    tot_obs = sum(r["obs"] for r in rows)
    tot_src = sum(r["sources"] for r in rows)

    head = []
    for label, typ, tip, extra in COLUMNS:
        suffix = (' <span class="cs-delta">(obs. added)</span>'
                  if label == "Last run" else "")
        head.append(f'<th data-type="{typ}"><span class="cs-lbl">{label}{suffix}'
                    f'<span class="cs-arw"></span></span>'
                    f'<span class="cs-tip {extra}">{tip}</span></th>')

    body = []
    for r in sorted(rows, key=sort_key):
        delta = (f'<small class="cs-delta" title="observations added by that run">'
                 f'+{r["delta"]:,}</small>' if r["delta"] > 0 else "")
        desc = (f'{r["obs"]:,} observations &middot; {r["sources"]:,} sources'
                + (f' &middot; {r["span"]}' if r["span"] else ""))
        pos = (f' title="most recent observation reporting at least one case: '
               f'{r["last_positive"]}"' if r["last_positive"] else "")
        body.append(
            f'<tr>'
            f'<td class="cs-iso" data-sort="{r["iso"]}">{r["iso"]}</td>'
            f'<td data-sort="{r["name"]}">{r["name"]}</td>'
            f'<td data-sort="{state_rank(r)}">'
            f'<span class="cs-pill {r["cls"]}">{r["state"]}</span>'
            f'<small class="cs-qual {r["qcls"]}">{r["qual"]}</small></td>'
            f'<td data-sort="{r["n_agents"]}">{agent_dots(r["flags"])}</td>'
            f'<td class="cs-dt" data-sort="{r["last_run"]}">'
            f'{r["last_run"] or "&mdash;"} {delta}</td>'
            f'<td class="cs-dt" data-sort="{r["last_obs"]}"{pos}>'
            f'{r["last_obs"] or "&mdash;"}</td>'
            f'<td class="cs-desc" data-sort="{r["obs"]}">{desc}</td>'
            f'</tr>')

    return f"""<div class="cs-wrap">
{FRAGMENT_CSS}
<p class="cs-intro">All 40 countries have completed a full seven-agent pass. The
current cycle is re-running them one at a time to add recent data and revisit
historical sources; the qualifier beside each state shows how far that has got.
<b>{n_ref} refreshed, {n_part} in progress, {n_wait} awaiting refresh</b>
&mdash; {tot_obs:,} observations from {tot_src:,} sources in total.</p>
<p class="cs-hint">Hover a column heading for what it means. Click to sort.</p>
<table class="cs-table">
<thead><tr>{"".join(head)}</tr></thead>
<tbody>
{chr(10).join(body)}
</tbody></table>
{SCRIPT}
</div>"""


PILOT_CSS = """
<style>
.cs-wrap.cs-pilot { margin-top:2.4rem; padding-top:1.1rem; border-top:2px solid #e6e6e6; }
.cs-wrap .cs-pilot-h { font-size:1.15rem; margin:0 0 .4rem; }
.cs-wrap .cs-badge-pilot { display:inline-block; padding:.08rem .5rem; border-radius:10px;
    font-size:.7rem; font-weight:700; letter-spacing:.06em; vertical-align:middle;
    background:#efe5fb; color:#55288a; }
.cs-wrap .cs-pilot-note { border-left:3px solid #8a5cc2; background:#f9f5fe;
    padding:.6rem .85rem; margin:.5rem 0 .9rem; font-size:.88rem; }
.cs-wrap .cs-pilot-table th { cursor:default; }
.cs-wrap .cs-pilot-table td { white-space:normal; vertical-align:top; }
.cs-wrap .cs-pilot-sub { display:block; color:#6b6b6b; font-size:.78rem; }
.cs-wrap .cs-pilot-fig { margin:1rem 0 0; }
.cs-wrap .cs-pilot-fig img { max-width:100%; height:auto; border:1px solid #e6e6e6; }
.cs-wrap .cs-pilot-fig figcaption { color:#6b6b6b; font-size:.83rem; margin-top:.35rem; }
</style>
"""


def pilot_fragment(prows, pversion=None):
    """The separate "Pilot countries" section.

    Pilot rows use class cs-pilot-iso, never cs-iso, so py/validate_dashboard.py
    counts the 40 MOSAIC rows and the pilot rows apart. The figure URL carries
    the pilot figure stamp (py/stamp_figure_versions.py), separate from the
    40 countries' stamp.
    """
    if pversion is None:
        pversion = pilot_figure_version()
    codes = ", ".join(f"{r['prefix']}::{r['iso']}" for r in prows)
    head = "".join(f"<th>{h}</th>" for h in
                   ("ISO", "Country", "Pipeline state", "Agents run", "Last run",
                    "Current data", "Coverage", "Weekly series"))
    body, figs = [], []
    for r in prows:
        c = r["coverage"]
        cov = (f'{float(c.get("percent_coverage") or 0):.1f}% of months '
               f'({c.get("months_with_data", "")}/{c.get("total_months", "")})'
               f'<small class="cs-pilot-sub">{c.get("gap_periods", "")} gap period(s); '
               f'{c.get("months_ai_only", "")} months from the AI layer alone</small>'
               if c else "&mdash;")
        so, su, co = r["weeks"]
        weeks = (f'suspected: {so:,} observed + {su:,} undistributed wks'
                 f'<small class="cs-pilot-sub">confirmed: {co:,} observed wks</small>')
        delta = (f' <small class="cs-delta" title="observations added by that run">'
                 f'+{r["delta"]:,}</small>' if r["delta"] > 0 else "")
        desc = (f'{r["obs"]:,} observations &middot; {r["sources"]:,} sources'
                + (f' &middot; {r["span"]}' if r["span"] else "")
                + f'<small class="cs-pilot-sub">{r["presence"]:,} presence-only records '
                  f'(cholera reported, no count); no zero rows</small>')
        body.append(
            f'<tr>'
            f'<td class="cs-pilot-iso" data-sort="{r["iso"]}">{r["iso"]} '
            f'<span class="cs-badge-pilot">PILOT</span></td>'
            f'<td>{r["name"]}<small class="cs-pilot-sub">{r["subregion"]} &middot; '
            f'{r["prefix"]}::{r["iso"]}</small></td>'
            f'<td><span class="cs-pill {r["cls"]}">{r["state"]}</span>'
            f'<small class="cs-qual {r["qcls"]}">{r["qual"]}</small></td>'
            f'<td>{agent_dots(r["flags"])}</td>'
            f'<td class="cs-dt">{r["last_run"] or "&mdash;"}{delta}</td>'
            f'<td class="cs-desc">{desc}</td>'
            f'<td class="cs-desc">{cov}</td>'
            f'<td class="cs-desc">{weeks}</td>'
            f'</tr>')
        iso = r["iso"]
        links = ([f'<a href="../data/{iso}/search_report.txt">audit report</a>'] if r["report"] else []) + [
            f'<a href="../data/{iso}/cholera_data_ai.csv">AI observations</a>',
            f'<a href="../data/{iso}/metadata_ai.csv">sources</a>',
            f'<a href="../data/{iso}/cholera_weekly_{iso}.csv">suspected weekly series</a>',
            f'<a href="../data/{iso}/cholera_weekly_confirmed_{iso}.csv">confirmed weekly series</a>',
            f'<a href="../data/{iso}/cholera_period_totals_{iso}.csv">period totals</a>']
        if r["figure"]:
            figs.append(
                f'<figure class="cs-pilot-fig">'
                f'<img src="{r["figure"]}?v={pversion}" loading="lazy" '
                f'alt="{r["name"]} weekly cholera series, pilot: suspected and laboratory-confirmed panels">'
                f'<figcaption><b>{r["name"]} ({iso}), pilot.</b> Top: suspected cases per ISO week '
                f'(observed weeks as bars; multi-week totals shown as undistributed bands rather than '
                f'spread across weeks). Bottom: laboratory-confirmed cases per week. Weeks without data '
                f'are left empty. {" &middot; ".join(links)}</figcaption></figure>')
        else:
            figs.append(f'<p class="cs-hint">{" &middot; ".join(links)}</p>')
    table = (f'<table class="cs-table cs-pilot-table">\n<thead><tr>{head}</tr></thead>\n'
             f'<tbody>\n{chr(10).join(body)}\n</tbody></table>') if body else \
        '<p class="cs-hint">No pilot country has been processed.</p>'
    where = f" ({codes})" if codes else ""
    return f"""<div class="cs-wrap cs-pilot">
{PILOT_CSS}
<h3 class="cs-pilot-h">Pilot countries <span class="cs-badge-pilot">PILOT</span></h3>
<div class="cs-pilot-note"><b>Outside the 40 MOSAIC framework countries.</b> Pilot countries
are processed only when named explicitly, to test whether the pipeline generalises beyond
Africa. They are excluded from every 40-country table, figure, total and coverage statistic
on this dashboard, and MOSAIC-pkg does not read them. Locations use the country's WHO region
prefix{where}, not AFR::. The weekly series uses only rows whose count type is documented
(reference/count_basis/), keeps suspected and laboratory-confirmed cases in separate series,
has no zero rows, and leaves multi-week totals undistributed. Coverage counts any
observation, including years held out of the typed series. Not yet suitable for modelling.</div>
{table}
{chr(10).join(figs)}
</div>"""


def standalone_page(rows, pilot_html=""):
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Country status &mdash; AI cholera surveillance enhancement</title>
<style>
 body {{ font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
        color:#1a1a1a; margin:0; padding:2rem 1.25rem 4rem; }}
 .page {{ max-width:1000px; margin:0 auto; }}
 h1 {{ font-size:1.45rem; margin:0 0 .3rem; }}
 .lede {{ color:#6b6b6b; margin:0 0 1rem; }}
 .caveat {{ border-left:3px solid #d9a03c; background:#fdf8ef; padding:.65rem .9rem;
           margin:1rem 0 1.4rem; font-size:.9rem; }}
 footer {{ margin-top:2.2rem; padding-top:.9rem; border-top:1px solid #e6e6e6;
          color:#6b6b6b; font-size:.85rem; }}
 a {{ color:#15407f; }}
</style></head><body><div class="page">
<h1>Country status</h1>
<p class="lede">Progress of the AI-assisted enhancement of JHU/WHO cholera
surveillance data across the 40 MOSAIC framework countries.</p>
<div class="caveat"><b>This is an experimental pilot.</b> The AI-generated data
have not been fully validated by human experts and may change as methods are
refined. Verify independently before use.</div>
{fragment(rows)}
{pilot_html}
<footer>
Generated {datetime.now(timezone.utc).astimezone():%Y-%m-%d %H:%M %Z} &middot;
<a href="dashboard.html">Full dashboard</a> &middot;
<a href="run_status.html">Live run status</a> &middot;
<a href="https://github.com/InstituteforDiseaseModeling/ai-cholera-data-mining">Source and data</a>
</footer>
</div></body></html>
"""


def live_stats():
    """Figures the dashboard used to hard-code, computed from the data.

    Every one of these was wrong on the published site: average coverage was
    stated as 57.2% against an actual 81.5%, and the AI layer's contribution as
    3.1% against an actual 23.7% of country-months - an eightfold
    understatement of the project's own result. They are computed here so they
    cannot drift again.
    """
    eff = read_csv(ROOT / "reference" / "effective_surveillance_gaps_coverage.csv")
    base = read_csv(ROOT / "reference" / "baseline_surveillance_gaps_coverage.csv")
    fnum = lambda r, k: float(r.get(k) or 0)
    inum = lambda r, k: int(r.get(k) or 0)

    s = {}
    if eff:
        n = len(eff)
        tot = sum(inum(r, "total_months") for r in eff) or 1
        s["eff_coverage"] = f'{sum(fnum(r, "percent_coverage") for r in eff) / n:.1f}%'
        s["jhu_share"] = f'{100 * sum(inum(r, "months_jhu") for r in eff) / tot:.1f}%'
        s["who_share"] = f'{100 * sum(inum(r, "months_who") for r in eff) / tot:.1f}%'
        s["ai_share"] = f'{100 * sum(inum(r, "months_ai") for r in eff) / tot:.1f}%'
        s["ai_only_share"] = f'{100 * sum(inum(r, "months_ai_only") for r in eff) / tot:.1f}%'
        s["gt50"] = str(sum(1 for r in eff if fnum(r, "percent_coverage") > 50))
        s["gt75"] = str(sum(1 for r in eff if fnum(r, "percent_coverage") > 75))
        s["zero_cov"] = str(sum(1 for r in eff if fnum(r, "percent_coverage") == 0))
        s["top5"] = "".join(
            f"<li>{r['country']} ({r['iso_code']}): {fnum(r, 'percent_coverage'):.1f}%</li>"
            for r in sorted(eff, key=lambda r: -fnum(r, "percent_coverage"))[:5])
        ago = [r for r in eff if r["iso_code"] == "AGO"]
        if ago:
            s["ago_coverage"] = f'{fnum(ago[0], "percent_coverage"):.1f}%'
    if base:
        m = sum(fnum(r, "percent_coverage") for r in base) / len(base)
        s["baseline_coverage"] = f"{m:.1f}%"
        s["baseline_missing"] = f"{100 - m:.1f}%"
        s["baseline_zero_cov"] = str(
            sum(1 for r in base if fnum(r, "percent_coverage") == 0))

    # WHO baseline extent, so "2023-2025" cannot go stale again.
    # The 40 MOSAIC countries only (scope.mosaic_isos()), not every data/* dir.
    lo, hi = "9999", "0000"
    for iso in scope.mosaic_isos():
        f = ROOT / "data" / iso / "cholera_data_who.csv"
        if not f.exists():
            continue
        for r in read_csv(f):
            for k in ("TL", "TR"):
                v = (r.get(k) or "")[:10]
                if len(v) == 10:
                    lo, hi = min(lo, v), max(hi, v)
    if lo != "9999":
        s["who_range"] = f"{lo[:4]}–{hi[:4]}"

    s["source_count"] = str(sum(
        1 for line in (ROOT / "reference" / "priority_sources.txt").read_text().splitlines()
        if line[:1].isalnum()))
    s["generated"] = f"{datetime.now(timezone.utc).astimezone():%Y-%m-%d %H:%M %Z}"
    return s


def patch_stats(html, stats):
    """Replace <!--STAT:key-->...<!--/STAT--> spans with computed values."""
    out, n = html, 0
    for key, val in stats.items():
        a, b = f"<!--STAT:{key}-->", "<!--/STAT-->"
        i = 0
        while True:
            i = out.find(a, i)
            if i < 0:
                break
            j = out.find(b, i)
            if j < 0:
                break
            out = out[:i + len(a)] + val + out[j:]
            i = i + len(a) + len(val) + len(b)
            n += 1
    return out, n


def inject(frag, pilot_html=None):
    """Replace the marked regions of the production dashboard: the country
    table (COUNTRY-STATUS) and the pilot section (PILOT-COUNTRIES, created
    directly below the table on first use)."""
    if not DASHBOARD.exists():
        print(f"  skipped: {DASHBOARD.relative_to(ROOT)} not found")
        return False
    html = DASHBOARD.read_text()
    if MARK_START not in html or MARK_END not in html:
        print(f"  skipped: markers not found in {DASHBOARD.relative_to(ROOT)}; "
              f"add {MARK_START} / {MARK_END} around the table")
        return False
    # Plain string splice, not re.sub: the fragment's script contains "▲",
    # which re.sub parses as a replacement-template escape and rejects with
    # "bad escape \u".
    i = html.index(MARK_START)
    j = html.index(MARK_END, i) + len(MARK_END)
    new = html[:i] + MARK_START + "\n" + frag + "\n" + MARK_END + html[j:]
    if pilot_html is not None:
        block = PILOT_START + "\n" + pilot_html + "\n" + PILOT_END
        if PILOT_START in new and PILOT_END in new:
            i = new.index(PILOT_START)
            j = new.index(PILOT_END, i) + len(PILOT_END)
            new = new[:i] + block + new[j:]
        else:
            k = new.index(MARK_END) + len(MARK_END)
            new = new[:k] + "\n" + block + new[k:]

    stats = live_stats()
    new, n_stats = patch_stats(new, stats)

    if new == html:
        print("  dashboard unchanged")
        return False
    tmp = DASHBOARD.with_suffix(".tmp")
    tmp.write_text(new)
    tmp.replace(DASHBOARD)
    print(f"  injected into {DASHBOARD.relative_to(ROOT)}  "
          f"({n_stats} computed figures patched)")
    return True


def main():
    rows = collect()
    prows = collect_pilots()
    frag = fragment(rows)
    pilot_html = pilot_fragment(prows, pilot_figure_version())
    OUT_PAGE.parent.mkdir(parents=True, exist_ok=True)
    OUT_PAGE.write_text(standalone_page(rows, pilot_html))
    print(f"Wrote {OUT_PAGE.relative_to(ROOT)}  ({len(rows)} countries, "
          f"{len(prows)} pilot: {' '.join(r['iso'] for r in prows) or 'none'})")
    inject(frag, pilot_html)
    return 0


if __name__ == "__main__":
    sys.exit(main())
