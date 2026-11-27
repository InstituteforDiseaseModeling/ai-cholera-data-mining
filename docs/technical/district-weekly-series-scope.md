# Weekly district-level cholera series

Status: **implemented 2026-11-25** for 38 countries; **DRC added 2026-11-27** at
health-zone level (see "DR Congo health zones" below), so every MOSAIC country
with district rows is built except Gambia (no district rows). Runs on every
`bash update_dashboard.sh` after the province step.
The scoping notes that led here follow the implementation section.

## Implementation

| Command | Purpose |
|---|---|
| `python py/build_district_weekly.py [--iso ISO ...]` | Build `data/{ISO}/cholera_adm2_weekly_{ISO}.csv` and side files |
| `python py/validate_district_series.py [ISO ...]` | Reference and output checks; exits non-zero on error |
| `python py/plot_district_series.py [--iso ISO ...]` | Figures in `figures/district/` |

**Reference tables** (`reference/subnational/`), built by per-country research
from OCHA COD-AB admin-2 tables (HDX), laws and national lists:
- `adm2_units.csv`: 4,253 current districts, each under a current province.
- `adm2_aliases.csv`: 4,731 rows mapping every (current province, raw district
  [, child]) in the data, with era rows. The status vocabulary is the one used
  for provinces.
- `source_boundary_vintage.csv`: sources that report one boundary set in every
  year (ZMB JHU UID 21243 uses the 72 pre-2011 districts throughout).

Unit choices by country:
- districts: UGA (136), MWI (32 incl. 4 cities), ZMB (116), ZWE (91 incl. urban
  councils), GHA (261), SLE (16), SOM (90), LBR (136 statutory);
- sub-counties: KEN (290);
- councils: TZA (195);
- municipalities: AGO (326, 2024 law);
- communes: BDI (42, 2025), BEN (77);
- departments: CMR (58), TCD (120, 2024 ordinance), SEN (46), NER (63 + 4 cities);
- provinces: BFA (47, 2025);
- cercles: MLI (159 + Bamako communes);
- prefectures: GIN (33 + 13 Conakry communes), TGO (39);
- sub-prefectures: CAF (85);
- regions: CIV (31 + Abidjan, Yamoussoukro);
- zones: ETH (105);
- counties: SSD (79);
- LGAs: NGA (774);
- district/metro municipalities: ZAF (52);
- constituencies: NAM (121).

Health districts in the data are mapped to the administrative district
containing them.

**Rules** (on top of the province machinery, reused unchanged):
- **Only district-or-below rows count.** A province-slot row is a district's
  only when the province resolver says the slot is a part of a province
  (UGA/MWI districts), or when the province has a single district.
  Province totals are never assigned to a same-named district.
- **Area zeros.** A province's reported zero applies to each of its districts
  ('area'), except:
  - where the same province reports cases in an overlapping period;
  - in any week or period a district reports cases, including a week inside a
    district's multi-week total.

  Zeros from a part of a province (a former province) do not spread.
- **Seasonal template:** the district's own (>= 3 outbreak-years of weekly data),
  else the province's (from the province series' observed weeks), else the
  national one.
- **Cumulative chains:** reports chain only when they are for the same place
  (engine change; national series verified identical).

**Red-team review (2026-11-25)** found and led to fixes for:
- province totals assigned to same-named districts (8,199 rows);
- area zeros contradicting positive province reports;
- area zeros deleting districts' own totals through the coverage rule;
- missing netting for districts in the province slot;
- cross-place cumulative chaining;
- a province-builder bug treating a shifted district child (SLE Bombali) as the
  province.

**Kenya: LOCAL ONLY (decision 2026-11-25).** Kenya's sub-county series uses
MOSAIC-Kenya's aggregated weekly sub-county file
(`MOSAIC-Kenya/output/data/data-kenya-cholera-weekly-subcounties.csv`, read in
place; the line list itself is never read or copied). That file derives from Kenya
MoH / KEMRI record-level data in a private repository.
- **Which weeks it covers:** for weeks inside the line list's coverage (years
  with data, up to its end date, excluding gap years), the series IS the line
  list. Weeks with no record stay missing, because not every record is placed at
  sub-county. Other years keep this repository's rows.
