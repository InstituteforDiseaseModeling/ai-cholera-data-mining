#!/usr/bin/env python3
"""
Import sub-national weekly rows from the JHU public surveillance archive (OSF)
into data/{ISO}/cholera_data_jhu_archive.csv, for the sub-national builders only.

Why: the JHU baseline in data/{ISO}/cholera_data_jhu.csv comes from the
jhu_cholera_data scraper, whose copy of some observation collections is a small
snapshot. For DR Congo health zones the archive holds 16,995 non-phantom weekly
rows (zeros included) for 2018-2022 where the baseline has about 3,000; 13,992
of them (3,664 with cases) are not in the baseline at all (2026-11-27).

Source (read only, hand-curated): MOSAIC-data/raw/JHU/osfstorage-archive/
Public_surveillance_dataset.rds. Read with R (no Python .rds reader is installed).

Rows written:
  - spatial_scale == --level (default admin2), Location prefix AFR::{ISO}::
  - phantom rows dropped (JHU's own flag; as MOSAIC-OCV code/k_experiment/k_data.R)
  - weekly rows only (6-7 day span)
  - same 14 columns as cholera_data_jhu.csv; Index "A1", "A2", ... so row keys
    never collide with the baseline's; source_database "JHU"; confidence_weight
    copied from the baseline's rows of the same collection, else 0.9
  - notes carry "Primary: True, Phantom: False" so the shared row parser treats
    them as primary JHU rows

The file is read ONLY by py/build_province_weekly.py and py/build_district_weekly.py
(as JHU rows). The national builder, the validators of the AI layer and the
dashboard do not read it. Where the archive and the baseline both report a unit
and week, the weekly engine keeps the larger value within the JHU label, so the
two are never added.

Also writes data/{ISO}/metadata_jhu_archive.csv (one row per collection).

Usage: python py/import_jhu_archive.py [--iso COD] [--level admin2] [--dry-run]
"""

import argparse
import csv
import hashlib
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ARCHIVE = BASE.parent / "MOSAIC-data" / "raw" / "JHU" / "osfstorage-archive" / "Public_surveillance_dataset.rds"
COLS = ["Index", "Location", "TL", "TR", "deaths", "sCh", "cCh", "CFR", "reporting_date",
        "source_index", "source", "confidence_weight", "processing_notes", "source_database"]
META_COLS = ["Index", "Source", "URL", "Description", "TL", "TR", "Reliability_Level", "source_database"]

R_EXPORT = r'''
args <- commandArgs(TRUE)
D <- as.data.frame(readRDS(args[1]))
d <- D[startsWith(D$location_name, paste0("AFR::", args[2], "::")) & D$spatial_scale == args[3], ]
d <- d[!(d$phantom %in% TRUE), ]
d$TL <- as.character(as.Date(d$TL)); d$TR <- as.character(as.Date(d$TR))
keep <- c("location_name", "TL", "TR", "sCh", "cCh", "deaths", "observation_collection_id",
          "original_location_name", "location_period_id", "composite_loc")
write.csv(d[, keep], args[4], row.names = FALSE, na = "", fileEncoding = "UTF-8")
'''


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def num(v):
    if v in ("", None):
        return ""
    f = float(v)
    return str(int(f)) if f == int(f) else f"{f:g}"


