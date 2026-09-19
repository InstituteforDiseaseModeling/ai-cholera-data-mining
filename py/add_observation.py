#!/usr/bin/env python3
"""
Safe, validating writer for cholera_data_ai.csv and metadata_ai.csv.

Agents previously hand-edited these CSVs. That is the root cause of most of the
bookkeeping defects found in the existing data: source_index values pointing at
the wrong metadata entry, `source` text drifting away from the metadata Source
it claims to cite, duplicated or skipped Index numbers, and rows written with no
case value at all.

This tool makes the correct thing the easy thing:
  * allocates the next metadata Index atomically, or reuses an existing source
    when the same URL is registered again
  * writes the `source` column FROM the metadata entry, so the two can never
    disagree
  * refuses rows that violate a CLAUDE.md MANDATORY rule, before they land
  * preserves column order and never rewrites unrelated rows

Register a source, then add observations against it:

    python py/add_observation.py register-source ETH \\
        --name "WHO AFRO Ethiopia Cholera Situation Report 12" \\
        --url "https://example.who.int/..." \\
        --reliability 1 --date-range "2026-01-01 to 2026-06-30" \\
        --discovery "WebSearch: Ethiopia cholera 2026 WHO AFRO"

    python py/add_observation.py add ETH --source-index 18 \\
        --location "AFR::ETH::Oromia" --tl 2026-03-01 --tr 2026-05-31 \\
        --sch 412 --deaths 9 --reporting-date 2026-06-04 \\
        --confidence 0.9 \\
        --quote "Oromia region reported 412 cholera cases and 9 deaths"

    python py/add_observation.py add-zero ETH --source-index 18 \\
        --tl 2026-01-01 --tr 2026-02-28 --evidence Documented_Absence \\
        --confidence 0.9 --surveillance operational \\
        --quote "no cholera cases were reported in Ethiopia in January-February"

Exit codes: 0 written, 1 rejected by validation, 2 usage error.
"""

import argparse
import csv
import fcntl
import json
import shutil
import sys
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
REF = ROOT / "reference"

DATA_COLUMNS = [
    "Index", "Location", "TL", "TR", "deaths", "sCh", "cCh", "CFR",
    "reporting_date", "source_index", "source", "confidence_weight",
    "processing_notes", "source_database",
]
META_COLUMNS = [
    "Index", "Source", "URL", "Description", "Date_Range", "Data_Type", "Status",
    "Reliability_Level", "Validation_Status", "Search_Technique",
    "Language_Original", "Citation_Depth", "Cross_References",
    "Discovery_Method", "source_database",
]
# Evidence labels that may back a ZERO row. "Surveillance_Gap" is deliberately
# NOT here: a gap means nobody was looking, which is missing data, not absence
# of disease. py/build_weekly_timeseries.py collapses any non-documented zero to
# inferred_zero with sCh=0, so admitting Surveillance_Gap would emit a confirmed
# "0 cases" for periods with no surveillance at all - the exact false negative
# the zero-transmission-validator agent exists to prevent.
ZERO_EVIDENCE = ["Documented_Absence", "Inferred_Absence"]
ZERO_EVIDENCE_REJECTED = {
    "Surveillance_Gap": (
        "a surveillance gap is missing data, not a zero. Nobody was looking, so "
        "there is no evidence either way. Record it in cholera_presence_ai.csv "
        "or in your search log and leave the period genuinely empty; writing "
        "sCh=0 tells the model the disease was absent when it was merely unobserved."
    ),
}
RELIABILITY_WEIGHT = {1: (0.9, 1.0), 2: (0.7, 0.9), 3: (0.3, 0.6), 4: (0.1, 0.3)}

# Schema of data/{ISO}/cholera_presence_ai.csv - cholera confirmed present but
# no count available. Mandated by the agent definitions and the search protocol,
# but until now writable only as a side effect of py/repair_data_integrity.py,
# which left agents with an instruction they could not follow.
PRESENCE_COLUMNS = [
    "Location", "TL", "TR", "evidence", "source_index", "source",
    "confidence_weight", "processing_notes", "source_database", "moved_from_row",
]


def die(msg, code=1):
    print(f"REJECTED: {msg}", file=sys.stderr)
    sys.exit(code)


def load(path, columns):
    if not path.exists():
        return [], columns
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rdr = csv.DictReader(fh)
        rows = list(rdr)
        return rows, list(rdr.fieldnames or columns)