- **Weeks left out:** `conflict_bracketed` weeks, whose dates are random within a
  bracket.
- **Kept local:** every Kenya district output (`data/KEN/cholera_adm2_*`,
  `figures/district/countries/district_series_KEN.png`) is git-ignored and
  blocked by a local `.git/hooks/pre-commit` guard.
- **Excluded from shared outputs:** the shared district summary and figures, and
  any published page. Never commit, push or publish these.

**Second red-team review (2026-11-25)** covered code, reference tables and
outputs, then re-verified the fixes. It led to fixes for:
- **Former provinces taken as same-named communes.** Province-slot strings are
  districts only where `adm2_slot_districts.csv` says so: UGA, MWI, BEN
  Bassilla, and BDI Rumonge before 2015.
- **Cross-place cumulative chaining of rollups.** A rollup's place key is its set
  of part paths; it chains only into a later report whose part set contains it,
  as when a situation report lists more districts as an outbreak spreads (MWI
  2023).
- **Zero-filled weekly tables erasing cases.** Weekly zeros give way to same-week
  positive reports. The engine runs with `zero_coverage=False` for sub-national
  builds, so zero weeks no longer make it skip a total; the national default is
  unchanged. `source_zero_exclusions.csv` drops the zeros of the NGA UNICEF LGA
  tables (UID 5116/21443, 98.9% zeros, duplicated).
- **Sibling health districts dropped.** A district row reported beside same-depth
  siblings that it does not contain, and that is smaller than their sum, is
  summed with them (SEN Mbacke + Touba). A row at least as large as its siblings
  is kept as their container (SEN Pikine 45 beside Mbao 13).
- **Short restatements of long totals.** A row of 14 days or less that restates a
  total of 90 days or more is dropped (SOM 2023 W52 spikes).
- **Misdated annual rows.** `row_exclusions.csv` holds 41 BDI one-day 1 January
  rows that carry annual totals.
- **Area zeros.** These now come only from:
  - whole-unit province rows;
  - 'shifted' former provinces (which contain their successor), except those in
    `adm1_shift_partial.csv`:
    - pre-2024 Conakry spreads only to the 10 communes it contained;
    - pre-2020 Ombella-M'Poko never spreads to Bangui.

  An area zero is dropped where a same-week positive, or a positive report inside
  the zero's own period, exists anywhere in the province (Kenya line-list weeks
  included). Sub-area zeros do not spread to the parent district's successors.
- **Reference fixes:**
  - 73 ETH woreda child rows from COD-AB admin3, e.g. Moyale to Borena and Meda
    Welabu to East Borena;
  - UGA 2018 "Hoima" goes to Kikuube (the Kyangwali settlement outbreak);
  - referral hospitals whose admissions are city-wide are held out (SOM Banaadir
    General Hospital, MOZ Mavalane, Chamanculo and Jose Macamo, GHA La General
    Hospital);
  - `adm2_row_overrides.csv` for single misfiled rows.

**Known limits:**
- **Mali 2018-19 health-district zero tables** name former cercles that were
  split in 2023 with no recorded successor list. Their zeros are not spread
  (612 rows).
- **The container rule can undercount siblings.** It keeps a large row as their
  container, so a sitrep listing a district beside a smaller one carved out of it
  undercounts (SOM Jowhar 26 + Mahadaay 7 gives 26).
- **Partially overlapping totals of one place** (inherited engine logic) can
  overcount (ETH West Arsi 2006-07, GHA La Dade-Kotopon 2014). Fourier weeks
  where the seasonal template is zero carry 0 (inherited).
- **Multi-year totals are spread by default** (e.g. ZAF KwaZulu-Natal 2000-04
  district totals). Filter on `source_span_days`, or build with
  `--max-spread-days`.
- **Majority rule:** a 'shifted' legacy district takes 100% of its rows into the
  majority successor. 704 UGA rows have shares of 0.50-0.60, and AGO's 38
  shifted rows have no share recorded.
- **Conflicting cumulative series under one location** leave their discrepancy
  in one week (NGA Maiduguri 2026-W28, 9,642).
- **Weekly zero tables outrank AI totals under the coverage rule.** JHU weekly
  district tables reporting zeros can suppress an AI annual total (BEN Cotonou
  2020).
