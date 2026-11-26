#!/usr/bin/env python3
"""
Build weekly cholera time series at province (ADM1) level for the 40 MOSAIC
countries, from counts REPORTED at province level or below. National totals are
never split across provinces.

Method (docs/technical/subnational-weekly-series-plan.md):

  Units      Current first-level units, reference/subnational/adm1_units.csv.
             Every historical name is resolved to a current unit through
             reference/subnational/adm1_aliases.csv (most recent boundaries for
             all years). A legacy unit that split with no majority successor,
             composite names ("(A|B)", "Multi_*") and unidentified names are not
             assigned; they go to data/{ISO}/cholera_adm1_unallocated_{ISO}.csv.

  Evidence   direct  - a row reported for the province itself.
             rollup  - rows for parts of the province (districts, or former
                       provinces merged into the current one) summed per source
                       document (source + source_index) and reporting period.
                       Used only where no direct row covers that week/period.

  Engine     The national evidence ladder, unchanged
             (build_weekly_timeseries.process_country): observed weeks >
             documented zeros and multi-week totals, finest span first, each
             distributing only its residual > inferred zeros. The national
             builder's assumed_zero gap fill is removed: at province level an
             unreported week stays missing.

  Seasonal   Multi-week totals are spread with a Fourier template (BIC-selected
  template   K). The province's own template where it has >= MIN_YEARS
             outbreak-years of weekly data; otherwise the country's national
             template (itself the regional or continental pool when the country
             is too sparse).

  Long totals Every week records source_span_days, the span of the row that
             filled it (7 for observed weeks), so weeks spread from multi-year
             totals can be filtered out. --max-spread-days N instead excludes
             positive totals longer than N days before the build (listed in
             cholera_adm1_long_totals_{ISO}.csv); the default spreads all of
             them, exactly as the national builder does.

  No rescaling: province series are not forced to sum to the national series.
  The comparison is written to cholera_adm1_reconciliation_{ISO}.csv.

Outputs per country (data/{ISO}/):
  cholera_adm1_weekly_{ISO}.csv
  cholera_adm1_reconciliation_{ISO}.csv
  cholera_adm1_unallocated_{ISO}.csv
  cholera_adm1_long_totals_{ISO}.csv
Summary: reference/subnational/province_build_summary.csv
"""

import argparse
import csv
import math
import re
import unicodedata
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_weekly_timeseries as btw  # noqa: E402
import scope  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SUB_DIR = BASE_DIR / "reference" / "subnational"
UNITS_CSV = SUB_DIR / "adm1_units.csv"
ALIASES_CSV = SUB_DIR / "adm1_aliases.csv"
ROW_OVERRIDES_CSV = "adm1_row_overrides.csv"   # single rows whose figure belongs elsewhere
CONTAINMENT_CSV = "adm1_containment.csv"       # sub-areas filed as siblings of the area containing them
EXCLUSIONS_CSV = "row_exclusions.csv"          # single rows left out of sub-national builds
ZERO_EXCLUSIONS_CSV = "source_zero_exclusions.csv"   # sources whose zeros are not trusted
SUMMARY_CSV = SUB_DIR / "province_build_summary.csv"

ASSIGNING = {"current", "alias", "renamed", "shifted"}   # raw name IS the unit
PART = {"part"}                                           # raw name lies inside the unit
UNASSIGNABLE = {"split", "composite", "unknown", "not_place"}
WHOLE_UNIT = {"current", "alias", "renamed"}              # raw name is exactly the unit
SHIFT_PARTIAL_CSV = "adm1_shift_partial.csv"   # shifted units that do NOT contain the whole successor
_SHIFT_PARTIAL = None


def zero_spreads(alias_row):
    """
    Whether a reported zero for this alias speaks for its whole current unit:
    exact units do; a 'shifted' former unit does too (it lost territory to new
    units, so it contains the current one), except where adm1_shift_partial.csv
    says it does not (pre-2024 Conakry, pre-2020 Ombella-M'Poko).
    """
    global _SHIFT_PARTIAL
    if alias_row["status"] in WHOLE_UNIT:
        return True
    if alias_row["status"] != "shifted":
        return False
    if _SHIFT_PARTIAL is None:
        _SHIFT_PARTIAL = set()
        f = SUB_DIR / SHIFT_PARTIAL_CSV
        if f.exists():
            with open(f, newline="", encoding="utf-8") as fh:
                _SHIFT_PARTIAL = {(r["iso"], r["raw_adm1"], r["valid_to"]): r.get("spread_to", "")
                                  for r in csv.DictReader(fh)}
    return (alias_row["iso"], alias_row["raw_adm1"], alias_row.get("valid_to", "")) not in _SHIFT_PARTIAL


def zero_spread_districts(alias_row):
    """For a partial shift (adm1_shift_partial.csv), the current districts the
    former unit wholly contained (its zero holds for these only); else None."""
    zero_spreads(alias_row)   # loads the table
    v = _SHIFT_PARTIAL.get((alias_row["iso"], alias_row["raw_adm1"], alias_row.get("valid_to", "")))
    return None if v is None else [x for x in v.split("|") if x]
