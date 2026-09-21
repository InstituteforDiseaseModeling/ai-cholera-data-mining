#!/usr/bin/env python3
"""Build the country run-status table.

Writes two things from one shared fragment:
  dashboard/country_status.html   standalone page
  dashboard/dashboard.html        injected between the COUNTRY-STATUS markers

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
OUT_PAGE = ROOT / "dashboard" / "country_status.html"
DASHBOARD = ROOT / "dashboard" / "dashboard.html"
MARK_START = "<!-- COUNTRY-STATUS:START -->"
MARK_END = "<!-- COUNTRY-STATUS:END -->"

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


def collect():
    cmap = json.loads((ROOT / "reference" / "country_mapping.json").read_text())["countries"]
    mosaic = sorted(k for k, v in cmap.items() if v.get("mosaic_framework"))

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

    rec = {r["iso_code"]: r for r in
           read_csv(ROOT / "reference" / "effective_surveillance_recency.csv")}
    active = active_countries()

    starts = [r.get("started") for r in manifest if r.get("started")]
    cycle_start = None
    if starts:
        try:
            cycle_start = datetime.strptime(min(starts), "%Y-%m-%d %H:%M:%S").timestamp()
        except ValueError:
            cycle_start = None

    rows = []
    for iso in mosaic:
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
        rows.append({
            "iso": iso, "name": cmap[iso].get("name", iso),
            "state": state, "cls": cls, "qual": qual, "qcls": qcls,
            "flags": flags, "n_agents": n_now,
            "last_run": when, "delta": delta,
            "last_obs": r.get("latest_observation", ""),
            "last_positive": r.get("latest_positive_observation", ""),
            "obs": count_rows(ROOT / "data" / iso / "cholera_data_ai.csv"),
            "sources": count_rows(ROOT / "data" / iso / "metadata_ai.csv"),
            "span": f"{lo}–{hi}" if lo else "",
        })
    return rows


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


def standalone_page(rows):
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
<footer>
Generated {datetime.now(timezone.utc).astimezone():%Y-%m-%d %H:%M %Z} &middot;
<a href="dashboard.html">Full dashboard</a> &middot;
<a href="run_status.html">Live run status</a> &middot;
<a href="https://github.com/InstituteforDiseaseModeling/ai-cholera-data-mining">Source and data</a>
</footer>
</div></body></html>
"""


def inject(frag):
    """Replace the marked region of the production dashboard."""
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
    if new == html:
        print("  dashboard unchanged")
        return False
    tmp = DASHBOARD.with_suffix(".tmp")
    tmp.write_text(new)
    tmp.replace(DASHBOARD)
    print(f"  injected into {DASHBOARD.relative_to(ROOT)}")
    return True


def main():
    rows = collect()
    frag = fragment(rows)
    OUT_PAGE.parent.mkdir(parents=True, exist_ok=True)
    OUT_PAGE.write_text(standalone_page(rows))
    print(f"Wrote {OUT_PAGE.relative_to(ROOT)}  ({len(rows)} countries)")
    inject(frag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