- **Engine behaviours inherited from the national builder** are listed in
  `subnational-weekly-series-plan.md`.

**Decisions (2026-11-25):**
- **Administrative districts (ADM2)** everywhere, not health districts.
- **DRC stays at province level only**: too many districts. *Superseded
  2026-11-27: DRC is built at health-zone level (next section).*

## DR Congo health zones (2026-11-27)

The user asked whether DRC could be built at district level after all; the
answer was yes, and it was built the same day.

**Units: the 519 health zones (zones de sante), not territories.** DRC reports
cholera by health zone and OCV campaigns target health zones; health zones do
not nest in territories, so a territory series would have to split or set aside
many zones. This is the one exception to the administrative-district rule.
- List: OCHA "DR Congo - Health Zones" (Referentiel Geographique Commun,
  `RDC_Zone_de_sante_09092019`, https://data.humdata.org/dataset/dr-congo-health-0,
  sha256 e92e4afecfa7f1ac...), 519 zones, 26 provinces. Territory and pre-2015
  province come from the GRID3/SNIS layer in
  `MOSAIC-weather-stations/data/boundaries/rdc_zones_de_sante` (same codes).
  Both are in `reference/subnational/cod_health_zones.csv` (code, names,
  territory, old province, DHIS2 id, RGC population, centroid).
- One correction to the RGC list: **Manika** is placed in Lualaba, not
  Haut-Katanga (it is a Kolwezi zone; every data source files it under Lualaba;
  this gives Lualaba 14 zones and Haut-Katanga 27).
- A territory series can be added later by aggregating zones with the
  `territory` column.

**New source: the JHU public surveillance archive.** The JHU baseline
(`cholera_data_jhu.csv`, from the jhu_cholera_data scraper) holds a small
snapshot of DRC's health-zone collections. The archive in
`MOSAIC-data/raw/JHU/osfstorage-archive/Public_surveillance_dataset.rds` holds
16,995 non-phantom weekly health-zone rows for 2018-2022 (343-351 zones a week
in 2018, zeros included); 13,992 of them (3,664 with cases) are not in the
baseline. `py/import_jhu_archive.py` writes them to
`data/COD/cholera_data_jhu_archive.csv` (+ `metadata_jhu_archive.csv`), read only
by the province and district builders, as JHU rows: where the archive and the
baseline report the same zone-week the engine keeps the larger value (checked:
952 such zone-weeks, none double counted). The national builder, the AI-layer
validators and the dashboard do not read it. Early-2018 archive weeks sum to
within 1-2% of the national weekly series.

**Reference work (all in `reference/subnational/`):**
- `adm2_units.csv`: 519 DRC zones (unit_type `health_zone`).
- `adm2_aliases.csv`: 882 DRC rows. 841 name matches (265 exact, 576 after
  normalising: "X Health District", accents, Roman numerals, hyphens), about 30
  reviewed spellings (Kahele -> Kalehe, Kitoyi -> Katoyi, Tshilundu -> Cilundu,
  Kabondo in Haut-Lomami -> Kabondo Dianda, "Bili 2" -> Bili in Bas-Uele),
  31 composites (cities: Kisangani, Mbuji-Mayi, Lubumbashi, Bukavu; the former
  Kolwezi health district; Maluku before its split; JHU multi-zone strings) and
  10 unknown (health areas, camps, localities, strings not in the RGC list).
  Health zones written below Orientale::Ituri are matched with `raw_child` rows.
- `adm1_aliases.csv`: four former districts that became provinces with the same
  territory in 2015 (Orientale::Ituri, Katanga::Tanganyika, Katanga::Haut-Lomami,
  Equateur::Sud-Ubangi) changed from `part` to `renamed`; JHU province totals
  filed one level down (Nord-Kivu::Nord-Kivu, Sud-Kivu::Sud-Kivu) added as the
  province; three JHU zones filed under the wrong province (Rungu, Kimputu,
  Kalonda Est) moved to their province.