MAX_SPREAD_DAYS = None   # None = spread every multi-week total (national behaviour)
STATUSES = ASSIGNING | PART | UNASSIGNABLE

WEEKLY_COLS = ["iso_code", "adm1_name", "adm1_code", "year", "iso_week", "week_start",
               "week_end", "sCh", "deaths", "source", "confidence_weight",
               "disaggregation_method", "evidence", "template", "source_span_days"]
RECON_COLS = ["iso_code", "year", "iso_week", "week_start", "national_sCh",
              "national_method", "provinces_sCh", "provinces_reporting",
              "provinces_observed", "ratio"]
LONG_COLS = ["iso_code", "adm1_name", "source_database", "Index", "Location", "TL", "TR",
             "days", "sCh", "deaths", "evidence"]
UNALLOC_COLS = ["iso_code", "source_database", "Index", "Location", "TL", "TR", "sCh",
                "deaths", "source_index", "status", "reason"]


# ---------------------------------------------------------------------------
# Reference tables
# ---------------------------------------------------------------------------

def load_units(path=UNITS_CSV):
    units = defaultdict(dict)   # iso -> adm1_name -> row
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            units[r["iso"]][r["adm1_name"]] = r
    return units


def load_aliases(path=ALIASES_CSV):
    """{(iso, raw_adm1, raw_child): [row, ...]} - several rows when eras differ."""
    al = defaultdict(list)
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            r["_from"] = btw.parse_date(r.get("valid_from", "")) or date.min
            r["_to"] = btw.parse_date(r.get("valid_to", "")) or date.max
            al[(r["iso"], r["raw_adm1"], r.get("raw_child", ""))].append(r)
    return al


def load_row_overrides(path):
    """{(iso, source_database, Index): (Location, TL, adm1_name)} for individual rows."""
    ov = {}
    if path.exists():
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                ov[(r["iso"], r["source_database"], r["Index"])] = (r["Location"], r["TL"], r["adm1_name"])
    return ov


def _key(name):
    return name.replace(" ", "_").lower()


def load_containment(path):
    """{(iso, raw_adm1, container_key): {contained_key, ...}} - names compared space/underscore-blind."""
    c = defaultdict(set)
    if path.exists():
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                c[(r["iso"], r["raw_adm1"], _key(r["container"]))].add(_key(r["contained"]))
    return c


def _contains(containment, a, b):
    """True when location a contains location b (descendant, or a declared sub-area sibling)."""
    if b.startswith(a + "::"):
        return True
    pa, pb = a.split("::"), b.split("::")
    if len(pa) >= 4 and len(pb) >= 4 and pa[:3] == pb[:3]:
        inner = containment.get((pa[1], pa[2], _key(pa[3])), ())
        return _key(pb[3]) in inner
    return False


def load_exclusions(path):
    """{(iso, source_database, Index)} of rows left out of the sub-national builds."""
    out = set()
    if path.exists():
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                out.add((r["iso"], r["source_database"], r["Index"]))
    return out


def load_zero_exclusions(path):
    """[(iso, source_database, source_match)]: sources whose ZERO rows are not used."""
    out = []
    if path.exists():
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                out.append((r["iso"], r["source_database"], r["source_match"]))
    return out


def zero_excluded(r, iso, zero_excl):
    return r["sch"] == 0 and any(i == iso and s_ == r["source"] and m in r["src_name"]
                                 for i, s_, m in zero_excl)


def drop_restatements(rows):
    """
    Drop a positive row that restates a longer same-source total: same value,
    same end date (+-1 day), shorter span (SOM JHU 10-12 day rows ending 31 Dec
    that repeat the annual totals, which put a year of cases into one week).
    """
    pos = [r for r in rows if r["sch"] > 0]
    drop = set()
    for r in pos:
        for q in pos:
            # only the very short restatement (<= 14 days) of a genuinely long total
            # (>= 90 days, >= 4x): a 25-day sitrep window and a Jan-Apr summary of
            # one outbreak (KEN Bomet 2015) are both reports, and a 5-week row with
            # a weekly value (MWI 2018) is a mis-dated week, not a total
            if q is not r and q["source"] == r["source"] and q["sch"] == r["sch"] \
                    and abs((q["tr"] - r["tr"]).days) <= 1 and _span(r) <= 14 \
                    and _span(q) >= max(90, 4 * max(_span(r), 1)):
                drop.add(id(r))
                break
    return [r for r in rows if id(r) not in drop], len(drop)


