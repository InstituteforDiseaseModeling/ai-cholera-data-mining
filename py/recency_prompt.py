#!/usr/bin/env python3
"""Build the per-country prompt for a recency-only pass.

A recency pass brings each country up to the present without re-running the full
7-agent workflow. Its window is fixed per country:

    window start = day after the country's latest observation (any layer,
                   from reference/effective_surveillance_recency.csv)
    window end   = the pass date (today unless --end is given)

Two stages run as separate `claude -p` processes, driven by
run_all_countries.sh --mode recency:

    collect  cholera-baseline-collector, scoped to the window only
    audit    cholera-quality-auditor, scoped to the rows the collect stage wrote

Every row written in the pass carries the tag [RECENCY-<tag>] in
processing_notes so it can be audited or rolled back as a set. Logs go to
search_log_recency_<tag>_agent{1,7}.txt; the full-run logs, workflow_state.json
and the baselines are left alone.

Usage:
    python3 py/recency_prompt.py ETH collect --tag 20261116
    python3 py/recency_prompt.py ETH audit   --tag 20261116
    python3 py/recency_prompt.py --windows   --tag 20261116   # table of windows
"""
import argparse
import csv
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECENCY = ROOT / "reference" / "effective_surveillance_recency.csv"
WINDOWS_DIR = ROOT / "reference"


def windows_path(tag):
    return WINDOWS_DIR / f"recency_windows_{tag}.csv"


def compute_windows(end):
    out = {}
    for r in csv.DictReader(open(RECENCY, newline="", encoding="utf-8")):
        last = r.get("latest_observation") or ""
        if not last:
            continue
        start = datetime.strptime(last, "%Y-%m-%d").date() + timedelta(days=1)
        out[r["iso_code"]] = {
            "iso": r["iso_code"],
            "country": r["country"],
            "latest_observation": last,
            "latest_positive_observation": r.get("latest_positive_observation", ""),
            "window_start": start.isoformat(),
            "window_end": end.isoformat(),
            "window_days": (end - start).days + 1,
        }
    return out


def load_or_freeze_windows(tag, end):
    """Windows are frozen at the start of a pass.

    The recency file is regenerated after every country finishes, and a country's
    own new rows move its latest observation forward. Recomputing on a retry would
    shrink the window to nothing. So the first call writes
    reference/recency_windows_<tag>.csv and every later call reads it.
    """
    p = windows_path(tag)
    if p.exists():
        return {r["iso"]: r for r in csv.DictReader(open(p, newline="", encoding="utf-8"))}
    w = compute_windows(end)
    with open(p, "w", newline="", encoding="utf-8") as fh:
        cols = ["iso", "country", "latest_observation", "latest_positive_observation",
                "window_start", "window_end", "window_days"]
        wr = csv.DictWriter(fh, fieldnames=cols)
        wr.writeheader()
        for iso in sorted(w):
            wr.writerow(w[iso])
    return {k: {c: str(v) for c, v in d.items()} for k, d in w.items()}


def who_extent_text(iso):
    p = ROOT / "data" / iso / "cholera_data_who.csv"
    if not p.exists():
        return f"{iso} is not in the WHO weekly feed, so there is no WHO baseline to dedup against."
    trs = [r["TR"] for r in csv.DictReader(open(p, newline="", encoding="utf-8")) if r.get("TR")]
    if not trs:
        return f"{iso}'s WHO baseline file is empty."
    return f"{iso}'s WHO weekly rows end at {max(trs)}."


