#!/usr/bin/env python3
"""Liveness heartbeat for the unattended 40-country run.

The dashboard is only rebuilt when a country *finishes*. A country takes about
four hours, so for most of the run the published dashboard is hours stale and
gives no sign that anything is alive - the run looks dead from outside even
while it is working normally. This writes a small status file every few minutes
so progress can be watched remotely between country completions.

Usage:
    python py/run_status.py                # write dashboard/run_status.{json,html}
    python py/run_status.py --publish      # ...and commit+push them
"""
import argparse
import csv
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "dashboard" / "run_status.json"
OUT_HTML = ROOT / "dashboard" / "run_status.html"
MANIFEST = ROOT / "reference" / "run_manifest.csv"

# A country with no file written for this long is not working, whatever `ps` says.
STALL_MINUTES = 45


def ps_lines():
    r = subprocess.run(["ps", "-eo", "pid,etime,args"], capture_output=True, text=True)
    return r.stdout.splitlines()


def etime_to_minutes(s):
    """ps ELAPSED is [[dd-]hh:]mm:ss."""
    days = 0
    if "-" in s:
        d, s = s.split("-", 1)
        days = int(d)
    parts = [int(p) for p in s.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, sec = parts
    return days * 1440 + h * 60 + m + sec / 60.0


def newest_file(d):
    best = None
    for p in d.rglob("*"):
        if not p.is_file() or p.name.startswith("."):
            continue
        ts = p.stat().st_mtime
        if best is None or ts > best[0]:
            best = (ts, p)
    return best


def collect():
    now = time.time()
    st = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "runner_alive": False, "runner_pid": None, "runner_elapsed_minutes": None,
        # Countries run up to PARALLEL at a time, so this is a list. The
        # singular keys below are the first entry, kept so anything reading the
        # older shape still works.
        "active": [], "current_country": None, "country_elapsed_minutes": None,
        "current_agent": None, "agent_log_age_minutes": None,
        "last_write_file": None, "last_write_age_minutes": None,
        "stalled": False, "countries_done": 0, "countries_total": 40,
        "done": [], "attempted_not_done": [],
    }

    for line in ps_lines():
        m = re.match(r"\s*(\d+)\s+(\S+)\s+(.*)$", line)
        if not m:
            continue
        pid, et, args = int(m.group(1)), m.group(2), m.group(3)
        if "run_all_countries.sh" in args and args.startswith("bash"):
            st["runner_alive"] = True
            st["runner_pid"] = pid
            st["runner_elapsed_minutes"] = round(etime_to_minutes(et), 1)
        cm = re.match(r"^claude -p ([A-Z]{3})\b", args)
        if cm:
            st["active"].append({"iso": cm.group(1),
                                 "elapsed_minutes": round(etime_to_minutes(et), 1)})

    for a in st["active"]:
        d = ROOT / "data" / a["iso"]
        a["agent"] = None
        a["last_write_file"] = None
        a["last_write_age_minutes"] = None
        if not d.is_dir():
            continue
        # Which agent is working: the most recently touched canonical log.
        best = None
        for k in range(1, 8):
            f = d / f"search_log_agent_{k}.txt"
            if f.exists() and (best is None or f.stat().st_mtime > best[0]):
                best = (f.stat().st_mtime, k)
        if best:
            a["agent"] = best[1]
        nf = newest_file(d)
        if nf:
            a["last_write_file"] = str(nf[1].relative_to(ROOT))
            a["last_write_age_minutes"] = round((now - nf[0]) / 60.0, 1)
        # A country whose process is alive but which has written nothing for
        # 45 minutes is not working, whatever `ps` says.
        a["stalled"] = bool(st["runner_alive"]
                            and a["last_write_age_minutes"] is not None
                            and a["last_write_age_minutes"] > STALL_MINUTES)

    st["active"].sort(key=lambda a: a["iso"])
    if st["active"]:
        a0 = st["active"][0]
        st["current_country"] = a0["iso"]
        st["country_elapsed_minutes"] = a0["elapsed_minutes"]
        st["current_agent"] = a0["agent"]
        st["last_write_file"] = a0["last_write_file"]
        st["last_write_age_minutes"] = a0["last_write_age_minutes"]
        st["stalled"] = any(a["stalled"] for a in st["active"])

    if MANIFEST.exists():
        last = {}
        with open(MANIFEST, newline="") as fh:
            for r in csv.DictReader(fh):
                if r.get("iso"):
                    last[r["iso"]] = r.get("status")
        st["done"] = sorted(i for i, s in last.items() if s == "done")
        st["attempted_not_done"] = sorted(i for i, s in last.items() if s != "done")
        st["countries_done"] = len(st["done"])
    return st


