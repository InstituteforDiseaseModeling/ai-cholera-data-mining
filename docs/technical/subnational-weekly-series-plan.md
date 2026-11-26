# Weekly province-level cholera series

Status: **implemented 2026-11-25** for all 40 MOSAIC countries (pilots NPL/BGD
out of scope). Runs on every `bash update_dashboard.sh` (build, validate, figures),
right after the national weekly series. The figures are not on the dashboard page.

| Command | Purpose |
|---|---|
| `python py/build_province_weekly.py [--iso ISO ...]` | Build the series (writes `data/{ISO}/cholera_adm1_weekly_{ISO}.csv` + side files) |
| `python py/validate_province_series.py [ISO ...]` | Reference-table and output checks; exits non-zero on error |
| `python py/plot_province_series.py [--iso ISO ...]` | Figures in `figures/province/` |

## Principle

Built **only from counts reported at province level or below**. National totals are
never split across provinces, and province series are not rescaled to the national
series (the comparison is written out, never applied).

## Units: most recent boundaries for all years

`reference/subnational/adm1_units.csv` - 555 current first-level units (519 with an
ISO 3166-2 code), the division in force on 2026-01-01, ASCII-standardised names.
`reference/subnational/adm1_aliases.csv` - every province-slot name in the data
(and child names where needed) resolved to a current unit, with era rows
(`valid_from`/`valid_to`) where a name's territory changed. Built 2026-11-25 by
per-country research (sources in `source_url`/`note` on each row).

Status vocabulary and how the builder uses it:

| Status | Meaning | Builder |
|---|---|---|
| current / alias / renamed | the raw name is the current unit | direct province row |
| shifted | legacy unit; current unit holds > 50% of its population (`successor_share`) | assigned to that unit |
| part | inside one current unit (merged former province, district in the province slot) | summed as a roll-up |
| split | legacy unit, no majority successor | unallocated unless child rows resolve it |
| composite | several units (`(A|B)`, `Multi_*`, "Mainland") | unallocated |
| unknown / not_place | unidentifiable or contested | unallocated |

