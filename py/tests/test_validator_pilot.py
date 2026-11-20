"""Pilot validator rules: tag enforced, no zero rows, AGE warning, prefix check."""
import csv
import importlib.util
import sys
from pathlib import Path

import pytest

PY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PY))


def _load():
    spec = importlib.util.spec_from_file_location("vq_test", PY / "validate_quality.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _fixture(tmp, rows):
    d = tmp / "NPL"
    d.mkdir(parents=True)
    vq = _load()
    with open(d / "metadata_ai.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=vq.META_COLUMNS)
        w.writeheader()
        w.writerow({"Index": 1, "Source": "EDCD sitrep", "URL": "https://example.org/x",
                    "Reliability_Level": "Level 1", "source_database": "AI"})
    with open(d / "cholera_data_ai.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=vq.DATA_COLUMNS)
        w.writeheader()
        for i, r in enumerate(rows, start=1):
            base = {"Index": i, "Location": "SEAR::NPL", "TL": "2022-06-01", "TR": "2022-06-30",
                    "reporting_date": "2022-07-05", "source_index": 1, "source": "EDCD sitrep",
                    "confidence_weight": 0.9, "source_database": "AI",
                    "processing_notes": "[NPL-PILOT] Source states: 'x' - interpreted as 5 sCh cases"}
            base.update(r)
            w.writerow(base)
    vq.DATA = tmp
    return vq


def _checks(vq):
    rep = vq.Report({})
    vq.validate_country("NPL", rep)
    return {(f["severity"], f["check"]) for f in rep.findings}


def test_clean_row_passes(tmp_path):
    vq = _fixture(tmp_path, [{"sCh": 5}])
    assert not [c for c in _checks(vq) if c[0] == "ERROR"]


def test_missing_tag_is_error(tmp_path):
    vq = _fixture(tmp_path, [{"sCh": 5, "processing_notes": "Source states: 'x' - interpreted as 5 sCh"}])
    assert ("ERROR", "pilot_tag_missing") in _checks(vq)


def test_zero_row_is_error(tmp_path):
    vq = _fixture(tmp_path, [{"sCh": 0, "deaths": 0,
                              "processing_notes": "[NPL-PILOT] Source confirms zero. Evidence type: Documented_Absence"}])
    assert ("ERROR", "pilot_zero_row") in _checks(vq)


def test_age_mention_warns_but_village_does_not(tmp_path):
    vq = _fixture(tmp_path, [
        {"sCh": 5, "processing_notes": "[NPL-PILOT] Source states: '5 AGE cases' - interpreted as 5 sCh"},
        {"sCh": 6, "TL": "2022-07-01", "TR": "2022-07-31",
         "processing_notes": "[NPL-PILOT] Source states: 'village outbreak' - interpreted as 6 sCh"},
    ])
    rep = vq.Report({})
    vq.validate_country("NPL", rep)
    rows = [f["row"] for f in rep.findings if f["check"] == "pilot_age_mention"]
    assert rows == [2]


def test_afr_prefix_rejected_for_nepal(tmp_path):
    vq = _fixture(tmp_path, [{"sCh": 5, "Location": "AFR::NPL"}])
    assert ("ERROR", "location_prefix") in _checks(vq)