def html(st):
    if not st["runner_alive"]:
        badge, colour = "NOT RUNNING", "#b3261e"
    elif st["stalled"]:
        badge, colour = "POSSIBLY STALLED", "#b26a00"
    else:
        badge, colour = "RUNNING", "#1b7f3b"

    def row(k, v):
        return f"<tr><th>{k}</th><td>{v if v is not None else '&mdash;'}</td></tr>"

    def mins(v):
        return f"{v:.0f} min" if isinstance(v, (int, float)) else None

    if st["active"]:
        cells = []
        for a in st["active"]:
            flag = ' <b style="color:#b26a00">STALLED</b>' if a.get("stalled") else ""
            cells.append(
                f'<tr><td><b>{a["iso"]}</b></td>'
                f'<td>agent {a["agent"] or "-"} of 7</td>'
                f'<td>{mins(a["elapsed_minutes"])}</td>'
                f'<td><small>wrote {mins(a["last_write_age_minutes"]) or "&mdash;"} ago</small>{flag}</td></tr>')
        active_tbl = ('<table class="sub"><tr><th>Country</th><th>Progress</th>'
                      '<th>Running</th><th>Last write</th></tr>' + "".join(cells) + "</table>")
    else:
        active_tbl = "<small>none</small>"

    body = "".join([
        row("Status", f'<b style="color:{colour}">{badge}</b>'),
        row("Countries complete", f'{st["countries_done"]} of {st["countries_total"]}'
                                  f' &nbsp;<small>{", ".join(st["done"]) or "none yet"}</small>'),
        row(f'In progress ({len(st["active"])})', active_tbl),
        row("Runner uptime", mins(st["runner_elapsed_minutes"])),
        row("Heartbeat written", st["generated_at"]),
    ])
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta http-equiv="refresh" content="120">
<title>MOSAIC cholera run status</title>
<style>
 body{{font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
      margin:2.5rem auto;max-width:44rem;padding:0 1rem;color:#1a1a1a}}
 h1{{font-size:1.25rem;margin-bottom:.25rem}}
 table{{border-collapse:collapse;width:100%;margin-top:1rem}}
 th,td{{text-align:left;padding:.5rem .6rem;border-bottom:1px solid #e6e6e6;vertical-align:top}}
 th{{width:14rem;font-weight:600;color:#555}}
 small{{color:#777}} .note{{margin-top:1.4rem;color:#666;font-size:.9rem}}
 table.sub{{margin:0}} table.sub th,table.sub td{{padding:.25rem .5rem .25rem 0;
   border:0;width:auto;font-weight:400;color:#1a1a1a}}
 table.sub th{{color:#888;font-size:.8rem;text-transform:uppercase}}
</style></head><body>
<h1>MOSAIC AI cholera pipeline &mdash; run status</h1>
<div><small>Auto-refreshes every 2 minutes. Heartbeat is written every 10 minutes
while the run is active.</small></div>
<table>{body}</table>
<p class="note">A country runs seven agents and takes roughly four hours, so the
main dashboard only changes when one finishes. This page changes continuously,
and is the quickest way to tell whether the run is alive.
&nbsp;<a href="dashboard.html">Full dashboard &rarr;</a></p>
</body></html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    st = collect()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(st, indent=2) + "\n")
    OUT_HTML.write_text(html(st))

    if not a.quiet:
        who = ", ".join(f"{a['iso']} ag{a['agent'] or '-'}/7"
                        f"{' STALLED' if a.get('stalled') else ''}"
                        for a in st["active"]) or "none"
        print(f"{'RUNNING' if st['runner_alive'] else 'NOT RUNNING'}  "
              f"done={st['countries_done']}/40  active[{len(st['active'])}]: {who}")

    if a.publish:
        sys.path.insert(0, str(ROOT / "py"))
        from publish import publish
        msg = (f"Run heartbeat: {st['countries_done']}/40 complete, "
               f"active {', '.join(a['iso'] for a in st['active']) or 'none'}")
        print(publish(["dashboard/run_status.json", "dashboard/run_status.html"], msg))
    return 0


if __name__ == "__main__":
    sys.exit(main())
