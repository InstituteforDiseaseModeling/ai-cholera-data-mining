#!/usr/bin/env python3
"""
Safe, validating editor for EXISTING rows of data/{ISO}/cholera_data_ai.csv.

py/add_observation.py is the writer for NEW rows. It has no verb for the other
half of the job: retracting a row the evidence contradicts, re-weighting a row
that turned out to be conflicted, or appending an adjudication to
processing_notes. Agents needing those have been hand-editing the CSVs, which
CLAUDE.md forbids and which is the documented root cause of the mismatched
citations, ragged rows and reversed dates already in this dataset.

This tool closes that gap. It reuses add_observation.py's file lock, timestamped
backup and header-integrity guard, so a revision is exactly as safe as an
insert, and it re-checks the same arithmetic invariants afterwards.

    # append an adjudication to processing_notes (never overwrites)
    python py/revise_observation.py TGO --index 6 \
        --append-note "CONFLICT: Rebaudet 2018 Table 1 gives 194 for 2013." \
        --reason "Agent 5 cross-reference"

    # re-weight a row that stays in the file but is now known to be conflicted
    python py/revise_observation.py TGO --index 122 --confidence 0.4 \
        --append-note "..." --reason "..."

    # retract a row the evidence contradicts (writes a tombstone to
    # data/{ISO}/retracted_rows_ai.csv so the value is never silently lost)
    python py/revise_observation.py TGO --index 51 --delete \
        --reason "superseded by Index 103, named district health director"

Exit codes: 0 written, 1 rejected by validation, 2 usage error.
"""

import argparse
import csv
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from add_observation import (  # noqa: E402
    DATA, DATA_COLUMNS, META_COLUMNS, check_scope, die, load, locked, save,
)

RETRACT_COLUMNS = DATA_COLUMNS + ["retracted_on", "retracted_reason"]