@contextmanager
def locked(path):
    """Hold an exclusive lock across a read-modify-write of `path`.

    Without this, two agents adding rows concurrently both read the same file,
    both append, and the second write silently discards the first agent's row -
    while both print "ADDED". Measured: 6 concurrent adds produced 1 surviving
    row and 6 success messages.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.parent / f".{path.name}.lock"
    fh = open(lock, "w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()


def save(path, rows, fields):
    # Refuse to write a row carrying a key the header does not have. The old
    # filter-and-continue silently dropped the value - including reporting a
    # cCh it had not written - and, because the whole file is re-serialised,
    # permanently stripped that column from every other row too.
    unknown = set()
    for r in rows:
        unknown |= {k for k in r if k not in fields and k is not None}
    if unknown:
        die(f"{path.name} header is missing column(s) {sorted(unknown)}; "
            f"refusing to write, because doing so would drop them from every "
            f"row in the file. Fix the header first.")
    if any(None in r for r in rows):
        die(f"{path.name} contains a ragged row with more fields than its "
            f"header; refusing to rewrite the file.")

    if path.exists():
        # Microsecond stamp: a second-granular name let two writes in the same
        # second overwrite each other, so the backup was not a restore point.
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S%f")
        shutil.copy2(path, path.parent / f".backup_{path.stem}_{stamp}.csv")
    tmp = path.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    tmp.replace(path)


def mosaic_isos():
    m = json.loads((REF / "country_mapping.json").read_text())["countries"]
    return {k for k, v in m.items() if v.get("mosaic_framework")}


def check_scope(iso):
    if iso not in mosaic_isos():
        die(f"{iso} is not one of the 40 MOSAIC framework countries; "
            f"CLAUDE.md restricts collection to those", code=2)


def parse_d(s, field):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        die(f"{field}={s!r} must be YYYY-MM-DD", code=2)


def cmd_register_source(a):
    check_scope(a.iso)
    path = DATA / a.iso / "metadata_ai.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with locked(path):
        return _register_source_locked(a, path)


def _register_source_locked(a, path):
    rows, fields = load(path, META_COLUMNS)

    for r in rows:
        if a.url and (r.get("URL") or "").strip() == a.url.strip():
            print(f"EXISTS index={r['Index']} (same URL already registered)")
            print(f"  Source: {r.get('Source')}")
            return 0

    used = {int(r["Index"]) for r in rows if (r.get("Index") or "").strip().isdigit()}
    idx = max(used) + 1 if used else 1
    if any(r.get("Source", "").strip() == a.name.strip() for r in rows):
        die(f"a different metadata entry already uses the Source name {a.name!r}; "
            f"names must be unique to keep the dual-reference system unambiguous")

    lo, hi = RELIABILITY_WEIGHT[a.reliability]
    rows.append({
        "Index": str(idx), "Source": a.name.strip(), "URL": a.url.strip(),
        "Description": a.description, "Date_Range": a.date_range,
        "Data_Type": a.data_type, "Status": "Active",
        "Reliability_Level": f"Level {a.reliability}",
        "Validation_Status": "Pending", "Search_Technique": a.discovery,
        "Language_Original": a.language, "Citation_Depth": str(a.citation_depth),
        "Cross_References": a.cross_references, "Discovery_Method": a.discovery,
        "source_database": "AI",
    })
    save(path, rows, fields)
    print(f"REGISTERED index={idx} in data/{a.iso}/metadata_ai.csv")
    print(f"  Source          : {a.name}")
    print(f"  Reliability     : Level {a.reliability} -> confidence_weight {lo}-{hi}")
    print(f"  Use --source-index {idx} when adding observations.")
    return 0


def _append_row(a, row, sch, deaths, cch):
    check_scope(a.iso)
    dpath = DATA / a.iso / "cholera_data_ai.csv"
    with locked(dpath):
        return _append_row_locked(a, row, sch, deaths, cch, dpath)


def _append_row_locked(a, row, sch, deaths, cch, dpath):
    mpath = DATA / a.iso / "metadata_ai.csv"
    meta, _ = load(mpath, META_COLUMNS)
    midx = {(m.get("Index") or "").strip(): m for m in meta}

    si = str(a.source_index)
    if si not in midx:
        die(f"source_index {si} is not registered in data/{a.iso}/metadata_ai.csv. "
            f"Run `register-source` first. Known: "
            f"{sorted(midx, key=lambda x: int(x)) if midx else 'none'}")

    src_entry = midx[si]
    # The source column is written FROM metadata, never supplied by the caller:
    # this makes the source_index <-> Source mismatch class structurally
    # impossible rather than merely discouraged.
    row["source_index"] = si
    row["source"] = (src_entry.get("Source") or "").strip()
    row["source_database"] = "AI"

    lvl = (src_entry.get("Reliability_Level") or "")
    lo = hi = None
    for n, (l, h) in RELIABILITY_WEIGHT.items():
        if f"Level {n}" in lvl:
            lo, hi = l, h
    cw = float(a.confidence)
    if not (0.1 <= cw <= 1.0):
        die(f"--confidence {cw} outside 0.1-1.0")

    # The reliability band is a CEILING, not a window.
    #
    # Treating it as a two-sided window deadlocks against the downgrade rules:
    # a 20%-CFR row from a Level 1 WHO source must be capped at 0.7 by the CFR
    # rule, but 0.7 sits below the Level 1 floor of 0.9, so no value satisfied
    # both and the row could not be written at all. Claiming MORE confidence
    # than the source tier justifies is the actual error; claiming less is
    # always permissible and is exactly what the downgrade rules require.
    if hi is not None and cw > hi and not a.force_confidence:
        die(f"--confidence {cw} exceeds the ceiling for {lvl} ({hi}). A row "
            f"cannot be more reliable than the source it cites.")
    if lo is not None and cw < lo:
        print(f"NOTE: confidence {cw} is below the usual {lvl} floor ({lo}) - "
              f"recorded as a deliberate downgrade.")

    tl, tr = parse_d(row["TL"], "--tl"), parse_d(row["TR"], "--tr")
    if tl > tr:
        die(f"TL {tl} is after TR {tr}")
    today = date.today()
    if tr > today:
        die(f"TR {tr} is in the future (today {today}); surveillance data cannot "
            f"describe a period that has not happened")
    if row.get("reporting_date"):
        rd = parse_d(row["reporting_date"], "--reporting-date")
        if rd > today:
            die(f"reporting_date {rd} is in the future")
        if rd < tr:
            die(f"reporting_date {rd} precedes TR {tr}")

    # Multi-year ZERO rows are mandated by the Agent 3 spec ("create ONE row for
    # a multi-year absence, not year-by-year rows") and are exempted from the
    # aggregation cap here, matching py/validate_quality.py. Only rows carrying
    # COUNTS are aggregates whose confidence must be capped: a decade-long
    # absence attested by one source is not an aggregate of anything.
    is_zero_row = (sch == 0 and deaths == 0)
    if (tr - tl).days > 760 and cw > 0.7 and not is_zero_row:
        die(f"period spans {(tr - tl).days} days (>2 years) with confidence "
            f"{cw}; CLAUDE.md caps multi-year aggregates at 0.7")

    # Negative counts would subtract from national aggregates downstream.
    for nm, v in (("sCh", sch), ("cCh", cch), ("deaths", deaths)):
        if v is not None and v < 0:
            die(f"--{nm.lower()} {v} is negative; counts cannot be below zero")

    # These comparisons were gated on `sch > 0`, which skipped them exactly
    # where they matter: sCh=0 with deaths=500 is impossible AND is read
    # downstream as a documented absence - the precise false negative this
    # tool exists to prevent.
    if deaths is not None and sch is not None:
        if deaths > sch:
            extra = ("  A zero case count with deaths above zero is also read "
                     "downstream as a documented absence." if sch == 0 else "")
            die(f"deaths {deaths} exceeds sCh {sch}.{extra}")
        if sch > 0:
            implied = deaths / sch * 100
            row["CFR"] = f"{implied:.2f}"
            if sch >= 25 and implied > 15 and cw > 0.7:
                die(f"implied CFR {implied:.1f}% exceeds 15% with confidence {cw}; "
                    f"downweight to <=0.7 and document the context")
    if cch is not None and sch is not None and cch > sch:
        die(f"cCh {cch} exceeds sCh {sch}")
    if deaths is not None and sch is None and cch is not None and deaths > cch:
        die(f"deaths {deaths} exceeds cCh {cch} and no sCh was given")

    if not row["Location"].startswith(f"AFR::{a.iso}"):
        die(f"Location {row['Location']!r} must start with AFR::{a.iso}")
    low = row["Location"].lower()
    for tok in ("vaccination", "training", "demographics", "age_", "laboratory_",
                "surveillance_", "population", "capacity", "ocv"):
        if tok in low:
            die(f"Location {row['Location']!r} looks like a non-geographic "
                f"category (matched {tok!r}); CLAUDE.md prohibits these")

    rows, fields = load(dpath, DATA_COLUMNS)
    for i, ex in enumerate(rows, start=2):
        if ((ex.get("Location"), ex.get("TL"), ex.get("TR"), ex.get("sCh"),
             ex.get("deaths")) == (row["Location"], row["TL"], row["TR"],
                                   row["sCh"], row["deaths"])):
            die(f"identical row already present at line {i} "
                f"(same location, period and counts). If this is independent "
                f"corroboration, record it in that row's processing_notes "
                f"instead of adding a duplicate.")

    used = {int(r["Index"]) for r in rows if (r.get("Index") or "").strip().isdigit()}
    row["Index"] = str(max(used) + 1 if used else 1)
    row["confidence_weight"] = f"{cw}"

    rows.append(row)
    save(dpath, rows, fields)
    print(f"ADDED row Index={row['Index']} to data/{a.iso}/cholera_data_ai.csv")
    print(f"  {row['Location']}  {row['TL']}..{row['TR']}  "
          f"sCh={row['sCh'] or '-'} cCh={row['cCh'] or '-'} deaths={row['deaths'] or '-'} "
          f"CFR={row['CFR'] or '-'}")
    print(f"  source[{si}] {row['source']}  (confidence {cw})")
    return 0


def cmd_add(a):
    if a.sch is None and a.cch is None and a.deaths is None:
        die("a row needs at least one of --sch, --cch or --deaths. A source that "
            "confirms cholera was present but gives no numbers belongs in "
            "cholera_presence_ai.csv: CLAUDE.md prohibits count-less rows in the "
            "data file, and coverage analysis discards them as non-informative, so "
            "they would read as data while contributing none.")
    if not a.quote.strip():
        die("--quote is mandatory: processing_notes must carry the exact source "
            "text supporting the interpretation")
    notes = f"Source states: '{a.quote.strip()}' - interpreted as "
    parts = []
    if a.sch is not None:
        parts.append(f"{a.sch} sCh cases")
    if a.cch is not None:
        parts.append(f"{a.cch} cCh confirmed cases")
    if a.deaths is not None:
        parts.append(f"{a.deaths} deaths")
    notes += ", ".join(parts) + "."
    if a.note:
        notes += " " + a.note.strip()
    row = {
        "Location": a.location, "TL": a.tl, "TR": a.tr,
        "deaths": "" if a.deaths is None else str(a.deaths),
        "sCh": "" if a.sch is None else str(a.sch),
        "cCh": "" if a.cch is None else str(a.cch),
        "CFR": "", "reporting_date": a.reporting_date or "",
        "processing_notes": notes,
    }
    return _append_row(a, row, a.sch, a.deaths, a.cch)


def cmd_add_zero(a):
    if a.evidence in ZERO_EVIDENCE_REJECTED:
        die(f"--evidence {a.evidence} cannot back a zero row: "
            f"{ZERO_EVIDENCE_REJECTED[a.evidence]}")
    if a.evidence not in ZERO_EVIDENCE:
        die(f"--evidence must be one of {ZERO_EVIDENCE}")
    if not a.quote.strip():
        die("--quote is mandatory for a zero row: an undocumented zero is "
            "indistinguishable from missing data downstream")
    notes = (f"Source confirms zero cholera transmission {a.tl}..{a.tr}. "
             f"Source states: '{a.quote.strip()}'. "
             f"Evidence type: {a.evidence}. "
             f"Surveillance system status during absence: {a.surveillance}.")
    if a.note:
        notes += " " + a.note.strip()
    row = {
        "Location": a.location or f"AFR::{a.iso}", "TL": a.tl, "TR": a.tr,
        "deaths": "0", "sCh": "0", "cCh": "", "CFR": "0.0",
        "reporting_date": a.reporting_date or "", "processing_notes": notes,
    }
    return _append_row(a, row, 0, 0, None)


def cmd_add_presence(a):
    """Record cholera confirmed present with no usable count."""
    check_scope(a.iso)
    if not a.quote.strip():
        die("--quote is mandatory: record what the source actually said")
    ppath = DATA / a.iso / "cholera_presence_ai.csv"
    mpath = DATA / a.iso / "metadata_ai.csv"
    with locked(ppath):
        meta, _ = load(mpath, META_COLUMNS)
        midx = {(m.get("Index") or "").strip(): m for m in meta}
        si = str(a.source_index)
        if si not in midx:
            die(f"source_index {si} is not registered in data/{a.iso}/metadata_ai.csv")
        tl, tr = parse_d(a.tl, "--tl"), parse_d(a.tr, "--tr")
        if tl > tr:
            die(f"TL {tl} is after TR {tr}")
        if tr > date.today():
            die(f"TR {tr} is in the future")
        if not a.location.startswith(f"AFR::{a.iso}"):
            die(f"Location {a.location!r} must start with AFR::{a.iso}")

        rows, fields = load(ppath, PRESENCE_COLUMNS)
        key = (a.location, a.tl, a.tr, si)
        for r in rows:
            if (r.get("Location"), r.get("TL"), r.get("TR"),
                    r.get("source_index")) == key:
                die("an identical presence record is already on file")
        rows.append({
            "Location": a.location, "TL": a.tl, "TR": a.tr,
            "evidence": "presence_confirmed_count_unknown",
            "source_index": si,
            "source": (midx[si].get("Source") or "").strip(),
            "confidence_weight": str(a.confidence),
            "processing_notes": f"Source states: '{a.quote.strip()}' - cholera "
                                f"confirmed present; no case count available.",
            "source_database": "AI", "moved_from_row": "",
        })
        save(ppath, rows, fields)
    print(f"RECORDED presence in data/{a.iso}/cholera_presence_ai.csv")
    print(f"  {a.location}  {a.tl}..{a.tr}  (no count available)")
    print("  This is NOT a data row and will not enter the time series. It is "
          "evidence for gap classification.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    rs = sub.add_parser("register-source", help="register a source in metadata_ai.csv")
    rs.add_argument("iso")
    rs.add_argument("--name", required=True)
    rs.add_argument("--url", required=True)
    rs.add_argument("--reliability", type=int, required=True, choices=[1, 2, 3, 4])
    rs.add_argument("--description", default="")
    rs.add_argument("--date-range", default="")
    rs.add_argument("--data-type", default="Surveillance")
    rs.add_argument("--discovery", default="", help="query or method that found it")
    rs.add_argument("--language", default="en")
    rs.add_argument("--citation-depth", type=int, default=0)
    rs.add_argument("--cross-references", default="")
    rs.set_defaults(func=cmd_register_source)

    common = dict(required=False)
    ad = sub.add_parser("add", help="add an observation with case counts")
    ad.add_argument("iso")
    ad.add_argument("--source-index", required=True)
    ad.add_argument("--location", required=True)
    ad.add_argument("--tl", required=True)
    ad.add_argument("--tr", required=True)
    ad.add_argument("--sch", type=int, **common)
    ad.add_argument("--cch", type=int, **common)
    ad.add_argument("--deaths", type=int, **common)
    ad.add_argument("--reporting-date", default="")
    ad.add_argument("--confidence", required=True)
    ad.add_argument("--quote", required=True, help="exact source text")
    ad.add_argument("--note", default="", help="extra interpretation notes")
    ad.add_argument("--force-confidence", action="store_true")
    ad.set_defaults(func=cmd_add)

    az = sub.add_parser("add-zero", help="add a validated zero-transmission period")
    az.add_argument("iso")
    az.add_argument("--source-index", required=True)
    az.add_argument("--location", default="")
    az.add_argument("--tl", required=True)
    az.add_argument("--tr", required=True)
    az.add_argument("--evidence", required=True,
                    choices=ZERO_EVIDENCE + list(ZERO_EVIDENCE_REJECTED),
                    help="Surveillance_Gap is accepted by the parser only so it "
                         "can be rejected with an explanation")
    az.add_argument("--surveillance", required=True,
                    choices=["operational", "partial", "disrupted", "unknown"])
    az.add_argument("--reporting-date", default="")
    az.add_argument("--confidence", required=True)
    az.add_argument("--quote", required=True)
    az.add_argument("--note", default="")
    az.add_argument("--force-confidence", action="store_true")
    az.set_defaults(func=cmd_add_zero)

    pr = sub.add_parser("add-presence",
                        help="record cholera present but with no usable count")
    pr.add_argument("iso")
    pr.add_argument("--source-index", required=True)
    pr.add_argument("--location", required=True)
    pr.add_argument("--tl", required=True)
    pr.add_argument("--tr", required=True)
    pr.add_argument("--confidence", default="0.5")
    pr.add_argument("--quote", required=True)
    pr.set_defaults(func=cmd_add_presence)

    a = ap.parse_args()
    a.iso = a.iso.upper()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
