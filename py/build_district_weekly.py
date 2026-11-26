#!/usr/bin/env python3
"""
Build weekly cholera time series at administrative district (ADM2) level, from
counts REPORTED at district level or below. Province and national totals are
never split across districts.

Method (docs/technical/district-weekly-series-scope.md): the province build's
machinery one level down (py/build_province_weekly.py), using its rules for
per-report roll-ups, completeness, containment, area-wide zeros, midpoint weeks
and the national evidence ladder.

  Units      Current administrative districts, reference/subnational/adm2_units.csv,
             each under a current province (adm1_units.csv). A row's province is
             resolved with the province tables; its district string is the
             segment after the province slot (or the province slot itself where
             that string is a district, as in UGA and MWI), resolved through
             adm2_aliases.csv keyed by (current province, raw district).
  Evidence   direct  - a row for the district itself.
             rollup  - rows for parts of the district (health districts, towns,
                       sub-counties, chiefdoms) summed per report and period.
             area    - a reported zero for a whole province, or for a composite or
                       split area, applied to each district in it (zero for an area
                       is zero in every part). Never placed in a week where the
                       district has a positive report.
  Seasonal   The district's own Fourier template where it has >= MIN_YEARS
  template   outbreak-years of weekly data; else its province's (from the
             province series' observed weeks, same rule); else the national one.
  Scope      DRC (COD) is province-level only (decision 2026-11-25: too many
             districts); pilots are out of scope.

Outputs per country (data/{ISO}/):
  cholera_adm2_weekly_{ISO}.csv, cholera_adm2_reconciliation_{ISO}.csv,
  cholera_adm2_unallocated_{ISO}.csv
Summary: reference/subnational/district_build_summary.csv
"""

import argparse
import csv
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_province_weekly as bpw  # noqa: E402

btw = bpw.btw
BASE_DIR = bpw.BASE_DIR
DATA_DIR = bpw.DATA_DIR
SUB_DIR = bpw.SUB_DIR
SUMMARY_CSV = SUB_DIR / "district_build_summary.csv"
EXCLUDE = {"COD"}   # province level only (user decision 2026-11-25)

# LOCAL ONLY. Kenya's sub-county series uses the MOSAIC-Kenya line-list weekly
# aggregates (Kenya MoH / KEMRI record-level data in a private repository). Its
# outputs are git-ignored (.gitignore, .git/hooks/pre-commit), excluded from the
# shared summary and from the shared figures, and must never be pushed or
# published. Decision 2026-11-25.
LOCAL_ONLY = {"KEN"}
SLOT_DISTRICTS = {"UGA", "MWI"}   # countries whose districts sit in the province slot in every era
# (era-specific slot districts, e.g. BDI Rumonge before 2015, are in adm2_slot_districts.csv)
MAX_SPREAD_DAYS = None   # None = spread every multi-week total (as the province/national builds)
KEN_LINELIST = BASE_DIR.parent / "MOSAIC-Kenya" / "output" / "data" / \
    "data-kenya-cholera-weekly-subcounties.csv"
# MOSAIC-Kenya: conflict_bracketed weeks are drawn at random between two
# contradictory dates - "leave out of any analysis of timing".
KEN_METHODS = {"onset": "observed", "facility": "observed", "fourier_distributed": "fourier_linelist"}

WEEKLY_COLS = ["iso_code", "adm1_name", "adm2_name", "adm2_code", "year", "iso_week",
               "week_start", "week_end", "sCh", "deaths", "source", "confidence_weight",
               "disaggregation_method", "evidence", "template", "source_span_days"]
RECON_COLS = ["iso_code", "adm1_name", "year", "iso_week", "week_start", "province_sCh",
              "province_method", "districts_sCh", "districts_reporting", "ratio"]
UNALLOC_COLS = ["iso_code", "source_database", "Index", "Location", "TL", "TR", "sCh",
                "deaths", "adm1_name", "status", "reason"]
SEP = "||"   # unit key: adm1_name || adm2_name


# ---------------------------------------------------------------------------
# Reference tables
# ---------------------------------------------------------------------------