A child-level alias (`raw_child` set) always wins over its parent's.
`reference/subnational/adm1_row_overrides.csv` reassigns individual rows whose
figure belongs to another unit (e.g. NER 1984 "Niamey" = today's Tillaberi).

Decisions:
- **Uganda and Malawi use their regions (4 and 3)** - the first-level unit; the
  data report districts, which are rolled up.
- **Recent reforms adopted**: BDI 5 provinces (2025), BFA 17 regions (2025), MLI 19
  regions + Bamako (2023), COG 15 departments (2024), AGO 21 provinces (2024/25),
  CAF 20 prefectures (2020), ETH 14 units (2023), GHA 16 (2019), SLE 5 (2017).
- **Reported after the 2026-01-01 cutoff, not applied (press reports only)**: CIV -
  abrogation of the 12 districts (March 2026), which would make the 31 regions the
  first level; GIN - Siguiri and Beyla regions (decree of 2026-08-20).
- Split-vs-shifted judgement calls near 50% (SLE Northern 54%, TCD Moyen-Chari 52%,
  KEN Machakos/Meru) are documented in the alias notes.

## Evidence

- **direct**: a row for the province itself, including a child alias that is the
  province (`KEN Coast::Mombasa` = Mombasa county). A province-slot row is
  netted of same-report district rows that belong to another province (e.g.
  ZMB `Lusaka::Chirundu`; the minority children of a shifted legacy total).
- **rollup**: rows for parts of the province (districts, merged former
  provinces) summed per source document and reporting period. Rules:
  - De-duplication:
    - repeated rows of one location keep the max;
    - a location whose ancestor is present, or that a declared container holds
      (`reference/subnational/adm1_containment.csv`: Douala, Dakar and Harare
      sub-areas filed as siblings), is dropped;
    - a sibling named inside a composite part `(A|B)` is dropped;
    - a part equal to the sum of the others (3+ parts, within 1%) is their total.
  - Same-period rollups from different documents are summed when their parts do
    not overlap or nest.
  - A rollup is *complete* when it lists >= max(3, 80% of) the most parts any
    single report lists for that province. A **zero** rollup counts only when
    complete. One district's zero never becomes a province zero.
  - Weekly and daily rollups are dropped where a direct weekly row covers the
    week.
  - An **incomplete** rollup is a lower bound: it is used only where no positive
    direct total overlaps it, and its weeks are labelled `rollup_partial`.
  - A complete multi-week rollup is dropped only for a positive direct total of
    comparable span (0.5x-2x) covering >= 50% of it; finer complete rollups
    inside a longer total are kept as nested evidence.
  - Completeness is counted per reporting level: former provinces in the
    province slot need 2+, districts 3+.
- **rollup_partial**: as rollup, from an incomplete list of parts. A lower bound
  for the province, never used inside a province-reported total.
- **area**: a reported zero for an area made of whole provinces is applied to
  each of them. Such areas are a `(A|B)` composite in the province slot, or a
  single-era split legacy unit with child-identified successors. Area zeros
  never displace positive rollups.
- Zero rows shorter than 6 days are ignored (a one-day zero does not assert a
  zero week). Every 6-7 day row is placed in the ISO week holding its midpoint,
  as the national engine now also does (it keyed weekly rows by start date until
  2026-11-25, putting Sunday-Saturday reporting weeks one week early).

## Engine and seasonal template

The national evidence ladder (`build_weekly_timeseries.process_country`, imported
unchanged): observed weeks > documented zeros and multi-week totals, finest span
first, each distributing only its residual > inferred zeros. The national
`assumed_zero` gap fill is dropped: an unreported province-week stays missing.

Multi-week totals are spread with a BIC-selected Fourier template: the province's
own where it has >= 3 outbreak-years of weekly data (`template` = `province_kN`),
otherwise the country's national template (`national_...`).

Every week records `source_span_days` - the span of the row that filled it (7 for
observed weeks). Totals longer than 2 years are spread as the national builder
does (e.g. CIV's 2002-2017 province totals, MWI's 2001-2018 district totals), and
can be filtered by this column, or excluded at build time with
`--max-spread-days N` (lists them in `cholera_adm1_long_totals_{ISO}.csv`).

## Outputs (per country, `data/{ISO}/`)

Names avoid the `cholera_weekly_` prefix on purpose: MOSAIC-pkg's
`process_AI_cholera_data()` reads every `^cholera_weekly_.*\.csv$` file as a
national series.

- `cholera_adm1_weekly_{ISO}.csv`: `iso_code, adm1_name, adm1_code, year, iso_week,
  week_start, week_end, sCh, deaths, source, confidence_weight,
  disaggregation_method, evidence, template, source_span_days`
- `cholera_adm1_reconciliation_{ISO}.csv`: sum of provinces vs national per week
- `cholera_adm1_unallocated_{ISO}.csv`: rows not assigned, with status and reason
- `reference/subnational/province_build_summary.csv`: per-province weeks, methods,
  template, totals

## Red-team review (2026-11-25)

Three independent reviews (code, reference tables, outputs), followed by
re-reviews of the rewrite, found and led to fixes for the following:
- output names that MOSAIC-pkg would have read as national data;
- partial district zeros becoming province zeros;
- partial rollups suppressing province totals;
- start-date week keying;
- nested-sibling double counting;
- coarse totals displacing finer rollups;
- cross-era and district-level area zeros;
- shifted-parent double counting;
- merger reforms treated as shifted;
- eleven reference-table errors;
- in the second round, an arithmetic "total" heuristic that dropped real counts,
  cross-report merges of one place spelled two ways, completeness counted
  across mixed levels, and partial lists crowding out province totals.

Inherited from the national engine and not changed here, because changing them
would also change the national series:
- Source priority (WHO > JHU > AI) can let a higher-priority zero override a
  larger lower-priority count in the same week (about 31 weeks, 4.2k cases;
  e.g. NGA Zamfara 2018-W29).
- Totals of 8-13 days are skipped when weekly rows cover half their weeks (e.g.
  ZWE Matabeleland South AI 2776).
- A positive total that shares its weeks with a documented zero reaching outside
  its span keeps only the seasonal share of its free weeks. MOZ Nampula 1998
  gets 1,186 of AI 4570's 2,755, against a documented zero to 1998-09-20.
- Overlapping cumulative series from one source with different start dates are
  each decumulated and placed. ZWE Harare 2018 is 16,386 against JHU's annual
  10,133. This is the same-source overlap issue known in the national builder.
- A week built from 1-3 days of daily rows is labelled observed.
- JHU weekly zero tables in active outbreaks (NGA 2018 states, COD 2017-18)
  count as observed coverage and can suppress province totals; these are source
  conflicts to review.

The start-date week keying was fixed in the national builder too
(`build_weekly_timeseries.py`: Tier 1, the typed pilot path and template
building), with a regression check (2026-11-25, as of 2026-11-25):
- 36 of 40 countries' weekly series changed, plus NPL's confirmed series;
- gap analyses, validator findings and BGD were unchanged;
- 26,297 of 117,093 country-weeks changed, and total cases fell 1.15%;
- the fall is almost all ZWE 2008-09, which went from 161,941 (overlap-inflated)
  to 98,592, the reported epidemic total;
- 19 country-years changed by more than 5%, e.g. SSD moved about 4.8k cases from
  2016 into 2017, consistent with the outbreak peaking in 2017.

## Known data issues surfaced by the build

- **SSD 2023, Upper Nile (Renk)**: JHU weekly rows of 300-700 cases/week through 2023
  (several identical values of 329) against a national series of 1,473 for the year;
  the documented Renk outbreak began in December 2023. Likely AWD counts; needs
  review in `data/SSD/cholera_data_jhu.csv`.
- **TZA "Mainland"/"Zanzibar"** rows (about 1.0M cases, 1970-2026) are territory
  totals and remain unallocated.
- Some districts are filed under the wrong province in the source data (CMR health
  districts, TCD Moussoro/Goz Beida); child-level aliases can correct them.
