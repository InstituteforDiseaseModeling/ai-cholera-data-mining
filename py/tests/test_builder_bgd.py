"""Typed builder, Bangladesh settings: the count-basis `coverage` column holds a
whole row (both fields) out of the national series, and strict_basis holds out
every untyped national value, AI rows included. Synthetic fixture in a temp dir;
never data/BGD/."""
import csv
import importlib.util
import sys
from datetime import date
from pathlib import Path

import pytest

PY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PY))

DATA_COLS = ["Index", "Location", "TL", "TR", "deaths", "sCh", "cCh", "CFR", "reporting_date",
             "source_index", "source", "confidence_weight", "processing_notes", "source_database"]
CB_COLS = ["source_key", "year_from", "year_to", "field", "basis", "status", "coverage", "evidence"]


def _write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=DATA_COLS)
        w.writeheader()
        for i, r in enumerate(rows, start=1):
            w.writerow({"Index": i, "confidence_weight": 0.9,
                        "processing_notes": "Primary: True [BGD-PILOT]", **r})


def _row(tl, tr, sch="", cch="", source="", sidx="1", db="JHU", loc="SEAR::BGD"):
    return {"Location": loc, "TL": tl, "TR": tr, "sCh": sch, "cCh": cch, "deaths": "",
            "source": source, "source_index": sidx, "source_database": db}


def _cb(path, rows):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(CB_COLS)
        w.writerows(rows)


@pytest.fixture()
def bwt(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("bwt_bgd", PY / "build_weekly_timeseries.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    d = tmp_path / "data" / "BGD"
    _write(d / "cholera_data_who.csv", [
        _row("2024-06-03", "2024-06-09", sch=12, source="WHO Cholera Surveillance Dashboard (2024)",
             db="WHO"),                                                     # Cox's Bazar camps
    ])
    _write(d / "cholera_data_jhu.csv", [
        _row("2014-05-01", "2018-06-30", sch=26221, cch=1604,
             source="JHU Cholera Database (UID: 21363)"),                   # sentinel enrolment
        _row("1995-01-01", "1995-12-31", sch=2297,
             source="WHO Annual Cholera Report (UID: 429)"),                # typed suspected
        _row("2019-01-01", "2019-12-31", sch=503,
             source="WHO Annual Cholera Report (UID: 429)"),                # no entry
    ])
    _write(d / "cholera_data_ai.csv", [
        _row("2022-03-07", "2022-03-13", sch=40, cch=5, source="untyped report", sidx="1", db="AI"),
        _row("2021-08-02", "2021-08-08", sch=30, cch=4, source="typed report", sidx="2", db="AI"),
    ])
    cb = tmp_path / "count_basis"
    cb.mkdir()
    _cb(cb / "BGD.csv", [
        ["WHO:dashboard", 2023, 2026, "sCh", "suspected", "verified", "subset", "camps"],
        ["JHU:21363", 2014, 2018, "sCh", "age", "inferred", "sample", "enrolled"],
        ["JHU:429", 1995, 1995, "sCh", "suspected", "verified", "", "WER"],
        ["AI:2", 2021, 2021, "sCh", "suspected", "verified", "national", "x"],
        ["AI:2", 2021, 2021, "cCh", "confirmed", "verified", "national", "x"],
    ])
    monkeypatch.setattr(m, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(m, "COUNT_BASIS_DIR", cb)
    monkeypatch.setattr(m, "SERIES_END", date(2026, 11, 18))
    return m


def _run(bwt):
    diag = {}
    s = bwt.process_country("BGD", (None, "undistributed"), diag)
    return s, diag


def _held(diag):
    return {(h["source_key"], h["TL"][:4], h["field"]): h["reason"] for h in diag["holdout"]}


def test_coverage_holds_whole_row(bwt):
    s, diag = _run(bwt)
    h = _held(diag)
    # only sCh is typed for 21363, yet its cCh must not reach the confirmed series
    assert h[("JHU:21363", "2014", "sCh")] == "coverage sample - not a national count"
    assert h[("JHU:21363", "2014", "cCh")] == "coverage sample - not a national count"
    assert h[("WHO:dashboard", "2024", "sCh")] == "coverage subset - not a national count"
    assert not any(p["source_key"] == "JHU:21363" for p in diag["periods"])
    assert not any(e["monday"].year == 2024 for e in s.values())


def test_strict_basis_holds_untyped_values(bwt):
    s, diag = _run(bwt)
    h = _held(diag)
    assert "unresolved" in h[("AI:1", "2022", "sCh")]
    assert "unresolved" in h[("AI:1", "2022", "cCh")]
    assert "unresolved" in h[("JHU:429", "2019", "sCh")]
    assert not any(e["monday"].year == 2022 for e in s.values())
    assert not any(e["monday"].year == 2022 for e in diag["confirmed"].values())


def test_typed_national_values_kept(bwt):
    s, diag = _run(bwt)
    assert [e["sch"] for e in s.values() if e["method"] == "observed"] == [30]
    assert [e["sch"] for e in diag["confirmed"].values() if e["method"] == "observed"] == [4]
    totals = {(p["series"], p["source_key"], p["TL"][:4]): p["total"] for p in diag["periods"]}
    assert totals[("suspected", "JHU:429", "1995")] == 2297


def test_bad_coverage_rejected(bwt, tmp_path):
    _cb(tmp_path / "count_basis" / "BGD.csv",
        [["JHU:429", 1995, 1995, "sCh", "suspected", "verified", "camps", "x"]])
    with pytest.raises(SystemExit):
        bwt.load_count_basis("BGD")