def load_units(path):
    """{iso: {unit_key: row}} and {iso: {adm1: [unit_key, ...]}}."""
    units, by_prov = defaultdict(dict), defaultdict(lambda: defaultdict(list))
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            k = r["adm1_name"] + SEP + r["adm2_name"]
            units[r["iso"]][k] = r
            by_prov[r["iso"]][r["adm1_name"]].append(k)
    return units, by_prov


def load_aliases(path):
    """
    {(iso, adm1_name, raw_district, raw_child): [row, ...]}. Also reads
    local/adm2_aliases_*.csv beside it: git-ignored mappings that must stay on
    this machine (Kenya's, decided partly from the MOSAIC-Kenya line list).
    """
    al = defaultdict(list)
    files = [Path(path)] + sorted((Path(path).parent / "local").glob("adm2_aliases_*.csv"))
    for f in files:
        if not f.exists():
            continue
        with open(f, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                r["_from"] = btw.parse_date(r.get("valid_from", "")) or date.min
                r["_to"] = btw.parse_date(r.get("valid_to", "")) or date.max
                al[(r["iso"], r["adm1_name"], r["raw_district"], r.get("raw_child", ""))].append(r)
    return al


def unit_for(units, iso, adm2_name, prov):
    """Unit key of a district name: its own province first, else the only match."""
    k = (prov or "") + SEP + adm2_name
    if k in units[iso]:
        return k
    cands = [u for u in units[iso] if u.split(SEP, 1)[1] == adm2_name]
    return cands[0] if len(cands) == 1 else None


def load_row_overrides2(path):
    """{(iso, source_database, Index): (Location, TL, adm1_name, adm2_name)} for single rows."""
    ov = {}
    if path.exists():
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                ov[(r["iso"], r["source_database"], r["Index"])] = (r["Location"], r["TL"],
                                                                     r["adm1_name"], r["adm2_name"])
    return ov


def load_vintages(path):
    """[(iso, source_database, source_match, level, date)]: sources that report one
    boundary set in every year; their names resolve as of that date."""
    out = []
    if path.exists():
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                out.append((r["iso"], r["source_database"], r["source_match"], r["level"],
                            date.fromisoformat(r["boundary_date"])))
    return out


def alias_date(r, iso, level, vintages):
    for v_iso, v_src, v_match, v_level, v_date in vintages:
        if v_iso == iso and v_src == r["source"] and v_level == level and v_match in r["src_name"]:
            return v_date
    return r["tl"]


SLOT_TABLE = []


def load_slot_districts(path):
    """[(iso, raw_adm1 or '*', from, to)]: province-slot strings that are districts."""
    out = []
    if path.exists():
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                out.append((r["iso"], r["raw_adm1"], btw.parse_date(r["valid_from"]) or date.min,
                            btw.parse_date(r["valid_to"]) or date.max))
    return out


def slot_is_district(iso, raw, tl):
    if not SLOT_TABLE:
        SLOT_TABLE[:] = load_slot_districts(SUB_DIR / "adm2_slot_districts.csv")
    return any(i == iso and (s_ == "*" or s_ == raw) and f <= (tl or date.min) <= t_
               for i, s_, f, t_ in SLOT_TABLE)


def district_of(parts, prov, prov_level, iso, al2, by_prov, tl=None):
    """
    (raw district, index of the first segment below it, single_unit) or (None, None, None).
    The province slot holds a district only in countries whose data file districts
    there (SLOT_DISTRICTS: UGA, MWI) and when the province resolver says the slot
    is a PART of the province. Elsewhere a 'part' slot is a former province or
    area (BDI's pre-2025 provinces share names with 2025 communes) and its rows
    are province-level. When the slot IS the province, the row is a province
    total - never a district's - unless the province has exactly one district
    (GNB Bissau, CIV Abidjan, ZWE Bulawayo), whose total it then is.
    """
    if len(parts) == 4 and prov_level == "direct":
        return None, None, None   # a child alias that IS the province (TZA Mainland::Songwe)
    if len(parts) >= 4:
        return parts[3], 4, None
    if prov_level == "part" and slot_is_district(iso, parts[2], tl) \
            and (iso, prov or "", parts[2], "") in al2:
        return parts[2], 3, None
    if prov_level == "direct" and prov and len(by_prov[iso].get(prov, ())) == 1:
        return parts[2], 3, by_prov[iso][prov][0]
    return None, None, None


def resolve_district(al2, units, iso, prov, raw, child, tl):
    """(unit_key or None, status, adm2 alias row or None)."""
    if child is not None:
        rows = al2.get((iso, prov or "", raw, child))
        if rows:
            a = bpw._pick(rows, tl, strict=True)
            if a is not None:
                return _assign(a, units, iso, prov)
    rows = al2.get((iso, prov or "", raw, "")) or al2.get((iso, "", raw, ""))
    if not rows:
        return None, "unmapped", None
    return _assign(bpw._pick(rows, tl), units, iso, prov)


def _assign(a, units, iso, prov):
    if a["status"] in bpw.ASSIGNING | bpw.PART and a["adm2_name"]:
        u = unit_for(units, iso, a["adm2_name"], prov)
        return (u, a["status"], a) if u else (None, "bad_unit", a)
    return None, a["status"], a


def zero_districts(al2, units, by_prov, iso, prov, raw, tl, split_children):
    """Districts a reported zero for an unassignable district-level area speaks for."""
    if raw.startswith("(") and raw.endswith(")"):
        out = set()
        for m in raw[1:-1].split("|"):
            u, st, _ = resolve_district(al2, units, iso, prov, m.split("##")[0], None, tl)
            if u and st in bpw.ASSIGNING:
                out.add(u)
        return out
    rows = al2.get((iso, prov or "", raw, ""))
    if rows and len(rows) == 1 and rows[0]["status"] == "split":
        return set(split_children.get((iso, prov or "", raw), ()))
    return set()


def district_split_children(al2, units):
    idx = defaultdict(set)
    for (iso, prov, raw, child), rows in al2.items():
        if child:
            for a in rows:
                if a["status"] in bpw.ASSIGNING | bpw.PART and a["adm2_name"]:
                    u = unit_for(units, iso, a["adm2_name"], prov)
                    if u:
                        idx[(iso, prov, raw)].add(u)
    return idx


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

def province_templates(iso):
    """{adm1: (template, label)} from the province series' observed positive weeks."""
    p = DATA_DIR / iso / f"cholera_adm1_weekly_{iso}.csv"
    rows = defaultdict(list)
    if p.exists():
        with open(p, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["disaggregation_method"] == "observed" and r["sCh"] and float(r["sCh"]) > 0:
                    mon = date.fromisoformat(r["week_start"])
                    rows[r["adm1_name"]].append((mon, date.fromisoformat(r["week_end"]), float(r["sCh"])))
    out = {}
    for prov, rs in rows.items():
        tmpl, n_yrs, k = btw.build_template_from_data(rs)
        if n_yrs >= btw.MIN_YEARS:
            out[prov] = (tmpl, f"province_k{k}")
    return out


def district_template(rows, prov_tmpl, national_template):
    weekly = [(r["tl"], r["tr"], r["sch"]) for r in rows
              if r["has_count"] and bpw._span(r) <= 7 and r["sch"] > 0]
    tmpl, n_yrs, k = btw.build_template_from_data(weekly)
    if n_yrs >= btw.MIN_YEARS:
        return (tmpl, f"district_k{k}"), n_yrs
    if prov_tmpl:
        return prov_tmpl, n_yrs
    nt, nm = national_template
    return (nt, f"national_{nm}"), n_yrs


# ---------------------------------------------------------------------------
# Per-country build
# ---------------------------------------------------------------------------

def kenya_county_positives(units):
    """(county, pseudo-row) for each positive line-list week, so that repository
    province zeros contradicting the line list are dropped (LOCAL ONLY data)."""
    out = []
    if not KEN_LINELIST.exists():
        return out
    parent = {u["adm2_code"]: u["adm1_name"] for u in units["KEN"].values() if u["adm2_code"]}
    with open(KEN_LINELIST, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["cases_data_available"] == "TRUE" and float(r["cases"] or 0) > 0 \
                    and r["adm2_code"] in parent:
                mon = date.fromisoformat(r["date_start"])
                out.append((parent[r["adm2_code"]],
                            {"tl": mon, "tr": date.fromisoformat(r["date_stop"]), "sch": 1.0}))
    return out


def demote_named_siblings(direct, parts, containment):
    """
    A district-level row reported in the same report and period as sibling parts
    that it does not contain is one part among several (a health district named
    like its department: SEN Mbacke beside Touba, BDI Isale beside Bujumbura
    North, SOM Jowhar beside Mahadaay), not the whole district. Move it to the
    parts so the report is summed. Rows that contain their siblings (an ancestor
    location, or a containment-table entry: Harare, Dakar, Bissau) stay direct.
    """
    by_doc = defaultdict(list)
    for p in parts:
        by_doc[(p["source"], p["src_index"], p["tl"], p["tr"])].append(p)
    keep, moved = [], []
    for d in direct:
        depth = d["location"].count("::")
        # siblings are parts at the SAME location depth; deeper rows are its own
        # sub-areas (UGA Kasese with its sub-counties, GNB Bissau with its bairros)
        sib = [p for p in by_doc.get((d["source"], d["src_index"], d["tl"], d["tr"]), ())
               if p["location"].count("::") == depth]
        # A row at least as large as its same-depth siblings together behaves as
        # their container (a department total beside its health districts: SEN
        # Pikine 45 beside Mbao 13), so it stays the district's own row; erring
        # this way never double counts.
        if sib and any(not bpw._contains(containment, d["location"], p["location"]) for p in sib) \
                and d["sch"] < sum(p["sch"] for p in sib):
            moved.append(d)
        else:
            keep.append(d)
    return keep, parts + moved


def process_country_districts(iso, units, by_prov, al1, al2, national_template,
                              row_overrides, containment, vintages=(), exclusions=(),
                              row_overrides2=None, zero_excl=()):
    row_overrides2 = row_overrides2 or {}
    rows = [r for r in bpw.load_country_rows(iso)
            if r["has_count"] and not (r["sch"] == 0 and bpw._span(r) < 6)
            and (iso, r["source"], r["row_index"]) not in exclusions
            and not bpw.zero_excluded(r, iso, zero_excl)]
    split1 = bpw.split_child_index(al1)
    split2 = district_split_children(al2, units)
    resolved, province_rows, unalloc = [], [], []
    prov_any_pos = defaultdict(list)
    if iso == "KEN":
        for county, pr in kenya_county_positives(units):
            prov_any_pos[county].append(pr)
    for r in rows:
        parts = r["location"].split("::")
        prov, plvl, pst, _ = bpw.resolve(al1, iso, parts, r["tl"])
        ov = row_overrides.get((iso, r["source"], r["row_index"]))
        if ov and ov[0] == r["location"] and ov[1] == r["tl"].isoformat():
            prov = ov[2]
            plvl = "direct" if len(parts) == 3 else "part"
        r = bpw.rekey_weekly(r)
        raw, ci, single = district_of(parts, prov, plvl, iso, al2, by_prov, r["tl"])
        if prov and r["sch"] > 0:
            prov_any_pos[prov].append(r)   # any positive report inside the province
        if raw is None:
            # Province-level row. Positive: never split. Zero: carries to the
            # districts only when the row is for whole provinces - the province
            # itself, or a composite/split area of whole provinces - not when the
            # slot is a part of a province (a former province, a district).
            pal = bpw._pick(al1[(iso, parts[2], "")], r["tl"]) if (iso, parts[2], "") in al1 else None
            if prov and plvl == "direct" and (pal is None or bpw.zero_spreads(pal)):
                province_rows.append((r, {prov}))
            elif prov and plvl == "direct" and pal is not None and r["sch"] == 0 \
                    and bpw.zero_spread_districts(pal):
                # partial shift: the zero holds for the districts the former unit contained
                only = {prov + SEP + n for n in bpw.zero_spread_districts(pal)}
                province_rows.append((r, {prov}, only))
            elif prov is None and len(parts) == 3 and r["sch"] == 0:
                province_rows.append((r, bpw.zero_targets(al1, iso, parts, r["tl"], split1)))
            elif len(parts) == 3 and r["sch"] > 0 and plvl == "part":
                unalloc.append((r, prov, "slot_part",
                                "province-slot string that is neither a province nor a listed "
                                "slot district (adm2_slot_districts.csv)"))
            continue
        child = parts[ci] if len(parts) > ci else None
        if single:
            unit, st = single, "current"
        else:
            unit, st, _ = resolve_district(al2, units, iso, prov, raw, child,
                                           alias_date(r, iso, "adm2", vintages))
        ov2 = row_overrides2.get((iso, r["source"], r["row_index"]))
        if ov2 and ov2[0] == r["location"] and ov2[1] == r["tl0"].isoformat():
            unit, st = unit_for(units, iso, ov2[3], ov2[2]), "row_override"
        level = "direct" if (unit and len(parts) == ci
                             and (st in bpw.ASSIGNING or st == "row_override")) else "part"
        if child is not None and unit and st in bpw.ASSIGNING and len(parts) == ci + 1 \
                and al2.get((iso, prov or "", raw, child)):
            level = "direct"   # a child alias that IS the district
        resolved.append((r, parts, unit, level, st, prov, raw, ci))

    # net district rows of same-report sub-areas assigned to another district
    # (districts in the province slot are depth 3, the rest depth 4; the
    # function keeps any extra tuple fields)
    resolved2, n_net3 = bpw.net_of_children_elsewhere(resolved, depth=3)
    resolved2, n_net4 = bpw.net_of_children_elsewhere(resolved2, depth=4)
    n_net = n_net3 + n_net4

    per_unit = defaultdict(lambda: {"direct": [], "part": [], "zeros": []})
    n_area = 0
    for r, parts, unit, level, st, prov, raw, ci in resolved2:
        if unit is None:
            # only a row for the area itself (not one of its sub-areas) speaks for it
            targets = zero_districts(al2, units, by_prov, iso, prov, raw, r["tl"], split2) \
                if r["sch"] == 0 and raw and len(parts) == ci else set()
            if targets:
                n_area += 1
                for t in targets:
                    per_unit[t]["zeros"].append(dict(r, zero_broadcast=True))
                continue
            unalloc.append((r, prov, st or "unmapped", "district not assignable"))
            continue
        per_unit[unit][level].append(r)
    # A province zero claims every part of the province had no cases, so it is
    # dropped where ANY report inside that province - the province itself, a
    # former province, a district, a split area - gives cases in an overlapping
    # period (reports that disagree).
    for entry in province_rows:
        r, provs = entry[0], entry[1]
        only = entry[2] if len(entry) > 2 else None
        if r["sch"] != 0:
            continue
        for p_ in provs:
            # contradicted by a same-week positive anywhere in the province, or a
            # positive report lying inside the zero's own period; a long total
            # merely overlapping the zero does not contradict a zero week (and the
            # engine no longer lets zero weeks suppress long totals)
            if any(bpw._overlap(r, q) > 0 and (bpw._span(q) <= 7 or
                                               (q["tl"] >= r["tl"] and q["tr"] <= r["tr"]))
                   for q in prov_any_pos.get(p_, ())):
                continue
            for u in by_prov[iso].get(p_, ()):
                if only is None or u in only:
                    per_unit[u]["zeros"].append(dict(r, zero_broadcast=True))
        if provs:
            n_area += 1

    prov_tmpls = province_templates(iso)
    out, stats = {}, {}
    for unit in sorted(per_unit):
        d = per_unit[unit]
        direct, part_rows = demote_named_siblings(d["direct"], d["part"], containment)
        if MAX_SPREAD_DAYS:
            direct = [r for r in direct if not (r["sch"] > 0 and bpw._span(r) > MAX_SPREAD_DAYS)]
            part_rows = [r for r in part_rows if not (r["sch"] > 0 and bpw._span(r) > MAX_SPREAD_DAYS)]
        rollups, n_doc_max = bpw.build_rollups(part_rows, containment)
        rollups = bpw.select_rollups(direct, rollups, n_doc_max)
        positive = [r for r in direct + rollups if r["sch"] > 0]
        pos_weeks = {btw._midpoint_week(r) for r in positive if bpw._span(r) <= 7}

        def clashes(z):
            # An area-wide zero never sits on a week or period the district reports
            # cases in - including a week inside a district's positive multi-week
            # total, where the zero would otherwise count as observed coverage and
            # make the engine skip that total.
            if bpw._span(z) <= 7 and btw._midpoint_week(z) in pos_weeks:
                return True
            return any(bpw._overlap(z, p) > 0 for p in positive)
        zeros = [z for z in d["zeros"] if not clashes(z)]
        unit_rows, _ = bpw.drop_restatements(direct + rollups)
        unit_rows, _ = bpw.drop_contradicted_zeros(unit_rows + zeros)
        if not unit_rows:
            continue
        prov = unit.split(SEP, 1)[0]
        tinfo, n_yrs = district_template(direct + rollups, prov_tmpls.get(prov), national_template)
        series, _ = bpw.run_engine(iso, unit_rows, tinfo)
        for e in series.values():
            e["evidence"] = bpw.evidence_of(e, direct + zeros, rollups)
            e["template"] = tinfo[1]
        out[unit] = series
        stats[unit] = {"direct_rows": len(direct), "part_rows": len(part_rows),
                       "template": tinfo[1], "template_years": n_yrs}
    return out, stats, unalloc, {"area_zero_rows": n_area, "netted": n_net}


def overlay_kenya_linelist(out, units):
    """
    For every ISO week inside the line list's coverage (years with
    cases_data_available, up to data_end), Kenya's sub-county series IS the line
    list: entries built from repository rows in those weeks are removed and the
    line list's weekly counts placed instead (source MOH, evidence 'linelist').
    Weeks with no line-list record stay missing, not zero: not every record
    could be placed at sub-county. Years outside coverage keep the repository's
    district rows. Returns a short description, or None.
    """
    if not KEN_LINELIST.exists():
        print("  KEN: MOSAIC-Kenya line-list aggregates not found; repository rows only")
        return None
    code_to_unit = {u["adm2_code"]: k for k, u in units["KEN"].items() if u["adm2_code"]}
    covered, data_end = set(), None
    weeks = defaultdict(lambda: {"sch": 0.0, "deaths": 0.0, "kinds": set()})
    with open(KEN_LINELIST, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            data_end = date.fromisoformat(r["data_end"])
            if r["cases_data_available"] != "TRUE":
                continue
            covered.add(int(r["year"]))
            kind = KEN_METHODS.get(r["method"])
            unit = code_to_unit.get(r["adm2_code"])
            if kind is None or unit is None:
                continue
            mon = date.fromisoformat(r["date_start"])
            w = weeks[(unit, mon.isocalendar()[:2])]
            w["sch"] += float(r["cases"] or 0)
            w["deaths"] += float(r["deaths"] or 0)
            w["kinds"].add(kind)

    def in_cover(key):
        mon, _ = btw.isoweek_bounds(*key)
        return mon.isocalendar()[0] in covered and mon <= data_end
    removed = 0
    for unit in list(out):
        keep = {k: e for k, e in out[unit].items() if not in_cover(k)}
        removed += len(out[unit]) - len(keep)
        out[unit] = keep
    for (unit, key), w in weeks.items():
        if not in_cover(key):
            continue
        mon, sun = btw.isoweek_bounds(*key)
        out.setdefault(unit, {})[key] = {
            "sch": w["sch"], "deaths": w["deaths"], "source": "MOH", "confidence": 1.0,
            "method": "observed" if "observed" in w["kinds"] else "fourier_linelist",
            "monday": mon, "sunday": sun, "_origin": (mon, sun),
            "evidence": "linelist", "template": ""}
    out = {u: s_ for u, s_ in out.items() if s_}
    return (out, f"line list {min(covered)}-{data_end.isoformat()} ({len(covered)} years with data); "
                 f"{removed} repository weeks replaced; {len(weeks)} line-list sub-county-weeks")


def _r(v, n=4):
    return "" if v is None else round(v, n)


def write_outputs(iso, out, units, unalloc, out_root):
    base = out_root / iso
    base.mkdir(parents=True, exist_ok=True)
    with open(base / f"cholera_adm2_weekly_{iso}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=WEEKLY_COLS)
        w.writeheader()
        for unit in sorted(out):
            prov, name = unit.split(SEP, 1)
            code = units[iso][unit].get("adm2_code", "")
            for (yr, wk), e in sorted(out[unit].items()):
                w.writerow({"iso_code": iso, "adm1_name": prov, "adm2_name": name, "adm2_code": code,
                            "year": yr, "iso_week": wk, "week_start": e["monday"].isoformat(),
                            "week_end": e["sunday"].isoformat(), "sCh": _r(e["sch"]),
                            "deaths": _r(e["deaths"]), "source": e["source"],
                            "confidence_weight": round(e["confidence"], 3),
                            "disaggregation_method": e["method"], "evidence": e["evidence"],
                            "template": e["template"],
                            "source_span_days": 7 if e["method"] == "observed"
                            else (e["_origin"][1] - e["_origin"][0]).days + 1})
    with open(base / f"cholera_adm2_unallocated_{iso}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=UNALLOC_COLS)
        w.writeheader()
        for r, prov, st, reason in sorted(unalloc, key=lambda x: (x[0]["location"], x[0]["tl0"])):
            w.writerow({"iso_code": iso, "source_database": r["source"], "Index": r["row_index"],
                        "Location": r["location"], "TL": r["tl0"].isoformat(),
                        "TR": r["tr0"].isoformat(), "sCh": _r(r["sch"]), "deaths": _r(r["deaths"]),
                        "adm1_name": prov or "", "status": st, "reason": reason})
    # reconciliation against the province series (never used to rescale)
    prov_w = {}
    p = DATA_DIR / iso / f"cholera_adm1_weekly_{iso}.csv"
    if p.exists():
        with open(p, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                prov_w[(r["adm1_name"], int(r["year"]), int(r["iso_week"]))] = r
    agg = defaultdict(lambda: [0.0, 0])
    for unit, series in out.items():
        prov = unit.split(SEP, 1)[0]
        for k, e in series.items():
            if e["method"] == "inferred_zero":
                continue
            a = agg[(prov,) + k]
            a[0] += e["sch"] or 0.0
            a[1] += 1
    with open(base / f"cholera_adm2_reconciliation_{iso}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=RECON_COLS)
        w.writeheader()
        for k in sorted(agg):
            pr = prov_w.get(k)
            ps = float(pr["sCh"]) if pr and pr["sCh"] not in ("", None) else None
            mon, _ = btw.isoweek_bounds(k[1], k[2])
            w.writerow({"iso_code": iso, "adm1_name": k[0], "year": k[1], "iso_week": k[2],
                        "week_start": mon.isoformat(), "province_sCh": _r(ps),
                        "province_method": pr["disaggregation_method"] if pr else "",
                        "districts_sCh": _r(agg[k][0]), "districts_reporting": agg[k][1],
                        "ratio": _r(agg[k][0] / ps) if ps else ""})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--iso", nargs="+", help="only these countries (default: all with district units)")
    ap.add_argument("--as-of", help="series end date (default today)")
    ap.add_argument("--out-dir", help="write to DIR/{ISO}/ instead of data/{ISO}/")
    ap.add_argument("--ref-dir", help="reference directory (default reference/subnational)")
    ap.add_argument("--max-spread-days", type=int, default=None,
                    help="exclude positive totals longer than this many days (default: spread all)")
    args = ap.parse_args(argv)
    global MAX_SPREAD_DAYS
    MAX_SPREAD_DAYS = args.max_spread_days
    if args.as_of:
        btw.SERIES_END = date.fromisoformat(args.as_of)
    out_root = Path(args.out_dir) if args.out_dir else DATA_DIR
    ref = Path(args.ref_dir) if args.ref_dir else SUB_DIR

    country_map = btw.load_country_map()
    units, by_prov = load_units(ref / "adm2_units.csv")
    al1 = bpw.load_aliases(SUB_DIR / "adm1_aliases.csv")
    al2 = load_aliases(ref / "adm2_aliases.csv")
    row_overrides = bpw.load_row_overrides(SUB_DIR / bpw.ROW_OVERRIDES_CSV)
    containment = bpw.load_containment(SUB_DIR / bpw.CONTAINMENT_CSV)
    vintages = load_vintages(SUB_DIR / "source_boundary_vintage.csv")
    SLOT_TABLE[:] = load_slot_districts(SUB_DIR / "adm2_slot_districts.csv")
    exclusions = bpw.load_exclusions(SUB_DIR / bpw.EXCLUSIONS_CSV)
    row_overrides2 = load_row_overrides2(SUB_DIR / "adm2_row_overrides.csv")
    zero_excl = bpw.load_zero_exclusions(SUB_DIR / bpw.ZERO_EXCLUSIONS_CSV)
    targets = [i.upper() for i in args.iso] if args.iso else sorted(units)
    targets = [i for i in targets if i in country_map and i not in EXCLUDE and i in units]
    print("Building national seasonal templates (fallback)...")
    templates = btw.build_all_templates(country_map)

    summary = []
    for iso in targets:
        out, stats, unalloc, diag = process_country_districts(
            iso, units, by_prov, al1, al2, templates[iso], row_overrides, containment, vintages,
            exclusions, row_overrides2, zero_excl)
        if iso == "KEN":
            res = overlay_kenya_linelist(out, units)
            if res:
                out, msg = res
                print(f"  KEN [LOCAL ONLY]: {msg}")
        write_outputs(iso, out, units, unalloc, out_root)
        n_pos = sum(1 for s in out.values() for e in s.values() if e["sch"] and e["sch"] > 0)
        n_obs = sum(1 for s in out.values() for e in s.values()
                    if e["method"] == "observed" and e["sch"] and e["sch"] > 0)
        print(f"  {iso}: {len(out)}/{len(units[iso])} districts with data, {n_pos} positive "
              f"district-weeks ({n_obs} reported weekly); {len(unalloc)} rows unallocated; "
              f"{diag['area_zero_rows']} area-wide zero rows")
        rows_iso = []
        for unit in sorted(units[iso]):
            s = out.get(unit, {})
            st = stats.get(unit, {})
            pos = [e for e in s.values() if e["sch"] and e["sch"] > 0]
            prov, name = unit.split(SEP, 1)
            rows_iso.append({
                "iso_code": iso, "adm1_name": prov, "adm2_name": name,
                "adm2_code": units[iso][unit].get("adm2_code", ""), "weeks": len(s),
                "positive_weeks": len(pos),
                "observed_positive": sum(1 for e in pos if e["method"] == "observed"),
                "total_sCh": round(sum(e["sch"] or 0 for e in s.values()), 1),
                "first_week": min((e["monday"] for e in s.values()), default=""),
                "last_week": max((e["monday"] for e in s.values()), default=""),
                "template": st.get("template", ""), "template_years": st.get("template_years", ""),
                "direct_rows": st.get("direct_rows", 0), "part_rows": st.get("part_rows", 0)})
        if iso in LOCAL_ONLY:
            local = out_root / iso / f"cholera_adm2_summary_{iso}.csv"   # git-ignored
            with open(local, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows_iso[0]))
                w.writeheader()
                w.writerows(rows_iso)
        else:
            summary.extend(rows_iso)
    if not args.iso and not args.out_dir and summary:
        with open(SUMMARY_CSV, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(summary[0]))
            w.writeheader()
            w.writerows(summary)
        print(f"Summary: {SUMMARY_CSV.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