def _num(s):
    s = (s or "").strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _recheck(row):
    """Re-assert the invariants add_observation.py enforces on insert."""
    sch, cch, deaths = _num(row["sCh"]), _num(row["cCh"]), _num(row["deaths"])
    if sch is None and cch is None and deaths is None:
        die(f"Index {row['Index']}: revision would leave the row with no case "
            f"value at all; CLAUDE.md prohibits count-less rows in "
            f"cholera_data_ai.csv")
    if deaths is not None and sch is not None and deaths > sch:
        die(f"Index {row['Index']}: deaths {deaths:g} > sCh {sch:g}")
    if cch is not None and sch is not None and cch > sch:
        die(f"Index {row['Index']}: cCh {cch:g} > sCh {sch:g}")
    if row["TL"] > row["TR"]:
        die(f"Index {row['Index']}: TL {row['TL']} after TR {row['TR']}")
    rep = (row.get("reporting_date") or "").strip()
    if rep and rep < row["TR"]:
        die(f"Index {row['Index']}: reporting_date {rep} precedes TR "
            f"{row['TR']}; a period cannot be reported before it ends")
    conf = _num(row["confidence_weight"])
    if conf is None or not (0.1 <= conf <= 1.0):
        die(f"Index {row['Index']}: confidence_weight {row['confidence_weight']!r} "
            f"outside 0.1-1.0")
    # CFR is computed, never typed.
    if sch and deaths is not None:
        row["CFR"] = f"{deaths / sch * 100:.2f}"
    elif deaths in (0, None) and sch == 0:
        row["CFR"] = "0.0"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("iso")
    ap.add_argument("--index", help="value of the Index column in cholera_data_ai.csv")
    ap.add_argument("--meta-index",
                    help="value of the Index column in metadata_ai.csv; with "
                         "--set-description, corrects a source Description "
                         "without touching any data row")
    ap.add_argument("--set-description", default="",
                    help="replacement Description for --meta-index")
    ap.add_argument("--set-status", default="", dest="set_status",
                    help="replacement Status for --meta-index. Use 'Superseded' "
                         "to retire a source whose URL or attribution was found "
                         "wrong, so no future agent re-cites it. Refuses if any "
                         "live row in cholera_data_ai.csv still cites the entry")
    ap.add_argument("--append-note", default="",
                    help="text appended to processing_notes; never overwrites")
    ap.add_argument("--confidence", default="", help="new confidence_weight")
    ap.add_argument("--sch", default="")
    ap.add_argument("--cch", default="")
    ap.add_argument("--deaths", default="")
    ap.add_argument("--tl", default="")
    ap.add_argument("--tr", default="")
    ap.add_argument("--reporting-date", default="", dest="reporting_date",
                    help="new reporting_date (YYYY-MM-DD); must be >= TR")
    ap.add_argument("--location", default="")
    ap.add_argument("--set-evidence", default="", dest="set_evidence",
                    choices=["", "Documented_Absence", "Inferred_Absence"],
                    help="rewrite the row's CANONICAL 'Evidence type: X' token "
                         "(the first occurrence, written at insert time and the "
                         "one py/build_weekly_timeseries.py reads). Later "
                         "adjudication prose in the note is left untouched")
    ap.add_argument("--agent", default="5",
                    help="agent number stamped into the appended note; "
                         "defaults to 5 for backward compatibility")
    ap.add_argument("--delete", action="store_true",
                    help="retract the row; a tombstone is kept")
    ap.add_argument("--reason", required=True,
                    help="why, in one line; stamped into the row or tombstone")
    a = ap.parse_args()

    iso = a.iso.upper()
    check_scope(iso)

    if a.meta_index:
        if not (a.set_description or a.set_status):
            die("--meta-index requires --set-description and/or --set-status",
                code=2)
        mpath = DATA / iso / "metadata_ai.csv"

        # Retiring a source is only safe if nothing still cites it. Check the
        # data file BEFORE taking the metadata lock, so a stale citation can
        # never be laundered into a clean-looking Superseded entry.
        if a.set_status and a.set_status.strip().lower() != "active":
            dpath = DATA / iso / "cholera_data_ai.csv"
            if dpath.exists():
                drows, _ = load(dpath, DATA_COLUMNS)
                citing = [r.get("Index") for r in drows
                          if (r.get("source_index") or "").strip()
                          == str(a.meta_index)]
                if citing:
                    die(f"refusing to set Status='{a.set_status}' on metadata "
                        f"Index {a.meta_index}: {len(citing)} live row(s) still "
                        f"cite it (Index {', '.join(map(str, citing[:10]))}). "
                        f"Re-point or retract those rows first.", code=1)

        with locked(mpath):
            mrows, mfields = load(mpath, META_COLUMNS)
            hit = [r for r in mrows
                   if (r.get("Index") or "").strip() == str(a.meta_index)]
            if len(hit) != 1:
                die(f"metadata Index {a.meta_index} not found exactly once "
                    f"in {mpath}", code=2)
            print(f"REVISED metadata Index {a.meta_index} in {mpath}")
            if a.set_description:
                old = hit[0].get("Description", "")
                hit[0]["Description"] = a.set_description
                print(f"  old Description ({len(old)} chars): {old[:160]}...")
            if a.set_status:
                old_st = hit[0].get("Status", "")
                hit[0]["Status"] = a.set_status
                print(f"  Status: '{old_st}' -> '{a.set_status}'")
            save(mpath, mrows, mfields)
            print(f"  reason: {a.reason}")
        return 0

    if not a.index:
        die("one of --index or --meta-index is required", code=2)
    path = DATA / iso / "cholera_data_ai.csv"
    if not path.exists():
        die(f"{path} does not exist", code=2)

    with locked(path):
        rows, fields = load(path, DATA_COLUMNS)
        hits = [r for r in rows if (r.get("Index") or "").strip() == str(a.index)]
        if not hits:
            die(f"no row with Index {a.index} in {path}", code=2)
        if len(hits) > 1:
            die(f"Index {a.index} is not unique in {path}; fix that first")
        row = hits[0]
        stamp = date.today().isoformat()

        if a.delete:
            rows.remove(row)
            tomb = path.parent / "retracted_rows_ai.csv"
            existing, tfields = load(tomb, RETRACT_COLUMNS)
            rec = {k: row.get(k, "") for k in DATA_COLUMNS}
            rec["retracted_on"] = stamp
            rec["retracted_reason"] = a.reason
            existing.append(rec)
            save(tomb, existing, tfields if tomb.exists() else RETRACT_COLUMNS)
            save(path, rows, fields)
            print(f"RETRACTED Index {a.index} from {path}")
            print(f"  tombstone -> {tomb}")
            print(f"  reason: {a.reason}")
            return 0

        before = {k: row.get(k, "") for k in
                  ("Location", "TL", "TR", "sCh", "cCh", "deaths",
                   "reporting_date", "confidence_weight")}
        for opt, col in (("location", "Location"), ("tl", "TL"), ("tr", "TR"),
                         ("sch", "sCh"), ("cch", "cCh"), ("deaths", "deaths"),
                         ("reporting_date", "reporting_date"),
                         ("confidence", "confidence_weight")):
            val = getattr(a, opt)
            if val != "":
                row[col] = val
        if a.set_evidence:
            note = row.get("processing_notes") or ""
            m = re.search(r"Evidence type:\s*([A-Za-z_]+)", note)
            if not m:
                die(f"Index {a.index}: no canonical 'Evidence type: X' token to "
                    f"rewrite; use add_observation.py add-zero instead", code=2)
            old_ev = m.group(1)
            if old_ev == a.set_evidence:
                die(f"Index {a.index}: canonical evidence label is already "
                    f"{old_ev}", code=2)
            row["processing_notes"] = (
                note[:m.start(1)] + a.set_evidence + note[m.end(1):])
            print(f"  canonical Evidence type: {old_ev!r} -> {a.set_evidence!r}")

        changed = {k: (before[k], row.get(k, "")) for k in before
                   if before[k] != row.get(k, "")}
        if not changed and not a.append_note and not a.set_evidence:
            die("nothing to change", code=2)

        _recheck(row)

        if a.append_note:
            note = (row.get("processing_notes") or "").rstrip()
            sep = " " if note and not note.endswith(".") else " "
            row["processing_notes"] = (
                f"{note}{sep}[AGENT {a.agent} REVISION {stamp}] {a.append_note} "
                f"(reason: {a.reason})").strip()
        elif changed:
            note = (row.get("processing_notes") or "").rstrip()
            row["processing_notes"] = (
                f"{note} [AGENT {a.agent} REVISION {stamp}] "
                f"{a.reason}").strip()

        save(path, rows, fields)
        print(f"REVISED Index {a.index} in {path}")
        for k, (old, new) in changed.items():
            print(f"  {k}: {old!r} -> {new!r}")
        if a.append_note:
            print(f"  processing_notes: appended {len(a.append_note)} chars")
    return 0


if __name__ == "__main__":
    sys.exit(main())