def drop_contradicted_zeros(rows):
    """
    Drop a weekly or sub-weekly zero where a positive report of a week or less for
    the same unit falls in that week: a zero-filled weekly table (NGA 2018 LGA
    tables, 99% zeros) otherwise beats a positive daily sum in its week. Zeros
    inside a longer positive total are kept (they are genuine zero weeks); the
    engine runs with zero_coverage=False so they cannot suppress that total.
    """
    pos = [r for r in rows if r["sch"] > 0 and _span(r) <= 7]
    keep, n = [], 0
    for r in rows:
        if r["sch"] == 0 and _span(r) <= 7:
            mid = r["tl"] + (r["tr"] - r["tl"]) / 2
            if any(p["tl"] <= mid <= _end(p) for p in pos):
                n += 1
                continue
        keep.append(r)
    return keep, n


def _pick(rows, tl, strict=False):
    """Alias row whose era contains tl. With strict, None when no era does (a
    child row then falls back to its parent); otherwise the closest era."""
    for r in rows:
        if r["_from"] <= tl <= r["_to"]:
            return r
    if strict:
        return None
    return min(rows, key=lambda r: min(abs((tl - r["_from"]).days) if r["_from"] != date.min else 10**9,
                                       abs((tl - r["_to"]).days) if r["_to"] != date.max else 10**9))


def resolve(aliases, iso, parts, tl):
    """
    parts = Location split on '::' (prefix, ISO, adm1, [child, ...]).
    Returns (unit or None, level 'direct'|'part', status, reason).
    A child-specific alias wins over its parent's alias. A child alias that IS a
    current unit (KEN Coast::Mombasa = Mombasa county) is a direct row.
    """
    raw1 = parts[2]
    child = parts[3] if len(parts) > 3 else ""
    if child and (iso, raw1, child) in aliases:
        rows_c = aliases[(iso, raw1, child)]
        a = _pick(rows_c, tl, strict=True)
        if a is not None:
            if a["status"] in ASSIGNING and a["adm1_name"]:
                # A child that IS the province (KEN Coast::Mombasa) is a direct row.
                # A 'shifted' child is the province only when the same child names
                # the unit itself in another era (KEN Eastern::Machakos pre-1992);
                # otherwise it is a district whose majority lies in the province
                # (SLE Northern::Bombali pre-2017) and is a part.
                is_unit = a["status"] != "shifted" or any(
                    x["status"] in {"current", "alias", "renamed"} for x in rows_c)
                return a["adm1_name"], ("direct" if len(parts) == 4 and is_unit else "part"), a["status"], ""
            if a["status"] in PART and a["adm1_name"]:
                return a["adm1_name"], "part", a["status"], ""
            return None, None, a["status"], f"child {a['status']}"
    rows = aliases.get((iso, raw1, ""))
    if not rows:
        return None, None, "unmapped", "no alias row"
    a = _pick(rows, tl)
    st = a["status"]
    if st in ASSIGNING and a["adm1_name"]:
        return a["adm1_name"], ("direct" if not child else "part"), st, ""
    if st in PART and a["adm1_name"]:
        return a["adm1_name"], "part", st, ""
    return None, None, st, st


def zero_targets(aliases, iso, parts, tl, split_children):
    """
    Provinces a reported ZERO for an unassignable area speaks for. Zero cases in
    an area means zero in every part of it, so:
      - a zero for "(A|B|...)" in the province slot holds for each member that is
        itself a province (members that are districts say nothing about the rest
        of their province);
      - a zero for a split legacy unit holds for the successors its child rows
        identify, only when the unit has a single era (successors differ by era).
    Only province-slot rows qualify. Positive totals for such areas stay unallocated.
    """
    if len(parts) != 3:
        return set()
    raw1 = parts[2]
    if raw1.startswith("(") and raw1.endswith(")"):
        out = set()
        for m in raw1[1:-1].split("|"):
            rows = aliases.get((iso, m.split("##")[0], ""))
            if rows:
                a = _pick(rows, tl)
                if zero_spreads(a) and a["adm1_name"]:
                    out.add(a["adm1_name"])
        return out
    rows = aliases.get((iso, raw1, ""))
    if rows and len(rows) == 1 and rows[0]["status"] == "split":
        return set(split_children.get((iso, raw1), ()))
    return set()


def split_child_index(aliases):
    idx = defaultdict(set)
    for (iso, raw1, child), rows in aliases.items():
        if child:
            for a in rows:
                if a["status"] in ASSIGNING | PART and a["adm1_name"]:
                    idx[(iso, raw1)].add(a["adm1_name"])
    return idx


# ---------------------------------------------------------------------------
# Row loading (reuses the national parser through a location allow-list)
# ---------------------------------------------------------------------------

def load_country_rows(iso):
    """All sub-national rows of iso, parsed exactly as the national builder parses rows."""
    d = DATA_DIR / iso
    out = []
    orig = btw.scope.national_codes
    for src, label in (("who", "WHO"), ("jhu", "JHU"), ("ai", "AI")):
        f = d / f"cholera_data_{src}.csv"
        if not f.exists():
            continue
        with open(f, newline="", encoding="utf-8") as fh:
            locs = {r.get("Location", "").strip() for r in csv.DictReader(fh)}
        locs = {l for l in locs if l.count("::") >= 2 and l.split("::")[1] == iso}
        if not locs:
            continue
        btw.scope.national_codes = lambda _iso, _l=sorted(locs): _l
        try:
            rows = btw.load_national_rows(iso, src, d)
        finally:
            btw.scope.national_codes = orig
        for r in rows:
            r["source"] = label
            r["src_file"] = src
            r["tl0"], r["tr0"] = r["tl"], r["tr"]   # as reported, for the side files
        out.extend(rows)
    return out


