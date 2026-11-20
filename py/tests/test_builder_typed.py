"""Typed builder path (pilot countries): count types kept apart, no zeros,
multi-week totals undistributed. Uses a synthetic NPL fixture in a temp dir -
never data/NPL/, which update_dashboard.sh would auto-commit."""
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


def _write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=DATA_COLS)
        w.writeheader()
        for i, r in enumerate(rows, start=1):
            w.writerow({"Index": i, "confidence_weight": 0.9, "processing_notes": "Primary: True",
                        **r})


def _row(tl, tr, sch="", cch="", deaths="", source="", sidx="1", db="JHU"):
    return {"Location": "SEAR::NPL", "TL": tl, "TR": tr, "sCh": sch, "cCh": cch,
            "deaths": deaths, "source": source, "source_index": sidx, "source_database": db}


@pytest.fixture()
def bwt(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("bwt_test", PY / "build_weekly_timeseries.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    data = tmp_path / "data"
    d = data / "NPL"
    who = "WHO Cholera Surveillance Dashboard (2024)"
    annual = "WHO Annual Cholera Report (UID: 436)"
    _write(d / "cholera_data_who.csv", [
        _row("2024-06-03", "2024-06-09", sch=10, source=who, db="WHO"),
        _row("2024-06-10", "2024-06-16", sch=0, source=who, db="WHO"),          # zero week
    ])
    _write(d / "cholera_data_jhu.csv", [
        _row("2016-01-01", "2016-12-31", sch=169, source=annual),                 # confirmed-only annual
        _row("2020-01-01", "2020-12-31", sch=0, source=annual),                   # national zero year
        _row("2021-01-01", "2021-12-31", sch=1609, source=annual),                # suspected annual
        _row("2011-01-01", "2011-12-31", sch=4577, cch=3,
             source="JHU Cholera Database (UID: 21301)"),                         # sCh is AGE
        _row("2024-07-19", "2024-07-19", sch=1, cch=1, source="JHU Cholera Database (UID: 21542)"),
        _row("2024-07-20", "2024-07-20", sch=0, cch=0, source="JHU Cholera Database (UID: 21542)"),
        _row("2013-01-01", "2013-12-31", sch=50, source="JHU Cholera Database (UID: 99999)"),  # untyped
    ])
    _write(d / "cholera_data_ai.csv", [
        _row("2021-08-02", "2021-08-08", cch=3, source="EDCD EWARS", sidx="1", db="AI"),
        _row("2021-10-04", "2021-12-07", sch=2023, source="EDCD sitrep", sidx="2", db="AI"),
    ])
    cb = tmp_path / "count_basis"
    cb.mkdir()
    with open(cb / "NPL.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["source_key", "year_from", "year_to", "field", "basis", "status", "evidence"])
        w.writerows([
            ["WHO:dashboard", 2023, 2025, "sCh", "suspected", "provisional", "test"],
            ["JHU:436", 2016, 2016, "sCh", "confirmed", "inferred", "test"],
            ["JHU:436", 2020, 2021, "sCh", "suspected", "provisional", "test"],
            ["JHU:21301", 2011, 2014, "sCh", "age", "provisional", "test"],
            ["JHU:21301", 2011, 2014, "cCh", "confirmed", "provisional", "test"],
            ["JHU:21542", 2022, 2024, "sCh", "confirmed", "inferred", "test"],
        ])
    monkeypatch.setattr(m, "DATA_DIR", data)
    monkeypatch.setattr(m, "COUNT_BASIS_DIR", cb)
    monkeypatch.setattr(m, "SERIES_END", date(2026, 11, 18))
    return m


def _run(bwt):
    diag = {}
    s = bwt.process_country("NPL", (None, "undistributed"), diag)
    return s, diag


def test_npl_takes_typed_path(bwt):
    s, diag = _run(bwt)
    assert diag.get("typed") is True


def test_confirmed_never_in_suspected(bwt):
    s, diag = _run(bwt)
    # 2016 confirmed-only annual and the 21542 daily confirmed count stay out
    assert not any(e["monday"].year == 2016 for e in s.values())
    jul = date(2024, 7, 15)
    assert not any(e["monday"] == jul for e in s.values())
    c = diag["confirmed"]
    assert sum(e["sch"] for e in c.values()) == pytest.approx(1 + 3)   # 21542 day + EWARS week
    assert {e["method"] for e in c.values()} == {"observed"}
    totals = {(p["series"], p["source_key"], p["TL"][:4]): p["total"] for p in diag["periods"]}
    assert totals[("confirmed", "JHU:436", "2016")] == 169
    assert totals[("confirmed", "JHU:21301", "2011")] == 3


def test_no_zero_weeks_anywhere(bwt):
    s, diag = _run(bwt)
    for ser in (s, diag["confirmed"]):
        assert not any(e["sch"] == 0 for e in ser.values())
        assert not ({e["method"] for e in ser.values()} & {"assumed_zero", "inferred_zero",
                                                           "documented_zero"})
    reasons = [h["reason"] for h in diag["holdout"]]
    assert sum("zero row" in r for r in reasons) == 3        # WHO week, 2020 annual, 21542 day


def test_multiweek_totals_undistributed(bwt):
    s, diag = _run(bwt)
    und = [e for e in s.values() if e["method"] == "undistributed"]
    assert und and all(e["sch"] is None for e in und)
    firsts = sorted(e["period_total"] for e in und if e.get("period_total"))
    # Oct-Dec AI total claims its weeks first (finer); the 2021 annual claims the rest
    assert firsts == [1609, 2023]
    assert not any(e["method"].startswith("fourier") for e in s.values())


def test_age_and_untyped_rows_held_out(bwt):
    s, diag = _run(bwt)
    h = {(x["source_key"], x["TL"][:4], x["field"]): x["reason"] for x in diag["holdout"]}
    assert "age" in h[("JHU:21301", "2011", "sCh")]
    assert "unresolved" in h[("JHU:99999", "2013", "sCh")]
    assert not any(e["monday"].year == 2013 for e in s.values())


def test_suspected_observed_week_kept(bwt):
    s, diag = _run(bwt)
    obs = [e for e in s.values() if e["method"] == "observed"]
    assert [e["sch"] for e in obs] == [10]


def test_outputs_written(bwt, tmp_path):
    s, diag = _run(bwt)
    out = tmp_path / "out"
    bwt.write_typed_outputs("NPL", s, diag, out)
    names = sorted(p.name for p in (out / "NPL").iterdir())
    assert names == ["builder_holdout.csv", "cholera_period_totals_NPL.csv",
                     "cholera_weekly_NPL.csv", "cholera_weekly_confirmed_NPL.csv"]
    hdr = (out / "NPL" / "cholera_weekly_confirmed_NPL.csv").read_text().splitlines()[0]
    assert "cCh" in hdr and "sCh" not in hdr       # MOSAIC-pkg's reader needs sCh, so skips it
