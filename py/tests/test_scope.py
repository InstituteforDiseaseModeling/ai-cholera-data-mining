"""Scope helpers: the 40 stay the default; pilots only when named."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pytest  # noqa: E402
import scope  # noqa: E402


def test_mosaic_is_forty_and_excludes_pilots():
    m = scope.mosaic_isos()
    assert len(m) == 40
    assert "NPL" not in m


def test_npl_is_pilot_only():
    assert scope.pilot_isos() == ["NPL"]
    assert scope.is_pilot("NPL") and scope.in_scope("NPL")


def test_resolve_defaults_to_forty():
    assert scope.resolve_isos([]) == scope.mosaic_isos()
    assert scope.resolve_isos(None) == scope.mosaic_isos()


def test_resolve_accepts_named_pilot_and_rejects_others():
    assert scope.resolve_isos(["npl", "ETH"]) == ["NPL", "ETH"]
    with pytest.raises(ValueError):
        scope.resolve_isos(["IND"])
    with pytest.raises(ValueError):
        scope.resolve_isos(["BGD"])


def test_prefixes():
    assert scope.location_prefix("ETH") == "AFR"
    assert scope.location_prefix("NPL") == "SEAR"
    # Somalia stays AFR-only until its own reviewed change (plan, Phase 7).
    assert scope.accept_prefixes("SOM") == ["AFR"]
    assert scope.location_belongs("SEAR::NPL::Bagmati", "NPL")
    assert scope.location_belongs("SEAR::NPL", "NPL")
    assert not scope.location_belongs("AFR::NPL", "NPL")
    assert not scope.location_belongs("SEAR::NPLX", "NPL")
    assert not scope.location_belongs("EMR::SOM", "SOM")
    assert scope.national_re("NPL").match("SEAR::NPL")
    assert not scope.national_re("NPL").match("SEAR::NPL::Koshi")


def test_settings():
    s = scope.settings("NPL")
    assert s["zero_policy"] == "none" and s["count_basis_table"] is True
    assert s["template_pool"] == "none"
    d = scope.settings("AGO")
    assert d["zero_policy"] == "default" and d["template_pool"] == "africa"
    assert d["count_basis_table"] is False