def _end(r):
    return max(r["tr"], r["tl"] + timedelta(days=1))


def _span(r):
    return (r["tr"] - r["tl"]).days


def _length(r):
    return max((_end(r) - r["tl"]).days, 1)


def _overlap(a, b):
    return (min(_end(a), _end(b)) - max(a["tl"], b["tl"])).days


def rekey_weekly(r):
    """
    Put a 6-7 day row on the ISO week holding its midpoint (Monday-Sunday dates).
    The engine keys weekly rows by midpoint week too (since 2026-11-25); aligning
    the dates here also lets rollup grouping and cross-report merging see a
    Sunday-start and a Monday-start report of one week as the same period.
    """
    if 6 <= _span(r) <= 7:
        mon, sun = btw.isoweek_bounds(*btw._midpoint_week(r))
        if mon != r["tl"]:
            return dict(r, tl=mon, tr=sun)
    return r


_SUFFIX = re.compile(r"(sanitarydistrict|healthdistrict|districtsanitaire|zonedesante|healthzone|district|hd|zs|ds)$")


def _norm_seg(seg):
    s_ = unicodedata.normalize("NFKD", seg).encode("ascii", "ignore").decode().lower()
    s_ = re.sub(r"[^a-z0-9]", "", s_)
    return _SUFFIX.sub("", s_) or s_


def _segs(loc):
    """Normalised place names below the province slot (the slot itself for a
    district sitting in the province slot): spelling-blind identity of a part."""
    p = loc.split("::")
    return tuple(_norm_seg(x) for x in p[3:]) if len(p) > 3 else (_norm_seg(p[2]),)


def _leaf(loc):
    return loc.rsplit("::", 1)[-1]


def _parent(loc):
    return loc.rsplit("::", 1)[0]


def _members(loc):
    leaf = _leaf(loc)
    if leaf.startswith("(") and leaf.endswith(")"):
        return {m.split("##")[0] for m in leaf[1:-1].split("|")}
    return set()


def build_rollups(part_rows, containment=None):
    """
    Sum rows for parts of one province, per source document and period.
    Within a group: repeated rows of one location keep the max; a location whose
    ancestor is present is dropped (the ancestor includes it); a sibling named
    inside a composite part "(A|B)" is dropped (the composite includes it); and a
    place reported under two spellings keeps its max. Then rollups of the same
    source and period from different documents are merged when no place is
    shared (spelling-blind) or nested between them.
    """
    groups = defaultdict(list)
    for r in part_rows:
        groups[(r["source"], r["src_index"], r["tl"], r["tr"])].append(r)
    docs = []
    for (label, sidx, tl, tr), rs in groups.items():
        by_loc, by_leaf = {}, {}
        for r in rs:   # one place under two spellings (Lusaka::Lusaka, ZM-09::Lusaka) keeps the max
            k = _segs(r["location"])[-1]
            if k not in by_leaf or r["sch"] > by_leaf[k]["sch"]:
                by_leaf[k] = r
        for r in by_leaf.values():
            by_loc[r["location"]] = r
        locs = set(by_loc)
        containment = containment or {}
        keep = {l: r for l, r in by_loc.items()
                if not any(_contains(containment, a, l) for a in locs if a != l)}
        inside = set()
        for c in keep:
            mem = _members(c)
            if mem:
                inside |= {l for l in keep if l != c and _parent(l) == _parent(c) and _leaf(l) in mem}
        keep = [r for l, r in keep.items() if l not in inside]
        docs.append((label, sidx, tl, tr, keep))

    def make(label, sidx, tl, tr, keep):
        deaths = [r["deaths"] for r in keep if r["deaths"] is not None]
        return {
            "tl": tl, "tr": tr, "sch": sum(r["sch"] for r in keep), "has_count": True,
            "evidence": "documented" if all(r["evidence"] == "documented" for r in keep) else "none",
            "deaths": sum(deaths) if deaths else None,
            "conf": sum(r["conf"] for r in keep) / len(keep),
            "primary": all(r["primary"] for r in keep),
            "cch": None, "deaths_raw": "", "src_name": keep[0]["src_name"],
            "src_index": sidx, "row_index": "",
            # place key from the part set: the engine chains cumulative reports
            # only within one place, so rollups of different parts never chain
            "location": "ROLLUP::" + "|".join(sorted({"/".join(_segs(r["location"])) for r in keep})),
            "source": label, "src_file": keep[0]["src_file"],
            "locs": frozenset(r["location"] for r in keep), "n_parts": len(keep),
            "depth": Counter(len(r["location"].split("::")) for r in keep).most_common(1)[0][0],
            "rollup": True, "tl0": tl, "tr0": tr,
        }

    n_doc_max = defaultdict(int)   # most parts any one report lists, per reporting level
    for *_, k in docs:
        d = Counter(len(r["location"].split("::")) for r in k).most_common(1)[0][0]
        n_doc_max[d] = max(n_doc_max[d], len(k))
    by_period = defaultdict(list)
    for label, sidx, tl, tr, keep in docs:
        by_period[(label, tl, tr)].append(make(label, sidx, tl, tr, keep))
    out = []
    for key, rs in by_period.items():
        rs.sort(key=lambda r: -r["n_parts"])
        merged = []
        for r in rs:
            for m in merged:
                shared = ({x for l in m["locs"] for x in _segs(l)}
                          & {x for l in r["locs"] for x in _segs(l)})
                nested = any(_contains(containment, a, b) or _contains(containment, b, a)
                             for a in m["locs"] for b in r["locs"])
                if not shared and not nested:
                    m["sch"] += r["sch"]
                    if r["deaths"] is not None:
                        m["deaths"] = (m["deaths"] or 0.0) + r["deaths"]
                    m["locs"] = m["locs"] | r["locs"]
                    m["n_parts"] = len(m["locs"])
                    m["location"] = "ROLLUP::" + "|".join(sorted({"/".join(_segs(l)) for l in m["locs"]}))
                    m["primary"] = m["primary"] and r["primary"]
                    if r["evidence"] != "documented":
                        m["evidence"] = "none"
                    break
            else:
                merged.append(dict(r))
        out.extend(merged)
    return out, n_doc_max