- `row_exclusions.csv`: 105 week rows of JHU collection 21140 dated
  2019-12-30..2020-01-05 that carry each zone's 2020 annual total (54 baseline,
  51 archive copies; the same collection also gives the 2019-12-30..2020-12-27
  totals), and AI row 305 (IRIN attributes MSF's Katanga-wide "more than 4,700"
  to Pweto in 2000; MSF's own figure for Pweto is 1,800, AI row 833). A general
  same-start restatement rule was tried and rejected: it also dropped genuine
  first-week counts of small outbreaks in BDI, ETH, KEN, ZAF and ZMB.
  `py/validate_province_series.py` now flags exclusions that match no data row.

**Result.** 519 zones with at least one week; 335 with cases; 29,213 positive
zone-weeks (9,408 of them weekly reports). Zone sums against the province
series: 0.76 (2018, 80% observed), 0.98 (2019, 95% observed), 0.80 (2022), 0.65
(2023), 0.55 (2025): from 2022 the situation reports list only the most active
zones, so those weeks are lower bounds and quiet zones are missing, not zero.
The DRC province series changed only where the archive or the alias fixes add
evidence (2018: 37,526 -> 38,811, mainly Kongo-Central, where complete
health-zone tables replace a spread JHU annual total; 2011-2013 +0.2-4%); every
other country's province and district outputs are unchanged.

**Known limits for DRC.**
- 108 province-weeks where zones sum to more than twice the province: annual
  zone totals (2017, 2020) are spread by the seasonal template while the province
  has weekly reports; annual totals agree (Nord-Kivu 2017: 15,050 both).
- Eight province-years before 2012 where zones exceed the province by more than
  1.5x (Tshopo 2011: zone tables about 2,000, province 338). The province series
  ignores partial lists inside a province total (Part C of the casebook).
- 196 district rows unallocated (96 composite, 100 unknown; 109 positive).

## Pilot, re-ranked for administrative districts

District names in the data were matched to the current official ADM2 lists
(geoBoundaries gbOpen, which mirrors OCHA COD-AB/national sources). Matching was
exact or fuzzy at 0.85 after accent and suffix folding. Positive district-weeks
counts only weekly rows; DRC was excluded here (it was added at health-zone level on 2026-11-27).

| Country | ADM2 list (units, year) | Positive district-weeks | Matching an ADM2 name | Verdict |
|---|---|---|---|---|
| ZWE | 91 districts, 2020 | 1,268 | 95% | Pilot |
| SOM | 118 districts, 2022 | 1,294 | 79% | Pilot |
| MWI | 28 districts, 2020 | 1,209 | 63% (the geoBoundaries file holds only 16 of the 28 districts; with the full list matching should be near-complete) | Pilot |
| GIN | 34 prefectures, 2017 | 626 | 99% | Pilot |
| NGA | 774 LGAs, 2022 | 622 | 98% | Pilot |
| SSD | 78 counties, 2020 | 578 | 98% | Pilot |
| KEN | 290 sub-counties, 2020 | (MOSAIC-Kenya line list; local only) | placed by MOSAIC-Kenya | Adopt MOSAIC-Kenya |
| AGO | 157 municipalities (2006 list) | 1,867 | 48% | Second wave: needs the 2024 municipal reform (about 326 units) |
| SLE, ZMB, MLI, MOZ, RWA, GHA, TZA | 13-260 | 260-480 each | 73-100% | Second wave: clean matches, less data |
| CMR | 58 departments | 2,898 | 7% | Data are health districts; needs a health-district -> department crosswalk |
| TCD, CIV, BDI | 70 / 33 / 118 | 250-470 each | 2-44% | Health districts or reformed units; crosswalk needed |
| UGA | districts not in geoBoundaries (ADM2 there = 2006 counties) | 543 | n/a | Needs the OCHA district list and Uganda's district-split history |

Reference caveat: the geoBoundaries files are incomplete for MWI (16 of 28
districts) and ETH (64 of 74). District gazetteers should come from OCHA COD-AB
or national lists, with geoBoundaries as a cross-check.

**Recommended pilot: 6 countries built here plus Kenya adopted**, i.e. ZWE, SOM,
MWI, GIN, NGA and SSD, plus KEN from MOSAIC-Kenya. That is 7 countries in all.
The earlier draft's pilot (CMR, COD, NGA, BDI + KEN) was chosen for complete
health-district tables. It is superseded: DRC is out, and Cameroon and Burundi
report in health units that need a crosswalk under the administrative-district
decision.

## Short answer

**Yes for a subset of countries; not as a uniform 40-country product.** The province
build's method transfers unchanged:
- reported-only counts;
- roll-ups per source document;
- the national evidence ladder;
- seasonal spreading;
- most-recent boundaries;
- area-wide zeros.

What does not transfer is the reference work. Three differences make districts much
harder than provinces:

1. **No district reference exists for most countries.** The province build had a
   600-unit list to start from; districts need about 6,000 current units, none of
   them in this repo.
2. **The reporting unit is often not the administrative district.** Many ministries
   report by *health* district or zone, whose boundaries differ from ADM2.
3. **District boundaries change far more often.** Uganda went from 56 to 146 districts,
   Angola's 2024 reform roughly doubled its municipalities, Zambia went from 72 to 116,
   Ghana from 216 to 261, and Ethiopia's woredas split continually. Under the
   "most recent boundaries for all years" rule, more historical counts become splits
   that cannot be assigned.

Recommended path: a pilot of 4-5 countries chosen for data density and an available
gazetteer, then extend country by country.

## What the data hold (this repo, rows below province level, resolved to current provinces)

4,747 distinct district names; 22,197 positive district-weeks reported weekly.

| Country | District names | Positive district-weeks (weekly rows) | Years | Weekly tables: median / max districts listed | Notes |
|---|---|---|---|---|---|
| COD | 860 | 5,877 | 30 | 4 / 502 | Health zones; GRID3 health-zone layer available locally (519 zones) |
| CMR | 364 | 2,900 | 21 | 178 / 187 | Complete weekly health-district tables (JHU) |
| AGO | 183 | 1,867 | 11 | 14 / 56 | Municipal reform 2024 (about 164 -> 326) |
| ZWE | 93 | 1,302 | 23 | 1 / 49 | |
| SOM | 122 | 1,294 | 14 | 2 / 20 | |
| MWI | 50 | 1,209 | 19 | 4 / 28 | Districts stable since 2003 |
| GIN | 42 | 626 | 10 | 3 / 34 | Prefectures = health districts |
| NGA | 813 | 622 | 16 | 4 / 774 | LGAs stable since 1996; complete LGA tables exist |
| SSD | 76 | 578 | 16 | 1 / 9 | Counties |
| UGA | 250 | 543 | 22 | 1 / 109 | Many district splits since 2000 |
| MOZ | 150 | 482 | 26 | 1 / 26 | ADM2 layer in MOSAIC-Mozambique |
| TCD | 148 | 476 | 9 | 10 / 51 | Health districts |
| BDI | 73 | 439 | 17 | 46 / 46 | Complete health-district tables |
| SLE | 15 | 435 | 7 | 13 / 13 | Complete district tables; chiefdom (ADM3) detail too |
| ZMB, KEN, TZA, MLI, ETH, RWA, GHA, CIV | 20-211 each | 250-380 each | | | KEN: see MOSAIC-Kenya below |
| BFA, TGO, NER, SEN, BEN, GNB, COG, CAF | 52-108 each | 7-176 each | | 31-71 / 31-72 | Complete JHU tables, nearly all zeros: strong absence evidence, few cases |
| LBR, ERI, NAM, SWZ, BWA, GAB, GNQ, GMB, MRT | 0-35 | 0-56 | | | Too thin |

**Unit type visible in the names:**
- Explicit health-unit labels in BDI ("Sanitary District"), CMR, TCD ("HD") and part of
  COD.
- Plain names elsewhere, so each country needs a decision on whether its source tables
  use administrative or health units.

## Resources outside this repo

| Resource | What it gives |
|---|---|
| `MOSAIC-Kenya` | Kenya MoH/KEMRI line list (private repository; local only), placed county -> sub-county -> ward with weekly series per level. Kenya's district series should come from here, not be rebuilt. |
| `MOSAIC-weather-stations/data/boundaries/rdc_zones_de_sante` | GRID3/SNIS DRC health-zone boundaries (519 zones), the COD gazetteer. |
| `MOSAIC-Mozambique/.../MOZ_ADM2.gpkg` | Mozambique districts. |
| `MOSAIC-RDTs/output/data/v2/recent_adm2_weekly.csv` | District-level weekly cases 2024-12-30 to 2026-09-14 for 15 countries (COD 202 units, AGO 107, GHA 26, TCD 25, SSD 23, ZMB 13 ...): recent data and a name list to match against. Check its provenance before use. |
| geoBoundaries / OCHA COD-AB ADM2 (online) | Administrative ADM2 lists for all 40 countries (codes, parents). Not health units. |

## How the build would generalise

1. **Gazetteer** `reference/subnational/adm2_units.csv`: current units with code,
   parent province (the province list already built), and unit type (admin or health).
   One reporting-unit system per country, chosen to match its surveillance tables.
2. **Aliases** `adm2_aliases.csv`: same schema and status vocabulary as ADM1, keyed by
   (province, raw district).
   - Seeded by exact and fuzzy matching within each province; about 4,700 names to
     resolve, versus 1,035 for provinces.
   - District change histories drive the era rows. Examples: Uganda's district
     creations, Kenya's pre-2010 districts to sub-counties (already done in
     MOSAIC-Kenya), Zambia 2011-18, Ghana 2018, Angola 2024, Mozambique 2013,
     Tanzania councils.