def baseline_weights(iso):
    """confidence_weight of the baseline's rows per JHU collection UID (mode)."""
    w = defaultdict(Counter)
    f = BASE / "data" / iso / "cholera_data_jhu.csv"
    if f.exists():
        for r in csv.DictReader(open(f, newline="", encoding="utf-8")):
            src = r.get("source", "")
            if "(UID: " in src:
                w[src.split("(UID: ")[1].rstrip(")")][r["confidence_weight"]] += 1
    return {uid: c.most_common(1)[0][0] for uid, c in w.items()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--iso", default="COD")
    ap.add_argument("--level", default="admin2", help="JHU spatial_scale to import (default admin2)")
    ap.add_argument("--archive", default=str(ARCHIVE))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    iso = a.iso.upper()
    arch = Path(a.archive)
    if not arch.exists():
        sys.exit(f"archive not found: {arch}")
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "export.csv"
        rs = Path(td) / "export.R"
        rs.write_text(R_EXPORT)
        subprocess.run(["Rscript", str(rs), str(arch), iso, a.level, str(out)], check=True)
        raw = list(csv.DictReader(open(out, newline="", encoding="utf-8")))

    weights = baseline_weights(iso)
    rows, skipped = [], Counter()
    for r in raw:
        try:
            tl, tr = date.fromisoformat(r["TL"]), date.fromisoformat(r["TR"])
        except ValueError:
            skipped["bad date"] += 1
            continue
        if not 6 <= (tr - tl).days <= 7:
            skipped["not weekly"] += 1
            continue
        if r["sCh"] == "":
            skipped["no sCh"] += 1
            continue
        if r["composite_loc"] == "TRUE" or "(" in r["location_name"]:
            skipped["composite"] += 1
            continue
        rows.append(r)
    rows.sort(key=lambda r: (r["location_name"], r["TL"], r["TR"], r["observation_collection_id"]))

    out_rows, per_coll = [], defaultdict(list)
    for i, r in enumerate(rows, 1):
        cid = r["observation_collection_id"]
        sch, deaths = num(r["sCh"]), num(r["deaths"])
        cfr = ""
        if deaths != "" and float(sch) > 0:
            cfr = f"{100 * float(deaths) / float(sch):.2f}"
        uid = cid.split(";")[0]
        notes = (f"Imported from the JHU public surveillance archive (OSF), observation collection {cid}; "
                 f"original location '{r['original_location_name']}'; location_period_id {r['location_period_id']}. "
                 f"Weekly row, JHU phantom rows excluded. Primary: True, Phantom: False. "
                 f"Read only by the sub-national builders (py/import_jhu_archive.py).")
        out_rows.append({
            "Index": f"A{i}", "Location": r["location_name"], "TL": r["TL"], "TR": r["TR"],
            "deaths": deaths, "sCh": sch, "cCh": num(r["cCh"]), "CFR": cfr, "reporting_date": r["TR"],
            "source_index": f"OSF{cid}", "source": f"JHU public surveillance archive (UID: {cid})",
            "confidence_weight": weights.get(uid, "0.9"), "processing_notes": notes, "source_database": "JHU"})
        per_coll[cid].append(r)

    digest = sha256(arch)
    meta = []
    for cid, rs_ in sorted(per_coll.items()):
        pos = sum(1 for r in rs_ if float(r["sCh"]) > 0)
        meta.append({
            "Index": f"OSF{cid}", "Source": f"JHU public surveillance archive (UID: {cid})",
            "URL": "MOSAIC-data/raw/JHU/osfstorage-archive/Public_surveillance_dataset.rds",
            "Description": (f"{len(rs_)} weekly {a.level} rows ({pos} with cases), phantom rows excluded; "
                            f"archive sha256 {digest[:16]}; imported {date.today().isoformat()}"),
            "TL": min(r["TL"] for r in rs_), "TR": max(r["TR"] for r in rs_),
            "Reliability_Level": "1", "source_database": "JHU"})

    print(f"{iso} {a.level}: {len(raw)} archive rows, {len(out_rows)} written, skipped {dict(skipped)}")
    print(f"  by year: {dict(sorted(Counter(r['TL'][:4] for r in out_rows).items()))}")
    print(f"  collections: {[(m['Index'], m['Description'].split(';')[0]) for m in meta]}")
    if a.dry_run:
        return
    d = BASE / "data" / iso
    with open(d / "cholera_data_jhu_archive.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(out_rows)
    with open(d / "metadata_jhu_archive.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=META_COLS)
        w.writeheader()
        w.writerows(meta)
    print(f"  wrote data/{iso}/cholera_data_jhu_archive.csv and data/{iso}/metadata_jhu_archive.csv")


if __name__ == "__main__":
    main()
