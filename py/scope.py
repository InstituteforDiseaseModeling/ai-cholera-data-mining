"""
Pipeline scope: which countries a script may process, and per-country settings.

Two sets:
  mosaic_isos()  the 40 MOSAIC framework countries (country_mapping.json
                 mosaic_framework=true). Every DEFAULT loop - run queue,
                 preflight, dashboard, supervisor, status page, gap files -
                 uses this set and nothing else.
  pilot_isos()   countries in reference/pipeline_countries.json with
                 pilot=true (currently NPL). They are processed only when a
                 caller names them explicitly; resolve_isos() enforces that.

settings(iso) merges the overlay's defaults with the country's overrides:
  location_prefix    prefix written on new rows ("AFR", "SEAR")
  accept_prefixes    prefixes read as this country (Somalia stays ["AFR"] for now)
  template_pool      "africa" (shares the regional/continental seasonal pools)
                     or "none" (multi-week totals are written undistributed)
  count_basis_table  builder uses only rows typed in reference/count_basis/{ISO}.csv
  zero_policy        "default" or "none" (no zero rows of any kind)

The overlay lives in its own file because py/get_iso_codes.py regenerates
country_mapping.json with a fixed schema and would wipe added fields.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "reference"
MAPPING = REF / "country_mapping.json"
OVERLAY = REF / "pipeline_countries.json"

_FALLBACK_DEFAULTS = {
    "location_prefix": "AFR",
    "accept_prefixes": ["AFR"],
    "template_pool": "africa",
    "count_basis_table": False,
    "zero_policy": "default",
}


@lru_cache(maxsize=None)
def _mapping():
    return json.loads(MAPPING.read_text())["countries"]


@lru_cache(maxsize=None)
def _overlay():
    if not OVERLAY.exists():
        return {"defaults": dict(_FALLBACK_DEFAULTS), "countries": {}}
    o = json.loads(OVERLAY.read_text())
    o.setdefault("defaults", {})
    o.setdefault("countries", {})
    return o


def mosaic_isos():
    """The 40 MOSAIC framework countries, sorted."""
    return sorted(k for k, v in _mapping().items() if v.get("mosaic_framework"))


def pilot_isos():
    """Pilot countries (processed only when named), sorted."""
    return sorted(k for k, v in _overlay()["countries"].items() if v.get("pilot"))


def in_scope(iso):
    return iso in mosaic_isos() or iso in pilot_isos()


def is_pilot(iso):
    return iso in pilot_isos()


def resolve_isos(requested=None):
    """Upper-case and validate explicitly requested ISO codes.

    No request -> the 40 MOSAIC countries (pilots are never implied).
    Raises ValueError naming any code that is neither MOSAIC nor pilot.
    """
    if not requested:
        return mosaic_isos()
    isos = [c.strip().upper() for c in requested if c and c.strip()]
    bad = [c for c in isos if not in_scope(c)]
    if bad:
        raise ValueError(f"not MOSAIC framework or pilot countries: {bad}")
    return isos


def country_meta(iso):
    """Mapping entry for a MOSAIC country, or the overlay entry for a pilot."""
    m = dict(_mapping().get(iso, {}))
    o = _overlay()["countries"].get(iso, {})
    for k in ("name", "region", "subregion"):
        if k in o:
            m[k] = o[k]
    return m


def country_name(iso):
    return country_meta(iso).get("name", iso)


def settings(iso):
    s = dict(_FALLBACK_DEFAULTS)
    s.update(_overlay()["defaults"])
    s.update(_overlay()["countries"].get(iso, {}))
    return s


def location_prefix(iso):
    return settings(iso)["location_prefix"]


def accept_prefixes(iso):
    return list(settings(iso)["accept_prefixes"])


def national_codes(iso):
    """Every Location string that means 'national' for this country."""
    return [f"{p}::{iso}" for p in accept_prefixes(iso)]


def all_prefixes():
    """Union of every prefix any in-scope country accepts or writes."""
    out = set()
    for iso in mosaic_isos() + pilot_isos():
        s = settings(iso)
        out.update(s["accept_prefixes"])
        out.add(s["location_prefix"])
    return sorted(out)


def location_belongs(loc, iso):
    """True when Location starts with an accepted prefix for iso."""
    loc = (loc or "").strip()
    return any(loc == c or loc.startswith(c + "::") for c in national_codes(iso))


def national_re(iso):
    """Regex matching the national Location code(s) for iso exactly."""
    alts = "|".join(re.escape(p) for p in accept_prefixes(iso))
    return re.compile(rf"^(?:{alts})::{re.escape(iso)}$")


def pilot_tag(iso):
    return settings(iso).get("pilot_tag")