3. **Builder**: parameterise `build_province_weekly.py` by level, with unit =
   (province, district).
   - Template hierarchy: the district's own template, else the province's, else the
     national template.
   - Roll-ups from ADM3 (SLE chiefdoms, ZAF local municipalities, MLI communes).
   - Area-wide zeros from complete district tables.
   - Reconciliation against the province series.
4. **Validation and figures**: the same checks, plus a check that districts nest inside
   their province. Figures as district x week heatmaps grouped by province.

## Effort and risks

| Step | Effort | Risk |
|---|---|---|
| Unit-type decision per country | Small: inspect source tables | Wrong choice mismatches every row |
| Gazetteers | **Large**: about 6,000 units; health-unit lists are not standardised and need GRID3/HDX/MoH sources | Name collisions within a province, out-of-date lists |
| Change histories (era rows) | **Large** for UGA, ZMB, GHA, AGO, ETH, TZA; small for NGA, MWI, SLE, COD | Many unassignable splits under the most-recent-boundaries rule |
| Builder changes | Small to medium | |
| Review | Medium | District rows are mostly JHU and AI extractions, and many are mis-parented. The province build already found Cameroon and Chad health districts filed under the wrong region. |

## Lessons from the province red team that matter more at district level

- **Completeness.** The province build judges a district list complete by its
  part count. At district level that needs a real gazetteer, because the
  denominator is the full list of districts in the province. A partial list must
  never assert zeros for missing districts. With a gazetteer, completeness can be
  exact.