def select_rollups(direct, rollups, n_doc_max):
    """
    Keep a rollup only where it adds evidence the province's own rows do not:
      - a rollup is 'complete' when it lists >= 80% of the most parts any single
        report lists for this province (and at least 2); a ZERO rollup that is
        not complete says nothing about the rest of the province and is dropped;
      - a weekly/daily rollup is dropped when a direct weekly row covers its week;
      - an incomplete rollup is dropped wherever a positive direct total overlaps
        it: a partial list is a lower bound, used only where the province
        reported no total of its own;
      - a complete multi-week rollup is dropped when a positive direct total of
        comparable span (0.5x-2x) covers >= 50% of it (a restatement); finer
        complete rollups inside a longer total are kept as nested evidence.
    Area-wide zeros never displace rollups.
    """
    def need(depth):
        m = n_doc_max.get(depth, 0)
        # former provinces in the province slot: a report listing all of them is
        # complete even when there are only 2; districts need at least 3 listed
        return max(2 if depth == 3 else 3, math.ceil(0.8 * m))
    direct_weeks, pos_aggs = set(), []
    for r in direct:
        if r.get("zero_broadcast"):
            continue
        if 6 <= _span(r) <= 7:
            direct_weeks.add(btw._midpoint_week(r))
        elif _span(r) > 7 and r["sch"] > 0:
            pos_aggs.append(r)
    kept = []
    for r in rollups:
        r["complete"] = r["n_parts"] >= need(r["depth"])
        if r["sch"] == 0 and not r["complete"]:
            continue
        if _span(r) <= 7 and btw._midpoint_week(r) in direct_weeks:
            continue
        if not r["complete"]:
            # A partial list is a lower bound for the province: it may stand in
            # only where the province reported no total of its own. Inside one it
            # would take the total's weeks first (ETH Somali 2017, COD Sud-Kivu
            # 2007), start false cumulative increments (MOZ Sofala 1998) or add
            # to a total it straddles (ZMB Lusaka 2010).
            if any(_overlap(a, r) > 0 for a in pos_aggs):
                continue
        elif _span(r) > 7:
            L = _length(r)
            if any(_overlap(a, r) >= 0.5 * L and 0.5 * L <= _length(a) <= 2 * L for a in pos_aggs):
                continue   # a complete list restating a comparable province total
        kept.append(r)
    return kept


def net_of_children_elsewhere(resolved, depth=3):
    """
    A province-slot row assigned to a unit can contain district rows of the same
    report that belong to another unit (ZMB Lusaka::Chirundu, a shifted legacy
    total's minority children). Those districts are counted where they belong, so
    subtract them from the parent row; drop the parent row if nothing is left.
    depth = Location depth of the parent rows (3 = province slot; 4 = district).
    """
    by_doc = defaultdict(list)
    for x in resolved:
        r = x[0]
        by_doc[(r["source"], r["src_index"], r["tl"], r["tr"])].append(x)
    adjusted = 0
    out = []
    for x in resolved:
        r, parts, unit, level = x[0], x[1], x[2], x[3]
        if unit is None or len(parts) != depth or r["sch"] <= 0:
            out.append(x)
            continue
        loc = r["location"]
        kids = [y for y in by_doc[(r["source"], r["src_index"], r["tl"], r["tr"])]
                if y[0]["location"].startswith(loc + "::") and y[2] is not None and y[2] != unit]
        kid_locs = {y[0]["location"] for y in kids}
        kids = [y for y in kids if not any(y[0]["location"].startswith(k + "::") for k in kid_locs)]
        if not kids:
            out.append(x)
            continue
        adjusted += 1
        sub = sum(y[0]["sch"] for y in kids)
        if r["sch"] - sub <= 0:
            continue
        d = r["deaths"]
        dk = sum(y[0]["deaths"] or 0.0 for y in kids)
        r = dict(r, sch=r["sch"] - sub, deaths=None if d is None else max(d - dk, 0.0))
        out.append((r,) + tuple(x[1:]))
    return out, adjusted


