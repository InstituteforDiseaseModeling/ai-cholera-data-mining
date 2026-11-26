"""Validator rules switched on by Bangladesh's settings (strict_basis,
warn_estimate_terms) and the sentinel-positivity sidecar. Synthetic fixture in
a temp dir; never data/BGD/ or the real count-basis table."""
import csv
import importlib.util
import sys
from pathlib import Path

PY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PY))

NOTE = "[BGD-PILOT] Source states: 'x' - interpreted as 5 sCh cases"


def _load():
    spec = importlib.util.spec_from_file_location("vq_bgd", PY / "validate_quality.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _fixture(tmp, rows, iso="BGD", count_basis=(), sentinel=None):
    d = tmp / iso
    d.mkdir(parents=True)
    vq = _load()
    with open(d / "metadata_ai.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=vq.META_COLUMNS)
        w.writeheader()
        w.writerow({"Index": 1, "Source": "IEDCR outbreak report", "URL": "https://example.org/x",
                    "Reliability_Level": "Level 1", "source_database": "AI"})
    cb = tmp / "count_basis"
    cb.mkdir()
    with open(cb / f"{iso}.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["source_key", "year_from", "year_to", "field", "basis", "status", "coverage",
                    "evidence"])
        w.writerows(count_basis)
    vq.COUNT_BASIS_DIR = cb
    tag = "[BGD-PILOT]" if iso == "BGD" else "[NPL-PILOT]"
    with open(d / "cholera_data_ai.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=vq.DATA_COLUMNS)
        w.writeheader()
        for i, r in enumerate(rows, start=1):
            base = {"Index": i, "Location": f"SEAR::{iso}", "TL": "2022-06-01", "TR": "2022-06-30",
                    "reporting_date": "2022-07-05", "source_index": 1,
                    "source": "IEDCR outbreak report", "confidence_weight": 0.9, "sCh": 5,
                    "source_database": "AI", "processing_notes": NOTE.replace("[BGD-PILOT]", tag)}
            base.update(r)
            w.writerow(base)
    if sentinel is not None:
        with open(d / vq.SENTINEL_FILE, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=vq.SENTINEL_COLUMNS)
            w.writeheader()
            for r in sentinel:
                w.writerow({"Location": "SEAR::BGD::Dhaka::Dhaka", "TL": "2019-01-07",
                            "TR": "2019-01-13", "site": "icddr,b Dhaka hospital", "tested": 40,
                            "positive": 6, "test_method": "culture", "serogroup": "O1",
                            "sampling": "2% systematic", "source_index": 1,
                            "source": "IEDCR outbreak report", "processing_notes": "x", **r})
    vq.DATA = tmp
    return vq


def _checks(vq, iso="BGD"):
    rep = vq.Report({})
    vq.validate_country(iso, rep)
    return {(f["severity"], f["check"]) for f in rep.findings}


def test_strict_national_row_without_entry_warns(tmp_path):
    vq = _fixture(tmp_path, [{}])
    assert ("WARN", "pilot_count_basis_missing") in _checks(vq)


def test_strict_row_with_entry_or_subnational_passes(tmp_path):
    vq = _fixture(tmp_path, [{}, {"Location": "SEAR::BGD::Dhaka", "TL": "2022-07-01",
                                  "TR": "2022-07-31", "reporting_date": "2022-08-05"}],
                  count_basis=[["AI:1", 2022, 2022, "sCh", "suspected", "verified", "", "x"]])
    assert ("WARN", "pilot_count_basis_missing") not in _checks(vq)


def test_estimate_mention_warns_on_national_rows_only(tmp_path):
    vq = _fixture(tmp_path, [{"processing_notes": NOTE + " Estimated burden 110,000 a year."}])
    assert ("WARN", "pilot_estimate_mention") in _checks(vq)
    vq = _fixture(tmp_path / "b", [{"Location": "SEAR::BGD::Dhaka",
                                    "processing_notes": NOTE + " estimated"}])
    assert ("WARN", "pilot_estimate_mention") not in _checks(vq)


def test_nepal_settings_unaffected(tmp_path):
    vq = _fixture(tmp_path, [{"processing_notes": NOTE.replace("[BGD-PILOT]", "[NPL-PILOT]")
                              + " estimated"}], iso="NPL")
    c = _checks(vq, "NPL")
    assert ("WARN", "pilot_estimate_mention") not in c
    assert ("WARN", "pilot_count_basis_missing") not in c


def test_sentinel_sidecar_checks(tmp_path):
    vq = _fixture(tmp_path, [{}], sentinel=[{}])
    assert not {c for c in _checks(vq) if c[1].startswith("sentinel_")}
    vq = _fixture(tmp_path / "b", [{}], sentinel=[
        {"positive": 50},                                  # > tested
        {"TL": "2019-02-01", "TR": "2019-01-01"},          # reversed
        {"Location": "SEAR::NPL"},                         # wrong country
        {"source_index": 9},                               # not in metadata
    ])
    c = {x[1] for x in _checks(vq) if x[0] == "ERROR"}
    assert {"sentinel_positive_gt_tested", "sentinel_dates", "sentinel_location",
            "sentinel_source_index"} <= c
