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
        "current_country": None, "country_elapsed_minutes": None,
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
            st["current_country"] = cm.group(1)
            st["country_elapsed_minutes"] = round(etime_to_minutes(et), 1)

    iso = st["current_country"]
    if iso:
        d = ROOT / "data" / iso
        if d.is_dir():
            # Which agent is working: the most recently touched canonical log.
            best = None
            for k in range(1, 8):
                f = d / f"search_log_agent_{k}.txt"
                if f.exists() and (best is None or f.stat().st_mtime > best[0]):
                    best = (f.stat().st_mtime, k)
            if best:
                st["current_agent"] = best[1]
                st["agent_log_age_minutes"] = round((now - best[0]) / 60.0, 1)
            nf = newest_file(d)
            if nf:
                st["last_write_file"] = str(nf[1].relative_to(ROOT))
                st["last_write_age_minutes"] = round((now - nf[0]) / 60.0, 1)
                st["stalled"] = st["runner_alive"] and \
                    st["last_write_age_minutes"] > STALL_MINUTES

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

    body = "".join([
        row("Status", f'<b style="color:{colour}">{badge}</b>'),
        row("Countries complete", f'{st["countries_done"]} of {st["countries_total"]}'
                                  f' &nbsp;<small>{", ".join(st["done"]) or "none yet"}</small>'),
        row("Current country", st["current_country"]),
        row("Current agent", f'{st["current_agent"]} of 7' if st["current_agent"] else None),
        row("This country running for", mins(st["country_elapsed_minutes"])),
        row("Last file written", f'{st["last_write_file"]}'
                                 f' <small>({mins(st["last_write_age_minutes"])} ago)</small>'
            if st["last_write_file"] else None),
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
        print(f"{'RUNNING' if st['runner_alive'] else 'NOT RUNNING'}  "
              f"country={st['current_country']} agent={st['current_agent']}/7  "
              f"done={st['countries_done']}/40  "
              f"last write {st['last_write_age_minutes']} min ago"
              f"{'  STALLED' if st['stalled'] else ''}")

    if a.publish:
        sys.path.insert(0, str(ROOT / "py"))
        from publish import publish
        msg = (f"Run heartbeat: {st['current_country'] or 'idle'} "
               f"agent {st['current_agent'] or '-'}/7, "
               f"{st['countries_done']}/40 complete")
        print(publish(["dashboard/run_status.json", "dashboard/run_status.html"], msg))
    return 0


if __name__ == "__main__":
    sys.exit(main())