# ---------------------------------------------------------------------------
# Per-province series
# ---------------------------------------------------------------------------

def province_template(rows, national_template):
    weekly = [(r["tl"], r["tr"], r["sch"]) for r in rows
              if r["has_count"] and _span(r) <= 7 and r["sch"] > 0]
    tmpl, n_yrs, k = btw.build_template_from_data(weekly)
    if n_yrs >= btw.MIN_YEARS:
        return (tmpl, f"province_k{k}"), n_yrs
    nt, nm = national_template
    return (nt, f"national_{nm}"), n_yrs


def run_engine(iso, rows, template_info):
    """process_country on one province's rows; returns the series without assumed_zero."""
    by_src = defaultdict(list)
    for r in rows:
        by_src[r["src_file"]].append(dict(r))
    orig = btw.load_national_rows
    btw.load_national_rows = lambda _iso, src, _d: [dict(r) for r in by_src.get(src, [])]
    try:
        diag = {}
        series = btw.process_country(iso, template_info, diag, zero_coverage=False)
    finally:
        btw.load_national_rows = orig
    return {k: v for k, v in series.items() if v["method"] != "assumed_zero"}, diag


def evidence_of(entry, direct_rows, rollups=()):
    """
    'direct' when the filling row was reported for the province itself, 'area'
    when it is an area-wide zero applied to the province, 'rollup' when it is a
    complete list of the province's parts, 'rollup_partial' when it is an
    incomplete list (a lower bound for the province).
    """
    src = entry["source"]
    if entry["method"] == "observed":
        key = entry["monday"].isocalendar()[:2]
        hits = [r for r in direct_rows if r["source"] == src and _span(r) <= 7
                and btw._midpoint_week(r) == key]
    else:
        o_tl, o_tr = entry["_origin"]
        # same end date (decumulated increments keep TR), starting no later
        hits = [r for r in direct_rows if r["source"] == src and _span(r) > 7
                and abs((r["tr"] - o_tr).days) <= 3 and r["tl"] <= o_tl + timedelta(days=3)]
    if not hits:
        if entry["method"] == "observed":
            key = entry["monday"].isocalendar()[:2]
            rh = [r for r in rollups if r["source"] == src and _span(r) <= 7
                  and btw._midpoint_week(r) == key]
        else:
            rh = [r for r in rollups if r["source"] == src and abs((r["tr"] - o_tr).days) <= 3
                  and r["tl"] <= o_tl + timedelta(days=3)]
        return "rollup" if any(r.get("complete") for r in rh) or not rh else "rollup_partial"
    return "direct" if any(not r.get("zero_broadcast") for r in hits) else "area"


def process_country_provinces(iso, units, aliases, national_template, row_overrides=None,
                              containment=None, exclusions=None, zero_excl=()):
    row_overrides = row_overrides or {}
    containment = containment or {}
    exclusions = exclusions or set()
    # One-day zeros are too weak to assert a zero week at province level.
    rows = [r for r in load_country_rows(iso)
            if r["has_count"] and not (r["sch"] == 0 and _span(r) < 6)
            and (iso, r["source"], r["row_index"]) not in exclusions
            and not zero_excluded(r, iso, zero_excl)]
    split_children = split_child_index(aliases)
    resolved = []
    for r in rows:
        parts = r["location"].split("::")
        unit, level, status, reason = resolve(aliases, iso, parts, r["tl"])
        ov = row_overrides.get((iso, r["source"], r["row_index"]))
        if ov and ov[0] == r["location"] and ov[1] == r["tl"].isoformat():
            unit, status, reason = ov[2], "row_override", ""
            level = "direct" if len(parts) == 3 else "part"
        if unit is not None and unit not in units[iso]:
            unit, status, reason = None, "bad_unit", f"alias points to unknown unit {unit!r}"
        resolved.append((rekey_weekly(r), parts, unit, level, status, reason))
    resolved, n_netted = net_of_children_elsewhere(resolved)

    per_unit = defaultdict(lambda: {"direct": [], "part": []})
    unalloc, long_rows = [], []
    n_zero_bcast = 0
    for r, parts, unit, level, status, reason in resolved:
        if unit is None:
            targets = zero_targets(aliases, iso, parts, r["tl"], split_children) \
                if r["sch"] == 0 else set()
            targets &= set(units[iso])
            if targets:
                n_zero_bcast += 1
                for t in targets:
                    per_unit[t]["direct"].append(dict(r, zero_broadcast=True))
                continue
            unalloc.append((r, status, reason))
            continue
        if MAX_SPREAD_DAYS and r["sch"] > 0 and _span(r) > MAX_SPREAD_DAYS:
            long_rows.append((unit, r))
            continue
        per_unit[unit][level].append(r)

    out, stats = {}, {}
    for unit in sorted(per_unit):
        direct = per_unit[unit]["direct"]
        rollups, n_doc_max = build_rollups(per_unit[unit]["part"], containment)
        rollups = select_rollups(direct, rollups, n_doc_max)
        unit_rows, _ = drop_restatements(direct + rollups)
        unit_rows, _ = drop_contradicted_zeros(unit_rows)
        if not unit_rows:
            continue
        tinfo, n_yrs = province_template(unit_rows, national_template)
        series, diag = run_engine(iso, unit_rows, tinfo)
        for e in series.values():
            e["evidence"] = evidence_of(e, direct, rollups)
            e["template"] = tinfo[1]
        out[unit] = series
        stats[unit] = {"direct_rows": len(direct), "part_rows": len(per_unit[unit]["part"]),
                       "rollup_rows_used": len(rollups), "template": tinfo[1],
                       "template_years": n_yrs}
    stats["_zero_broadcast_rows"] = n_zero_bcast
    stats["_netted_rows"] = n_netted
    return out, stats, unalloc, long_rows


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _r(v, n=4):
    return "" if v is None else round(v, n)