def collect_prompt(w, tag):
    iso, country = w["iso"], w["country"]
    s, e = w["window_start"], w["window_end"]
    lp = w["latest_positive_observation"] or "none on record"
    who_extent = who_extent_text(iso)
    return f"""RECENCY PASS {tag} - {country} ({iso}). Stage: COLLECT (you are Agent 1 of a 2-stage recency pass).

SCOPE: one gap only - from the day after {iso}'s latest observation to the present.
  Window: {s} to {e}  ({w['window_days']} days)
  Latest observation in any layer (JHU/WHO/AI): {w['latest_observation']}
  Latest POSITIVE observation: {lp}
Do NOT search, add, revise or retract anything for periods before {s}. Historical gaps are out
of scope for this pass, however tempting. The effective gap files list many older gaps; ignore
them. Your target is this single trailing window.

WHAT TO PRODUCE in ./data/{iso}/cholera_data_ai.csv (via py/add_observation.py only):
  1. Case/death counts for periods inside the window, at national level first, then ADM1
     where sources give it. Prefer period counts (weekly, monthly, epi-week ranges).
  2. Cumulative-to-date figures (e.g. "since 1 January 2026") are useful even though their TL
     falls before {s}: record them only when the cumulative END date falls inside the window,
     keep the source's own start date as TL, and say "cumulative since <date>" in --note.
     The weekly builder decumulates chains against existing rows. Do not hand-difference.
  3. A zero row (add-zero) ONLY with explicit evidence that {iso} had no cholera during a stated
     part of the window and surveillance was operating (e.g. a MoH/WHO statement of zero cases,
     an outbreak declared over with a date). A country's absence from a multi-country list is NOT
     evidence of zero. Never label a zero Surveillance_Gap.
  4. Presence without a count -> py/add_observation.py add-presence, not a data row.

TAGGING (mandatory): begin every --note you pass with "[RECENCY-{tag}]". Also put
"[RECENCY-{tag}]" at the start of --discovery when registering sources. Stage 2 audits exactly
the rows carrying this tag.

DEDUP before every add:
  - ./data/{iso}/cholera_data_who.csv is the WHO dashboard baseline, refreshed on 2026-11-16
    (feed reaches WHO epi-week 42 of 2026). {who_extent} Do not re-enter WHO dashboard
    weekly numbers as AI rows. A WHO AFRO bulletin or sitrep that restates the same week is a
    duplicate; one that adds ADM1 detail, deaths, or weeks the dashboard lacks is not.
  - Check ./data/{iso}/cholera_data_ai.csv for rows already covering the same period and
    location (grep by TL/TR; do not load very large files wholesale). Do not read
    ./data/{iso}/cholera_data_jhu.csv in full - it can be tens of thousands of rows, and JHU
    ends in early 2025 so it cannot overlap this window anyway.
  - When national and provincial rows cover the same period, say in --note which is the primary
    count ("National total" / "Provincial subset - do not sum with national row").

WHERE RECENT DATA LIVES (lag is 1-6 weeks; the last weeks of the window may not be published yet):
  WHO AFRO weekly bulletins on outbreaks and other emergencies; WHO multi-country cholera
  external situation reports (monthly); WHO Disease Outbreak News; Africa CDC weekly epidemic
  intelligence reports; ECDC Communicable Disease Threats Reports (monthly cholera roundup);
  ReliefWeb / OCHA sitreps and flash updates; UNICEF humanitarian sitreps; IFRC DREF/appeal
  updates; MSF; the national public health institute / MoH sitreps and press releases named in
  ./reference/country_profiles.json (health-ministry domains, search languages, local disease
  terms); national news in the local languages listed there. Also run
  `python3 -I -B py/xref_harvest.py queue {iso}` and use any lead whose period falls in the
  window (add it yourself with add_observation.py; do NOT run `xref_harvest.py apply`).

METHOD: follow ./templates/template_search_protocol.txt for batch structure and yield
accounting, restricted to this window. Stopping rule unchanged: at least 3 batches of 20, then
stop at 3 consecutive batches below 5% yield, or 12 batches. Every query should carry the
window's time constraint (months/year, "2026", epi-week numbers).

FILES:
  - Log to ./data/{iso}/search_log_recency_{tag}_agent1.txt. Create it at once with a header
    (country, window, start time). Do NOT write or overwrite ./data/{iso}/search_log_agent_1.txt
    or any other search_log_agent_*.txt - those are the full-run logs.
  - Do NOT write ./data/{iso}/workflow_state.json or search_report.txt. If you need state, use
    ./data/{iso}/workflow_state_recency_{tag}.json.
  - Never touch cholera_data_jhu.csv / cholera_data_who.csv (they are locked), the dashboard, or
    any other country's directory.

FINISH: run `python3 py/validate_quality.py {iso}` and fix any ERROR on your own rows (via
py/revise_observation.py). End the log with a summary: batches run and yield per batch, rows
added (Index numbers), sources registered, which parts of the window are now covered, which
remain empty and why (not yet published / no surveillance / quiet). Then stop - stage 2 is run
by the runner, not by you."""