- **Nested siblings.** Cities filed next to their own health districts (Douala,
  Dakar, Harare) and one place under two spellings were the main
  double-counting sources. A district gazetteer with codes and parent links
  removes most of this; the containment table covers the rest.
- **Week keying.** The midpoint-week fix belongs in the shared engine. District
  series should not repeat the province workaround.
- **Engine behaviours inherited from the national builder** (source priority over
  value, share loss next to documented zeros, overlapping cumulative chains) bite
  harder on small units. Fixing them once in `build_weekly_timeseries.py`, with
  a national regression run, should come before a district build.

## Earlier pilot draft (superseded by the table above)

1. **CMR**: complete weekly health-district tables 2004-2023, 187 districts, 2,900
   positive weeks.
2. **COD**: 5,877 positive health-zone-weeks over 30 years; health-zone gazetteer
   already local.
3. **NGA**: 774 stable LGAs since 1996 (an easy gazetteer), complete LGA tables.
4. **BDI**: complete health-district tables. The district reform alongside the 2025
   province reform needs checking.
5. **KEN**: adopt MOSAIC-Kenya's sub-county series (reconcile its schema) rather than
   rebuild it.

Then decide on MWI, ZWE, SOM, AGO, MOZ and SLE from what the pilot shows about
effort per country.

## Decisions

1. Unit type: administrative ADM2 (decided 2026-11-25).
2. DRC: province level only (decided 2026-11-25; superseded 2026-11-27, built at health-zone level).
3. Pilot: ZWE, SOM, MWI, GIN, NGA, SSD + KEN via MOSAIC-Kenya (proposed).