def write_outputs(iso, out, units, unalloc, long_rows, out_root):
    base = out_root / iso
    base.mkdir(parents=True, exist_ok=True)
    p = base / f"cholera_adm1_weekly_{iso}.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=WEEKLY_COLS)
        w.writeheader()
        for unit in sorted(out):
            code = units[iso][unit].get("adm1_code", "")
            for (yr, wk), e in sorted(out[unit].items()):
                w.writerow({"iso_code": iso, "adm1_name": unit, "adm1_code": code,
                            "year": yr, "iso_week": wk,
                            "week_start": e["monday"].isoformat(),
                            "week_end": e["sunday"].isoformat(),
                            "sCh": _r(e["sch"]), "deaths": _r(e["deaths"]),
                            "source": e["source"],
                            "confidence_weight": round(e["confidence"], 3),
                            "disaggregation_method": e["method"],
                            "evidence": e["evidence"], "template": e["template"],
                            "source_span_days": 7 if e["method"] == "observed"
                            else (e["_origin"][1] - e["_origin"][0]).days + 1})

    with open(base / f"cholera_adm1_unallocated_{iso}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=UNALLOC_COLS)
        w.writeheader()
        for r, status, reason in sorted(unalloc, key=lambda x: (x[0]["location"], x[0]["tl"])):
            w.writerow({"iso_code": iso, "source_database": r["source"], "Index": r["row_index"],
                        "Location": r["location"], "TL": r["tl0"].isoformat(),
                        "TR": r["tr0"].isoformat(), "sCh": _r(r["sch"]),
                        "deaths": _r(r["deaths"]), "source_index": r["src_index"],
                        "status": status, "reason": reason})

    long_path = base / f"cholera_adm1_long_totals_{iso}.csv"
    long_path.unlink(missing_ok=True)
    if MAX_SPREAD_DAYS:   # only meaningful when long totals were excluded
        with open(long_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=LONG_COLS)
            w.writeheader()
            for unit, r in sorted(long_rows, key=lambda x: (x[0], x[1]["tl"])):
                w.writerow({"iso_code": iso, "adm1_name": unit, "source_database": r["source"],
                            "Index": r["row_index"], "Location": r["location"],
                            "TL": r["tl"].isoformat(), "TR": r["tr"].isoformat(),
                            "days": (r["tr"] - r["tl"]).days + 1, "sCh": _r(r["sch"]),
                            "deaths": _r(r["deaths"]),
                            "evidence": "rollup" if r.get("rollup") else "direct"})

    # Reconciliation against the national weekly series (never used to rescale).
    nat = {}
    nat_csv = DATA_DIR / iso / f"cholera_weekly_{iso}.csv"
    if nat_csv.exists():
        with open(nat_csv, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                nat[(int(r["year"]), int(r["iso_week"]))] = r
    agg = defaultdict(lambda: [0.0, 0, 0])
    for unit, series in out.items():
        for k, e in series.items():
            if e["method"] == "inferred_zero":
                continue   # MOSAIC reads inferred_zero as missing
            a = agg[k]
            a[0] += e["sch"] or 0.0
            a[1] += 1
            a[2] += e["method"] == "observed"
    with open(base / f"cholera_adm1_reconciliation_{iso}.csv", "w", newline="",
              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=RECON_COLS)
        w.writeheader()
        for k in sorted(agg):
            n = nat.get(k)
            ns = float(n["sCh"]) if n and n["sCh"] not in ("", None) else None
            mon, _ = btw.isoweek_bounds(*k)
            w.writerow({"iso_code": iso, "year": k[0], "iso_week": k[1],
                        "week_start": mon.isoformat(), "national_sCh": _r(ns),
                        "national_method": n["disaggregation_method"] if n else "",
                        "provinces_sCh": _r(agg[k][0]), "provinces_reporting": agg[k][1],
                        "provinces_observed": agg[k][2],
                        "ratio": _r(agg[k][0] / ns, 4) if ns else ""})
    return p


def main(argv=None):
    global MAX_SPREAD_DAYS
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--iso", nargs="+", help="only these countries (default: the 40)")
    ap.add_argument("--as-of", help="series end date (default today)")
    ap.add_argument("--out-dir", help="write to DIR/{ISO}/ instead of data/{ISO}/")
    ap.add_argument("--max-spread-days", type=int, default=None,
                    help="exclude positive totals longer than this many days "
                         "(default: spread all, as the national builder does)")
    ap.add_argument("--ref-dir", help="read adm1_units.csv / adm1_aliases.csv from DIR "
                                      "(default reference/subnational)")
    args = ap.parse_args(argv)
    MAX_SPREAD_DAYS = args.max_spread_days
    if args.as_of:
        btw.SERIES_END = date.fromisoformat(args.as_of)
    out_root = Path(args.out_dir) if args.out_dir else DATA_DIR

    country_map = btw.load_country_map()
    targets = sorted(country_map) if not args.iso else [i.upper() for i in args.iso]
    bad = [i for i in targets if i not in country_map]
    if bad:
        raise SystemExit(f"not MOSAIC framework countries: {bad} (pilots are out of scope)")

    ref = Path(args.ref_dir) if args.ref_dir else SUB_DIR
    units, aliases = load_units(ref / "adm1_units.csv"), load_aliases(ref / "adm1_aliases.csv")
    row_overrides = load_row_overrides(ref / ROW_OVERRIDES_CSV)
    containment = load_containment(ref / CONTAINMENT_CSV)
    exclusions = load_exclusions(ref / EXCLUSIONS_CSV)
    zero_excl = load_zero_exclusions(ref / ZERO_EXCLUSIONS_CSV)
    print("Building national seasonal templates (fallback for provinces)...")
    templates = btw.build_all_templates(country_map)

    summary = []
    for iso in targets:
        out, stats, unalloc, long_rows = process_country_provinces(
            iso, units, aliases, templates[iso], row_overrides, containment, exclusions, zero_excl)
        write_outputs(iso, out, units, unalloc, long_rows, out_root)
        n_units = len(units[iso])
        for unit in sorted(units[iso]):
            s = out.get(unit, {})
            st = stats.get(unit, {})
            meth = defaultdict(int)
            for e in s.values():
                meth[e["method"].split("_")[0] if e["method"].startswith("fourier") else e["method"]] += 1
            pos = [e for e in s.values() if e["sch"] and e["sch"] > 0]
            summary.append({
                "iso_code": iso, "adm1_name": unit,
                "adm1_code": units[iso][unit].get("adm1_code", ""),
                "weeks": len(s), "observed": meth["observed"], "fourier": meth["fourier"],
                "documented_zero": meth["documented_zero"], "inferred_zero": meth["inferred_zero"],
                "positive_weeks": len(pos),
                "observed_positive": sum(1 for e in pos if e["method"] == "observed"),
                "rollup_weeks": sum(1 for e in s.values() if e["evidence"] == "rollup"),
                "total_sCh": round(sum(e["sch"] or 0 for e in s.values()), 1),
                "first_week": min((e["monday"] for e in s.values()), default=""),
                "last_week": max((e["monday"] for e in s.values()), default=""),
                "template": st.get("template", ""), "template_years": st.get("template_years", ""),
                "direct_rows": st.get("direct_rows", 0), "part_rows": st.get("part_rows", 0),
            })
        n_pos = sum(1 for u in out.values() for e in u.values() if e["sch"] and e["sch"] > 0)
        n_un = sum(1 for r, *_ in unalloc if r["sch"] > 0)
        n_zb = stats.pop("_zero_broadcast_rows", 0)
        n_net = stats.pop("_netted_rows", 0)
        own = sum(1 for s in stats.values() if s["template"].startswith("province"))
        print(f"  {iso}: {len(out)}/{n_units} provinces with data, {n_pos} positive province-weeks, "
              f"{own} own templates; {len(unalloc)} rows unallocated ({n_un} positive); "
              + (f"{len(long_rows)} totals > {MAX_SPREAD_DAYS} d held out; " if MAX_SPREAD_DAYS else "")
              + f"{n_zb} area-wide zeros applied; {n_net} parent rows netted of districts elsewhere")

    if not args.iso and not args.out_dir:
        cols = list(summary[0].keys())
        with open(SUMMARY_CSV, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(summary)
        print(f"Summary: {SUMMARY_CSV.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