def audit_prompt(w, tag):
    iso, country = w["iso"], w["country"]
    s, e = w["window_start"], w["window_end"]
    return f"""RECENCY PASS {tag} - {country} ({iso}). Stage: AUDIT (you are Agent 7 of a 2-stage recency pass).

SCOPE: audit ONLY the rows of ./data/{iso}/cholera_data_ai.csv whose processing_notes contain
"[RECENCY-{tag}]", written by stage 1 for the window {s} to {e}. Do not re-audit the rest of the
dataset and do not rewrite the full-run search_report.txt. Read stage 1's log first:
./data/{iso}/search_log_recency_{tag}_agent1.txt. If it does not exist, stage 1 did not run:
write your log saying so and stop.

Do not load ./data/{iso}/cholera_data_jhu.csv wholesale (it can be tens of thousands of rows and
ends in early 2025, before this window). Filter rows with python/csv or grep.

For EVERY tagged row (or all of them if there are many - no sampling below 30 rows):
  1. Fetch the cited URL and confirm the quoted text and numbers are in it. Confirm the period
     type (weekly vs cumulative vs year-to-date) and the dates were read correctly.
  2. Duplication: not a restatement of a WHO dashboard week already in
     ./data/{iso}/cholera_data_who.csv; not a duplicate of another AI row; national vs ADM1
     roles stated so nothing double-counts.
  3. Plausibility: deaths <= sCh, cCh <= sCh, CFR, epidemic-curve continuity with the WHO
     baseline weeks just before the window, and consistency with neighbouring countries.
  4. Zero rows: explicit evidence of absence with surveillance operating; Documented_Absence
     only when the source states it. A zero inferred from silence must be retracted.
  5. Confidence weight matches the source tier.
Retract or correct with `py/revise_observation.py` (never hand-edit the CSVs); always give
--reason, and prefix it with "[RECENCY-{tag} AUDIT]".

Then run `python3 py/validate_quality.py {iso}`; it must exit 0.

FILES:
  - Log to ./data/{iso}/search_log_recency_{tag}_agent7.txt (create at start). Do NOT overwrite
    search_log_agent_7.txt or workflow_state.json.
  - APPEND (do not replace) a section to ./data/{iso}/search_report.txt headed
    "=== RECENCY PASS {tag}: window {s} to {e} ===" giving: rows checked, kept, corrected,
    retracted (with Index numbers and reasons), sources added, part of the window now covered,
    what remains empty and why, and the validator result. Keep it under 40 lines.
  - Do not touch baselines, the dashboard, or other countries."""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("iso", nargs="?")
    ap.add_argument("stage", nargs="?", choices=["collect", "audit"])
    ap.add_argument("--tag", required=True, help="pass tag, e.g. 20261116")
    ap.add_argument("--end", default=date.today().isoformat(), help="window end (default today)")
    ap.add_argument("--windows", action="store_true", help="print the frozen window table")
    a = ap.parse_args()
    end = datetime.strptime(a.end, "%Y-%m-%d").date()
    w = load_or_freeze_windows(a.tag, end)
    if a.windows:
        for iso in sorted(w, key=lambda i: w[i]["window_start"]):
            r = w[iso]
            print(f"{iso}  {r['window_start']} .. {r['window_end']}  ({r['window_days']} d)  "
                  f"last positive {r['latest_positive_observation'] or '-'}")
        return 0
    if not a.iso or not a.stage:
        ap.error("iso and stage are required unless --windows")
    iso = a.iso.upper()
    if iso not in w:
        print(f"no recency window for {iso}", file=sys.stderr)
        return 2
    print(collect_prompt(w[iso], a.tag) if a.stage == "collect" else audit_prompt(w[iso], a.tag))
    return 0


if __name__ == "__main__":
    sys.exit(main())
