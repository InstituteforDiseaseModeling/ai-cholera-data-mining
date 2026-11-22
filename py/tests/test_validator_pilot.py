"""Pilot validator rules: tag enforced, no zero rows, AGE warning, prefix check,
count-basis warning judged from the row's source."""
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


def _fixture(tmp, rows, extra_meta=(), count_basis=None):
    d = tmp / "NPL"
    d.mkdir(parents=True)
    vq = _load()
    with open(d / "metadata_ai.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=vq.META_COLUMNS)
        w.writeheader()
        w.writerow({"Index": 1, "Source": "EDCD sitrep", "URL": "https://example.org/x",
                    "Reliability_Level": "Level 1", "source_database": "AI"})
        for m in extra_meta:
            w.writerow({"Reliability_Level": "Level 1", "source_database": "AI", **m})
    # Never read the real reference/count_basis/NPL.csv from a test.
    cb = tmp / "count_basis"
    cb.mkdir()
    if count_basis:
        with open(cb / "NPL.csv", "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["source_key", "year_from", "year_to", "field", "basis", "status", "evidence"])
            w.writerows(count_basis)
    vq.COUNT_BASIS_DIR = cb
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


WER = {"Index": 2, "Source": "WHO Weekly Epidemiological Record Vol 97 No 37 (16 Sep 2022): "
       "Cholera annual report 2021", "URL": "https://example.org/wer9737",
       "Data_Type": "WHO annual cholera report (multi-country)"}


def _basis_rows(vq):
    rep = vq.Report({})
    vq.validate_country("NPL", rep)
    return [f["row"] for f in rep.findings if f["check"] == "pilot_count_basis_missing"]


def test_wer_mention_in_notes_does_not_warn(tmp_path):
    """Quoting a WER total as a cross-check does not make the row's value a WHO figure."""
    vq = _fixture(tmp_path, [{"sCh": 77, "processing_notes":
        "[NPL-PILOT] Source states: '77 cases' - interpreted as 77 sCh. Cross-check: WER "
        "annual cholera report 2022 and WHO annual total also give 77."}])
    assert _basis_rows(vq) == []


def test_wer_source_without_count_basis_entry_warns(tmp_path):
    vq = _fixture(tmp_path, [{"sCh": 1609, "source_index": 2, "source": WER["Source"],
                              "TL": "2021-01-01", "TR": "2021-12-31", "reporting_date": "2022-09-16"}],
                  extra_meta=[WER])
    assert _basis_rows(vq) == [2]  # CSV line 2 = first data row


def test_wer_source_with_count_basis_entry_passes(tmp_path):
    vq = _fixture(tmp_path, [{"sCh": 1609, "source_index": 2, "source": WER["Source"],
                              "TL": "2021-01-01", "TR": "2021-12-31", "reporting_date": "2022-09-16"}],
                  extra_meta=[WER],
                  count_basis=[["AI:2", 2021, 2021, "sCh", "suspected", "verified", "quote"]])
    assert _basis_rows(vq) == []


def test_wer_source_detected_by_url_alone(tmp_path):
    m = {"Index": 2, "Source": "ReliefWeb mirror of a WHO report", "Data_Type": "report",
         "URL": "https://reliefweb.int/report/world/weekly-epidemiological-record-wer-16-september-2022-vol"}
    vq = _fixture(tmp_path, [{"cCh": 10, "source_index": 2, "source": m["Source"]}], extra_meta=[m])
    assert _basis_rows(vq) == [2]  # CSV line 2 = first data row
