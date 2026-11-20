# Development Plan: Adding Nepal (NPL) to the AI Data Mining Pipeline

**Status:** Phases 0–5 implemented on branch `feature/nepal-pilot` (2026-11-20), plus the MOSAIC-pkg guard on MOSAIC-pkg branch `feature/ai-pilot-iso-guard`. Phase 6 (the pilot run) has not been run. First draft 2026-11-18; revised 2026-11-20 after two red-team reviews (see `## Changes from the first draft`).
**Scope:** Nepal only, as a pilot that tests whether the pipeline generalises beyond the 40 African MOSAIC countries.
Bangladesh is deliberately excluded (see `## Why not Bangladesh too`).

## Implementation status (2026-11-20)

One commit per phase on `feature/nepal-pilot`. The regression gate (`py/regression_snapshot.py`, reference snapshot `reference/regression/snapshot_c6a1d680_asof_2026-11-18.json`) reports 84/84 items identical after every phase. Tests: `python -m pytest py/tests` (18 tests).

Where the implementation departs from the text below:

- **Gap files for pilots go to `reference/pilot/`,** not into the shared `reference/effective_surveillance_*.csv`. `analyze_effective_gaps.py` writes them automatically when `data/{ISO}/` exists for a pilot. Appending Nepal to the shared files would have changed the dashboard's coverage averages and the recency windows. The orchestrator and `country_notes` point Nepal's agents to the pilot files, and `xref_harvest.py` reads both.
- **Nepal's domains are in `reference/priority_sources_pilot.txt`,** not `priority_sources.txt`, so the dashboard's source count does not change.
- **Phase 1b.** Only the scripts that must accept a named pilot were switched to `py/scope.py`: `add_observation`, `validate_quality`, `build_weekly_timeseries`, `analyze_effective_gaps`, `build_country_profiles`, `convert_jhu/who_to_workflow`, `xref_harvest`, `generate_dual_timeline_plots` and `run_status`, plus the runner. The other scripts already loop over the 40 and need no change; switching them would have added risk without changing behaviour.
- **Dashboard national-row classification** stays shape-based (`{prefix}::[A-Z]{3}`) with per-country prefixes. A strictly per-ISO rule would have reclassified one mis-filed JHU row, `AFR::ZWE` inside `data/ZAF/cholera_data_jhu.csv`. That row is reported, not changed.
- **Count-basis `status` values** are `verified` (checked against source text), `inferred` (shown by the source data's own numbers, e.g. WHO 2016 169 = JHU 21303's confirmed count) and `provisional`. No entry is `verified` yet: that is pilot work. `WHO:dashboard` is `suspected`/`provisional`, because its annual sums exceed the confirmed counts in every year where both are known; 2024 (360 vs 95) remains the open conflict.
- **Decumulation is per source document** (collection, dashboard or AI source) on the typed path. Pooled by layer, JHU 21508's cumulative 2024 chain absorbed WHO-annual 2024.
- **`validate_quality.py NPL`** reports INFO `pilot_not_started`, not an error, until Agent 1 creates the AI layer.
- **`add_observation.py` writes the pilot tag itself.** The validator still errors on hand-edited rows without it.
- **The global cross-country sweep (`registry`/`parse`/`screen`) was not run.** It re-screens every country against data changed since 2026-10-08. 27 cached multi-country documents mention Nepal. Run the sweep between country runs, before Phase 6 step 1.
- **Baseline-file note text.** The JHU converter's phantom-zero note now reads "Phantom row; zero not verified" for every country. This affects future conversions only; the 40 countries' baseline files are not regenerated on this branch.

First Nepal build (`python py/build_weekly_timeseries.py --iso NPL`):
- **Suspected series:** 84 observed weeks (2010 JHU weekly; 2023–2025 WHO dashboard) and 1,312 undistributed weeks.
- **Confirmed series:** 10 observed weeks (2024).
- **Period totals:** 49.
- **Held out:** 139 rows (126 zero rows, 9 untyped or unknown, 4 AGE). Listed in `data/NPL/builder_holdout.csv`.
- **Years with no usable suspected count:** 1999–2009, 2011–2015 and 2017–2020.

## Goal

Produce `./data/NPL/` with:

- baseline files from JHU and WHO;
- an AI enhancement layer from the 7-agent workflow;
- a suspected-case weekly series at `./data/NPL/cholera_weekly_NPL.csv`, built only from rows whose count type is documented;
- a separate confirmed-case series at `./data/NPL/cholera_weekly_confirmed_NPL.csv`;
- a curated table recording what each source counted in each year (`./reference/count_basis/NPL.csv`).

Hard constraints:

- The 40 MOSAIC countries' outputs must not change. This is checked by a deterministic regression gate (Phase 0).
- Nepal is not picked up by any default loop: the run queue, preflight checks, dashboard, supervisor or status page.
- Nepal stays out of MOSAIC-pkg.

**What the pilot is for.** It tests whether the pipeline can work for a non-African country. It does not produce a model-ready series. MOSAIC-pkg has no Nepal inputs (shapefiles, climate, mobility, suitability). And because Nepal's sources switch between counting confirmed and suspected cases, its series needs a separate count-type design review before any modelling use (Phase 7).

## What to expect

These figures come from the 2026-11-18 evaluation, corrected by the red-team reviews.

- **Existing baseline:**
  - **WHO annual totals:** about 37 of the 56 years 1970–2025. In some years the total is suspected cases, in others confirmed only (2016: 169, which equals JHU's confirmed count).
  - **JHU:** 26 collections, 785 rows, including rows for 2008 and 2013.
  - **WHO dashboard:** weekly national counts for 2023–2025 (14 / 360 / 1,899). The 2024 figure (360) does not match the 95 confirmed cases in WER and EDCD; the dashboard's count type is not yet known.
- **Sources the AI layer can add:**
  - EDCD EWARS weekly bulletins, 2020–Sep 2022. These are confirmed counts from sentinel hospitals, mirrored on ReliefWeb.
  - EDCD outbreak situation reports (sitreps), e.g. the Kathmandu Valley 2022 outbreak.
  - DoHS annual reports, which are indexed by Nepali fiscal year.
  - WHO SEARO bulletins (Birgunj 2025).
  - IFRC DREF reports (2009, 2010, 2022, 2025).
  - Open-access papers on the 2016 Kathmandu and 2021 Kapilvastu outbreaks.
  - News coverage that quotes EDCD.
- **Gaps that are probably irreducible:** 1982–88 and 1999–2006.
- **The baseline alone already covers about 40 of 56 years.** Annual coverage is therefore not a useful success measure. What matters is whether the 2018–2025 calibration window has a consistent count type (see the Phase 6 acceptance criteria).
- **Realistic end state:**
  - suspected-case annual totals for most years 2018–2025, each with a documented count type;
  - a confirmed-case weekly series for EWARS 2020–2022, plus the 2024 sitreps;
  - weekly or daily outbreak detail for 2021, 2022 (sub-national only), 2024 and 2025;
  - no zero rows.

## Blockers in the current code

| # | Blocker | Where | Effect on Nepal |
|---|---|---|---|
| B1 | Scope is hard-gated to the 40 countries | `CLAUDE.md` (scope restriction); `py/add_observation.py:185` (`check_scope`); 19 scripts filter on `mosaic_framework` (list in Phase 1); rule 7 "Scope is the 40 MOSAIC countries" in six `.claude/agents/*.md` files | Nepal can't be written, validated or gap-analysed. Agents are told not to work on it |
| B1a | Every all-country loop assumes exactly the 40 | Run queue built from `reference/effective_surveillance_recency.csv` (`run_all_countries.sh:140`); preflight `build_country_profiles.py --check` and `validate_quality.py` (`run_all_countries.sh:103-106`); completion summary (`run_all_countries.sh:502`); `py/run_supervisor.sh:30`; `py/run_status.py` (`countries_total: 40`); `py/validate_dashboard.py:133` (exactly 40 table rows); `OUT_OF_SCOPE_NEIGHBORS` in `py/build_country_profiles.py:37` | If Nepal is added to the shared scope, preflight fails for every country, the dashboard check fails, and the unattended queue picks Nepal up |
| B2 | Location prefix hard-coded to `AFR::` | `py/add_observation.py:339,430,455`; `py/validate_quality.py:55` (regex), `:374` (check); `py/build_weekly_timeseries.py:224,308`; `py/convert_who_to_workflow.py:250`; `py/xref_harvest.py:519` (`REGION_PREFIXES`), `:1212,1389,2277,2321`; `py/generate_coverage_heatmap.py:112,115`; `py/generate_dual_timeline_plots.py:110,113` | JHU stores Nepal as `SEAR::NPL`. The weekly builder would ignore all of it, the same blind spot that already hides 736 `EMR::SOM` rows |
| B3 | Count types are mixed and not recorded | `py/build_weekly_timeseries.py:325` (`has_count = raw_sch != ""`), `:509` (rows without `sCh` skipped); `py/convert_jhu_to_workflow.py:184` (rows with neither `sCh` nor deaths dropped) | EWARS confirmed-only rows vanish. WHO confirmed-only annual totals sit in `sCh` and are treated as suspected. MOSAIC-pkg keeps only named columns (`process_AI_cholera_data.R:98`), so a count-type column would be lost downstream |
| B4 | Zero handling | Tier 3 `inferred_zero` (`py/build_weekly_timeseries.py:695-704`); assumed-zero fill (`:713-737`); `convert_jhu_to_workflow.py:180` labels phantom zero rows "Zero transmission period validated by JHU" | Sentinel zero weeks, WHO's 2020 zero and Nepal's data gaps would all become zero weeks inside the calibration window |
| B5 | Seasonal template falls back to a pool built from African data | `py/build_weekly_timeseries.py:246-297` | Nepal's annual totals would be spread using African seasonality. Nepal's rows would also enter the pool and shift the template for the 40 countries |
| B6 | JHU converter covers African names only | `py/convert_jhu_to_workflow.py:31` (`COUNTRY_ISO_MAPPING`); no single-country option; no age/sex filtering | No Nepal mapping. 376 of 785 Nepal rows are age- or sex-stratified |
| B7 | WHO converter covers African names only | `py/convert_who_to_workflow.py:68` (name map), `:370` (MOSAIC filter) | Nepal's 2023–2025 dashboard weekly counts can't be imported |
| B8 | No reference data for Nepal | `reference/country_mapping.json` (regenerated by `py/get_iso_codes.py` with a fixed schema), `reference/country_profiles.json`, `reference/priority_sources.txt` | No provinces, languages, disease terms or ministry domains for Nepal. Hand-added mapping fields would be wiped on the next regeneration |
| B9 | Agent instructions are worded for Africa, and the planned prompt mechanism doesn't reach agents | `templates/template_search_protocol.txt:106-140`; `.claude/agents/cholera-baseline-collector.md:63`; `.claude/agents/obscure-source-explorer.md:73`. The runner calls `claude -p ISO --agent workflow-orchestrator` (`run_all_countries.sh:324`) and never calls `py/generate_country_prompt.py` | Placeholders in prompt templates would never be filled. The only per-country channel that reaches agents is `reference/country_profiles.json`, which the orchestrator reads |
| B10 | The cross-country harvest step blocks Nepal | `py/xref_harvest.py:173` (Nepal is in the `XOT` block-list); zero screened rows for Nepal | `xref_harvest.py queue NPL` would return nothing |
| B11 | MOSAIC-pkg reads every weekly file | `MOSAIC-pkg/R/process_AI_cholera_data.R:71` (no ISO filter); `:86-90` keeps `observed`, `documented_zero`, `inferred_zero` and `fourier_*` | Once a Nepal weekly file exists, Nepal flows into MOSAIC-pkg |
| B12 | Nepali case definitions and dates | None | EWARS counts confirmed cholera separately from acute gastroenteritis (AGE, about 7–8k cases a year). DoHS uses Bikram Sambat fiscal years (Shrawan 1 ≈ mid-July). An unconverted year such as 2077 is already caught by the validator's future-date check (`py/validate_quality.py:402-409`), so no new date rule is needed |

The repo has no automated test suite. Phase 0 adds a regression gate that every later phase depends on.

## Decisions needed before starting

These are decisions for the project owner. Each has a recommended default.

1. **Scope policy.** Allow named pilot countries without adding them to the shared 40-country scope.
   *Default:* yes. Pilot countries go in a separate overlay file and are only processed when named explicitly. CLAUDE.md and rule 7 in the agent files name Nepal as the only pilot.
2. **Should Nepal flow into MOSAIC-pkg?**
   *Default:* no. An ISO filter in MOSAIC-pkg (Phase 2) lands before any Nepal weekly file exists.
3. **Count types.**
   *Default:* never put confirmed counts in the suspected series. Keep a separate confirmed series. Record each source-year's count type in a curated table; for Nepal, the builder uses only rows whose count type is documented.
4. **Zeros.**
   *Default:* Nepal has no zero rows of any kind during the pilot. No agent-added zeros, no inferred zeros and no assumed-zero fill. Weeks with no data stay empty.
5. **Seasonal distribution.**
   *Default:* Nepal's annual and multi-week totals are not distributed into weeks during the pilot. They are written as `undistributed`. Nepal's weekly data comes from two outbreaks at most, which is too thin for a seasonal template.
6. **Somalia's `EMR::SOM` rows.**
   *Default:* build the mechanism now but leave Somalia's behaviour unchanged. Fixing Somalia gets its own reviewed change (Phase 7).

## Plan

### Phase 0: Deterministic regression gate (about 0.5 day)

The gate must exist before any code changes. The first draft's "byte-identical outputs" check could never pass: several outputs depend on today's date, and the shared gap-analysis files gain Nepal rows once Nepal is processed.

- **Pin the date.**
  - Add an `--as-of YYYY-MM-DD` option to `py/build_weekly_timeseries.py` (replacing `SERIES_END = date.today()` at `:68`) and to `py/validate_quality.py` (`today()` at `:95`).
  - `py/analyze_effective_gaps.py` already has `--end-date`.
- **Add `py/regression_snapshot.py`.** For the 40 MOSAIC countries only, it hashes:
  - each `data/{ISO}/cholera_weekly_{ISO}.csv`;
  - the 40 countries' rows in each `reference/effective_surveillance_*.csv`, filtered by ISO so that adding Nepal's rows doesn't change the hash;
  - `validate_quality.py --json` output, with timestamps stripped.
- **Take the reference snapshot from a fixed worktree.**
  - Use `git worktree add ../aicdm-baseline <commit>` at the pre-change commit, with a fixed `--as-of`.
  - Every later phase reruns the same commands with the same `--as-of` in the working tree and must match.
- **Tests.** Add `py/tests/` (pytest). Fixtures live in `py/tests/fixtures/`, never under `data/`; `update_dashboard.sh:237` auto-commits any `data/*/cholera_weekly_*.csv`.

**Acceptance:** running the snapshot twice on the unchanged tree gives identical hashes.

### Phase 1: Pilot scope flag (about 1 day)

**1a. Scope overlay, not mapping fields.**
- Put pilot countries and per-country pipeline settings in a new hand-maintained file, `reference/pipeline_countries.json`.
  - `country_mapping.json` is left untouched, because `py/get_iso_codes.py` regenerates it from `reference/mosaic_country_codes.csv` with a fixed schema and would wipe added fields.
- Settings for each country:

  | Setting | Meaning | 40 MOSAIC countries | Nepal |
  |---|---|---|---|
  | `pilot` | Country is processed only when named | absent | `true` |
  | `location_prefix` | Prefix written on new rows | `AFR` | `SEAR` |
  | `accept_prefixes` | Prefixes read as this country | `["AFR"]` (Somalia too, for now) | `["SEAR"]` |
  | `template_pool` | Seasonal-template pool | `africa` | `none` |
  | `count_basis_table` | Builder uses only rows typed in `reference/count_basis/{ISO}.csv` | `false` | `true` |
  | `zero_policy` | Which zero rows are allowed | `default` | `none` |

- Add a shared module `py/scope.py`. It merges the mapping and the overlay and provides:
  - `mosaic_isos()`: the 40 countries, used by every all-country loop;
  - `pilot_isos()`;
  - `resolve_isos(requested)`: accepts MOSAIC or pilot ISO codes when named explicitly and rejects everything else;
  - `settings(iso)`, covering the fields above.

**1b. Switch the scripts.**
- **Default loops stay on the 40.** These 19 scripts currently read `mosaic_framework` directly:
  - `add_observation`, `analyze_effective_gaps`, `analyze_baseline_gaps_optimized`, `analyze_integrated_coverage_gaps`
  - `build_country_profiles`, `build_weekly_timeseries`, `convert_who_to_workflow`, `evaluate_fourier_seasonality`
  - `generate_country_status_page`, `generate_coverage_heatmap`, `generate_dual_timeline_plots`, `generate_monthly_surveillance_matrix_v2`
  - `get_iso_codes`, `get_workflow_status`, `repair_data_integrity`, `update_completion_checklist`, `update_dashboard_data`, `validate_quality`, `xref_harvest`

  Each switches to `scope.mosaic_isos()` for its default loop, so default behaviour is unchanged.
- **Commands that take ISO codes** route them through `resolve_isos`, so a pilot ISO works only when named:
  - `add_observation.py ... NPL`;
  - `validate_quality.py NPL`;
  - `build_weekly_timeseries.py --iso NPL`;
  - `analyze_effective_gaps.py --include NPL`. This appends Nepal's rows to the shared gap files. The regression gate ignores them, and the run queue filters them out (below).
- **`check_scope`** (`py/add_observation.py:185`) accepts MOSAIC and pilot ISOs.

**1c. Keep Nepal out of unattended runs.**
- **Run queue** (`run_all_countries.sh:140`): build it only from `mosaic_isos()`. A pilot ISO runs only through `--only`.
- **Preflight** (`run_all_countries.sh:103-106`):
  - checks the 40 as now;
  - when `--only` names a pilot, it also checks that country's profile and `validate_quality.py {ISO}`.
- **Completion summary** (`run_all_countries.sh:502`): intersect `--only` with MOSAIC + pilot ISOs. With the current code, `--only NPL` intersected with the 40 gives an empty set and reports "complete" trivially.
- **`py/run_supervisor.sh:30` and the dashboard:**
  - The supervisor stays MOSAIC-only. The pilot is launched directly, never through the supervisor.
  - `py/validate_dashboard.py:133` keeps its 40-row check. Nepal is not added to the dashboard during the pilot.
- **`py/run_status.py`:** take `countries_total` from the run's `--only` list instead of the hard-coded 40.
- **Profiles** (`py/build_country_profiles.py:37`): add `IND` and `CHN` to `OUT_OF_SCOPE_NEIGHBORS`.

**1d. Instructions.**
- Amend the CLAUDE.md scope section to name Nepal as the only pilot country.
- Change rule 7 in the six agent files to: "Scope is the 40 MOSAIC countries plus pilot countries listed in `reference/pipeline_countries.json`."
  - The six files are `cholera-baseline-collector`, `geographic-expansion-specialist`, `zero-transmission-validator`, `obscure-source-explorer`, `cross-reference-integrator` and `gap-context-investigator`.
  - All other non-MOSAIC countries stay prohibited.

**Acceptance:**
- The regression gate passes.
- `bash run_all_countries.sh --dry-run` (default queue) lists exactly the 40 countries, and its preflight passes.
- `python py/add_observation.py register-source NPL ...` no longer exits with the scope error. `register-source IND ...` still does.

### Phase 2: Region-aware location prefixes and the MOSAIC-pkg guard (about 1 day)

**2a. Validation and writing.**
- `py/validate_quality.py:55`: change the regex to `^(AFR|EMR|SEAR)::[A-Z]{3}(::[^:]+)*$`.
- `py/validate_quality.py:374`: after the format check, check that the prefix is in `settings(iso).accept_prefixes`. Update the error message, which currently says "AFR::ISO".
- `py/add_observation.py:339,430,455`: default and validate using `location_prefix`. New Nepal rows are written as `SEAR::NPL...`, matching JHU.

**2b. Builder.** `load_national_rows` and `load_all_weekly_rows` (`py/build_weekly_timeseries.py:224,308`) match against `{p}::{iso}` for each accepted prefix.

**2c. Other scripts.**
- `py/convert_who_to_workflow.py:250` uses `location_prefix`.
- `py/xref_harvest.py`: derive `REGION_PREFIXES` (`:519`) from the overlay, and replace the four hard-coded `f"AFR::{iso}"` at `:1212,1389,2277,2321`.
- `py/generate_coverage_heatmap.py:112,115` and `py/generate_dual_timeline_plots.py:110,113`: build the national-row match from each country's `accept_prefixes`.
  - Do **not** use a generic `^[A-Z]{3,4}::[A-Z]{3}$` regex. It would reclassify 256 `EMR::SOM` rows and change Somalia's figures.

**2d. MOSAIC-pkg guard** (separate commit in `MOSAIC-pkg/`):
- In `R/process_AI_cholera_data.R`, after the files are read, keep only `iso_code %in% MOSAIC::iso_codes_mosaic`.
- Log the excluded ISO codes so the exclusion is visible.
- Add a testthat test that uses a fake `NPL` file in a temp directory.

**Acceptance:**
- The regression gate passes. Somalia is unchanged.
- A dry-run row `SEAR::NPL::Bagmati` passes validation, and `AFR::NPL` is rejected.
- MOSAIC-pkg's processed output is unchanged when a fake Nepal weekly file is present.

### Phase 3: Count types, zeros and distribution in the builder (about 2 days)

All of this applies only when the country's settings ask for it. The 40 countries take the existing code path unchanged.

**3a. Count-basis table.** Add one hand-curated file per opted-in country, `reference/count_basis/{ISO}.csv`, with these columns:

| Column | Meaning |
|---|---|
| `source_key` | `JHU:<collection id>`, `WHO:annual`, `WHO:dashboard`, or `AI:<metadata Index>` |
| `year_from`, `year_to` | Years the entry covers |
| `basis` | `suspected`, `confirmed`, `age` (acute gastroenteritis), `mixed` or `unknown` |
| `field` | Column the count sits in (`sCh` or `cCh`) |
| `evidence` | Quote or citation showing which case definition the source used |

The table is needed because the count type can't be inferred from which column is filled: WHO's 2016 total of 169 is confirmed-only but sits in `sCh`.

**3b. Two series.** For a country with `count_basis_table: true`:
- **Suspected series** (`cholera_weekly_{ISO}.csv`).
  - **Baseline rows (JHU, WHO)** are used only when their source-year resolves to `basis=suspected`. Rows that resolve to anything else, or that have no entry, are held out and listed in `./data/{ISO}/builder_holdout.csv`.
  - **AI rows** are used when they have `sCh`. The prompt and validator rules in Phase 5 govern how agents assign columns, and Agent 7 adds table entries for AI sources that cite WHO or WER annual figures.
- **Confirmed series** (`cholera_weekly_confirmed_{ISO}.csv`).
  - Rows that resolve to `basis=confirmed`, and AI rows with only `cCh`.
  - The series has observed weeks only: no template distribution and no zeros.
  - MOSAIC-pkg's file pattern `^cholera_weekly_.*\.csv$` would match this file. The Phase 2d ISO guard covers it; also rename it if MOSAIC-pkg is ever opened to Nepal.
- **No `count_basis` column** is added to the weekly CSVs. The basis follows from which file a week is in, so the 40 countries' files are untouched.

Effects:
- Sentinel-confirmed weekly rows no longer cover weeks in the suspected series. The 50% coverage rule (`:602-604`) therefore no longer suppresses the WHO 2021 suspected total of 1,609.
- Source priority (`SOURCE_PRIORITY`, `:568`) applies only among rows of the same basis.

**3c. Zero policy.** For a country with `zero_policy: none`:
- `py/add_observation.py add-zero` refuses to write.
- The builder drops every row with `sCh = 0` and records it in `builder_holdout.csv`.
- Tier 3 `inferred_zero` and the assumed-zero fill are skipped. Weeks with no data are left out of the file, which MOSAIC-pkg would read as missing.
- In the JHU converter (`:180`), the "validated by JHU" note on phantom zero rows becomes "Phantom row; zero not verified" for every country. Only the note text changes, not the values or the weights, so the regression gate is unaffected.

**3d. Undistributed totals and template isolation.**
- For a country with `template_pool: none`, any suspected row longer than a week is written with the new method label `undistributed`:
  - one line per ISO week in its span, with a blank `sCh`;
  - the total in a new `period_total` column, on the first week only.
- `undistributed` weeks count as covered, so no later step can fill them.
- MOSAIC-pkg's keep filter (`:86-90`) would drop the label anyway, as an extra safeguard behind the ISO guard.
- The regional and continental template pools (`:246-297`) are built only from countries with `template_pool == "africa"`. Nepal's rows can never shift the African templates.
- `plot_weekly_series` labels the template source (it currently calls the fallback "continental") and draws `undistributed` periods as bars spanning their weeks.

**Acceptance:**
- The regression gate passes.
- A synthetic Nepal fixture produces the expected two series. It contains a confirmed-only EWARS week, a WHO annual total marked confirmed, a WHO annual total marked suspected, a zero row and a multi-month total. In it:
  - the confirmed rows never appear in the suspected file;
  - the zero row is held out;
  - the multi-month total becomes `undistributed` weeks;
  - no week has `assumed_zero` or `inferred_zero`.

### Phase 4: Nepal baseline (about 1 day)

**4a. JHU converter.**
- Add `--iso` (single-country) and `'Nepal': 'NPL'` to `COUNTRY_ISO_MAPPING` (`:31`).
- For Nepal:
  - drop rows with any of `age_L`, `age_R`, `sex` set (376 strata rows; the unstratified totals are kept);
  - **keep phantom rows**;
  - keep rows that have `cCh` but no `sCh` (`:184` currently drops them).
- Log every skipped row, with its collection ID and reason, to `./data/NPL/jhu_skipped_rows.csv`. Not `attribution_review.csv`, which is for citation problems.
- The 40 countries are unchanged; the regression gate checks this.

**4b. Collection triage.** Record each decision as a count-basis table entry, with evidence.

| Collection | Finding | Action |
|---|---|---|
| 21301 (2011–14) | sCh 4,577 / 1,744 / 5,042 / 4,170 against cCh 3 / 35 / 4 / 600. The sCh values look like AGE | Check against the source. If it is AGE: `basis=age` for sCh and `basis=confirmed` for cCh. The builder then holds the sCh values out, and an AI row can supply the suspected count. This works because JHU would otherwise outrank AI, and the baseline file stays a faithful copy of JHU |
| 21541 (2021 Kapilvastu) | Its phantom row is the only national 2021 total: 2,023, equal to the sum of the municipal rows | Keep it. Determine its basis (suspected is likely). Reconcile it against WHO's 1,609 and record the explanation |
| 21542 (2022–24, 641 rows) | National rows exist only for 2024: 68 daily rows summing to 95, which matches the 95 confirmed in WER and EDCD. The 2022 rows are district-level only | `basis=confirmed` for 2024, so it goes to the confirmed series. Check that `_decumulate` produces 95. The 2022 rows don't feed the national series |
| 436 (WHO annual) | Count type varies by year (2016: 169 = confirmed); 2020 has `sCh = 0` | One table entry per year. 2020 is held out under the zero policy |
| Legacy names (Seti, Bheri, Sagarmatha, Dhawalagiri, Province2; "Bagmati" is both an old zone and a current province) | Old zones versus the 7 post-2015 provinces | Map them through `adm1_legacy` in the country profile. The national series is unaffected |

**4c. WHO converter.**
- Add `"NEPAL": "NPL"` to the name map (`py/convert_who_to_workflow.py:68`), and route `:370` through `resolve_isos`.
- Delete `./data/NPL/cholera_data_who.csv` before any re-run (known bug: the converter appends duplicates).
- Confirm that `reference/who_epiweek_calendar.json` covers 2023–2025.
- Add `WHO:dashboard` entries to the count-basis table. The 2024 conflict (360 on the dashboard against 95 confirmed) stays `unknown` until a source settles it.

**4d. Lock and regenerate.**
- Register the new baseline files in `reference/baseline_checksums.json` via `py/protect_baselines.py`.
- Run `python py/analyze_effective_gaps.py --include NPL`.
- Run `python py/build_weekly_timeseries.py --iso NPL`.

**Acceptance:**
- `python py/validate_quality.py NPL` exits 0.
- Every JHU and WHO source-year that has non-zero Nepal rows has a count-basis entry.
- `builder_holdout.csv` lists every held-out row with a reason.
- The regression gate passes.

### Phase 5: Reference data, agent instructions and cross-country harvest (about 1.5 days)

**5a. Country profile.** Add Nepal to `py/country_profiles_data_b.py` (or `_a`), then run `python py/build_country_profiles.py` and `python py/verify_country_profiles.py`.

| Field | Value |
|---|---|
| `adm1` | Koshi, Madhesh, Bagmati, Gandaki, Lumbini, Karnali, Sudurpashchim |
| `adm1_legacy` | The 14 pre-2015 zones and 5 development regions; "Province 2" = Madhesh; "Province 1" = Koshi |
| `major_cities` | Kathmandu, Lalitpur, Bhaktapur, Birgunj, Biratnagar, Pokhara, Nepalgunj, Dhangadhi, Butwal, Janakpur |
| `neighbors` | IND, CHN (search hints only; covered by `OUT_OF_SCOPE_NEIGHBORS` from Phase 1) |
| `search_languages` | ne, en |
| `disease_terms` | हैजा (cholera); झाडापखाला (diarrhoea / AGE; for context only, never counted as cholera); "acute gastroenteritis"; "acute watery diarrhoea" |
| `health_domains` | edcd.gov.np, dohs.gov.np, mohp.gov.np, nphl.gov.np, nhrc.gov.np |
| `season` | "Monsoon Jun–Sep; Kathmandu Valley urban outbreaks; Terai (Madhesh, Lumbini) and far-west hill outbreaks; 1990–91 major epidemic" |
| `regional_sources` (new) | WHO SEARO (searo.who.int), WHO WER, EDCD EWARS bulletins, IFRC GO, ReliefWeb |
| `archive_hints` (new) | NHRC eLibrary, Gorkhapatra archives, WHO SEARO archives |
| `country_notes` (new) | The guidance in 5d |

**5b. Priority sources.** Add to `reference/priority_sources.txt`:
- Tier 1: `edcd.gov.np`, `dohs.gov.np`, `mohp.gov.np`, `nphl.gov.np`.
- Tier 2: `nhrc.gov.np` (including `elibrary.nhrc.gov.np`), `go.ifrc.org` / `go-api.ifrc.org`.
- Tier 3: `kathmandupost.com`, `thehimalayantimes.com`, `myrepublica.nagariknetwork.com`, `ekantipur.com`.

**5c. Delivery through the profile.** The orchestrator already reads `reference/country_profiles.json`; that file is the only per-country channel that reaches agents.
- `.claude/agents/workflow-orchestrator.md`: when the profile has `country_notes`, paste them verbatim at the top of every subagent prompt.
- `templates/template_search_protocol.txt:106-140`, `cholera-baseline-collector.md:63` and `obscure-source-explorer.md:73`:
  - add one short conditional: "If the profile has `regional_sources` / `archive_hints`, use those in place of the WHO AFRO, Africa CDC and francophone/lusophone archive lists below";
  - leave the African text as it is.
- Don't use placeholders in the template. Nothing in the runner fills them.

**5d. Nepal guidance for agents** (the `country_notes` text):

- **Pilot tag.** Every AI row for Nepal carries `[NPL-PILOT]` in `processing_notes`.
- **Case definitions:**
  - Suspected/AWD outbreak totals go in `sCh`; culture- or RDT-confirmed counts go in `cCh`. Never put AGE totals in either.
  - For a WHO or WER annual figure, quote the case definition the source used. Some WHO annual totals for Nepal are confirmed-only.
- **EWARS counts.** EWARS weekly counts come from sentinel hospitals (40 in 2015, 118 in 2022). Record them as `cCh` at `SEAR::NPL`, with that caveat in `processing_notes`.
- **No zero rows.** Don't add zero rows for Nepal (`add-zero` will refuse them). Record weeks or years with no cases reported, and sentinel zero weeks, in `./data/NPL/cholera_presence_ai.csv` or the search log instead.
- **Bikram Sambat dates.** Convert every BS date and fiscal year to the Gregorian calendar (fiscal year 20XX/YY starts on Shrawan 1, about mid-July) and quote the original in `processing_notes`.
- **Unreachable sites.** `edcd.gov.np` refused connections in testing. Use the Wayback Machine and ReliefWeb (`py/reliefweb.py`; the evaluation needed `SSL_CERT_FILE=/etc/ssl/cert.pem`, so confirm).
- **Priorities:**
  1. Count type for every source-year 2018–2025.
  2. The 2021 conflict: 2,023 from JHU against 1,609 from WHO.
  3. The 2024 conflict: 360 on the dashboard against 95 confirmed.
  4. Suspected totals for the EWARS years 2020–2022.
  5. Gaps 1999–2006 (Agents 1 and 4) and 1982–88 (Agent 4: NHRC eLibrary, Gorkhapatra archives, WHO SEARO archives).

**5e. Validator rules for Nepal** (`py/validate_quality.py`):
- **ERROR when an AI row lacks `[NPL-PILOT]`.** This enforces the tag.
- **ERROR on any `sCh = 0` row** (from `zero_policy: none`).
- **WARN when `processing_notes` matches** `\bAGE\b` (case-sensitive) or `(?i)\b(acute\s+)?gastro-?enteritis\b|झाडापखाला`, and `sCh` or `cCh` is filled. The word boundaries stop it firing on words like "village".
- **WARN when an AI row's source has no count-basis entry and its notes cite WHO or WER annual figures.**

**5f. Cross-country harvest.**
- In `py/xref_harvest.py`, remove `Nepal` from the `XOT` block-list (`:173`) and add an `NPL` pattern (`Nepal|नेपाल`).
- Run `parse`/`screen` for NPL over the existing registry; the WHO multi-country cholera sitreps (about #26–#32) list Nepal.
- Apply the global guardrails: no zeros from absence in a list, and reporting windows are not epidemiological periods.

**Acceptance:**
- `python py/verify_country_profiles.py` passes.
- `python3 -I -B py/xref_harvest.py queue NPL` returns screened items.
- Diffs to the agent and template files are limited to rule 7, the orchestrator's `country_notes` step and the conditional source sentence.
- The regression gate passes.

### Phase 6: Pilot run and audit (1 run, about 4–12 hours of wall time)

1. Seed from the cross-country harvest: run `xref_harvest.py apply --iso NPL` after a `--dry-run`.
2. Run `bash run_all_countries.sh --only NPL` directly, not through the supervisor. It runs in its own process; the runner raises the WebSearch cap to 2000.
3. Agent 7:
   - fills count-basis entries for AI sources that cite WHO or WER annual figures;
   - runs `python py/validate_quality.py NPL`, which must exit 0;
   - writes `search_report.txt` against the success criteria below.
4. Rebuild with `python py/build_weekly_timeseries.py --iso NPL`.
5. Render Nepal's figures with `--iso NPL` to `figures/pilot/NPL/`. Don't link them from the dashboard.

**Acceptance (pilot success).** These are measured on the 2018–2025 calibration window, not on 1970–2025 annual coverage.

- **Count types documented.** Every source-year 2018–2025 used in either series has a count-basis entry. None of them is `unknown` without a logged search for the definition.
- **Totals reconcile.** For each year 2018–2025, the suspected series' annual total either matches the WHO or WER total, or the difference is explained in the count-basis evidence. The 2021 and 2024 conflicts are resolved or documented.
- **Weeks reported.** `search_report.txt` states the number of 2018–2025 weeks in each series: suspected observed, suspected `undistributed`, and confirmed observed. These are reported, not targeted; the point is to see what the pipeline can reach.
- **No zeros.** Neither Nepal series contains a zero week (observed, inferred or assumed).
- **Validation.** All rows pass the validator, and every AI row carries `[NPL-PILOT]`.
- **Nothing else changes.** The regression gate passes. MOSAIC-pkg output is unchanged. The default queue and the dashboard still show exactly the 40 countries.

### Phase 7: Follow-ups (outside the pilot)

- **Count-type design review** before any modelling use of Nepal. Decide how MOSAIC would use a series whose count type varies by year: for example, a reporting-rate parameter that varies by year, or a separate confirmed-case likelihood. The current likelihood assumes one fixed reporting rate for suspected cases (`MOSAIC-docs/04-model-description.Rmd:887-932`).
- **Nepal seasonality.** Revisit distributing totals across weeks once Nepal has at least `MIN_YEARS` outbreak-years of suspected-basis weekly data.
- **Somalia.** Enable `accept_prefixes: ["AFR","EMR"]` for Somalia and review the change in its weekly series and figures (736 JHU rows, 256 national). This fixes the existing Somalia blind spot.
- **The 40 countries.** Decide whether to apply age/sex-stratum filtering, the count-basis table or the zero policy to any of them; check the effect with the regression snapshot diff first.
- **Dashboard.** Add a separate pilot-country section before showing Nepal on the main page.
- **MOSAIC-pkg.** Add Nepal inputs before lifting the Phase 2d guard.

## Effort and order

| Phase | Effort | Depends on |
|---|---|---|
| Decisions | — | — |
| 0 Regression gate | ~0.5 day | Decisions |
| 1 Pilot scope flag | ~1 day | 0 |
| 2 Prefixes and MOSAIC-pkg guard | ~1 day | 1 |
| 3 Count types, zeros and distribution | ~2 days | 2 |
| 4 Baseline | ~1 day | 3 |
| 5 Reference data, instructions and harvest | ~1.5 days | 1 (can run in parallel with 2–4) |
| 6 Pilot run and audit | ~0.5 day of attention plus run time | 4, 5 |

**Total:** about 7–8 developer days plus one pilot run. Phases 0–3 are generic changes. Most of that work carries over to Bangladesh or any other non-African country later.

## Risks

| Risk | Mitigation |
|---|---|
| Refactoring 19 scripts breaks the 40-country outputs | Deterministic regression gate (pinned date, ISO-filtered hashes, fixed worktree) at every phase; one commit per phase |
| Nepal enters unattended runs or the 40-country checks | Pilot countries run only when named; the queue, supervisor, preflight and dashboard stay on `mosaic_isos()` |
| Nepal leaks into MOSAIC-pkg | Phase 2d guard lands before any Nepal weekly file exists; Nepal-only method labels are also dropped by MOSAIC-pkg's keep filter |
| Confirmed and suspected counts mixed in one series | Separate series; curated count-basis table; baseline rows without an entry are held out |
| False zeros in the calibration window | `zero_policy: none`: no zero rows, no inferred or assumed zeros |
| Agents count AGE as cholera | `country_notes` rule, validator warning, count-basis `age` entries; Agent 7 checks every Nepal row with a count |
| Guidance never reaches agents | Delivered through `country_profiles.json`, which the orchestrator already reads, rather than through unused prompt placeholders |
| Thin weekly data gives a poor seasonal template | Nepal totals are `undistributed`; no African seasonality is borrowed |
| EDCD site unreachable | Wayback Machine and ReliefWeb mirrors; documented in `country_notes` |
| Pilot rows hard to audit or roll back | `[NPL-PILOT]` tag enforced by the validator |

## Why not Bangladesh too

The 2026-11-18 evaluation found no observed national cholera series for Bangladesh for 2001–2017. Government reporting doesn't separate cholera from diarrhoea. The WHO dashboard row labelled "Bangladesh" covers the Cox's Bazar camps only. The standard workflow would mostly yield diarrhoea counts and false zeros. Phases 0–3 still remove the technical blockers for it, and the count-basis table and zero policy are exactly what Bangladesh would need. But it needs a curated approach rather than the 7-agent run.

## Changes from the first draft

Two red-team reviews (pipeline engineering and epidemiology) found the following problems, now fixed above.

- **Ordering.** Adding Nepal to the shared scope in Phase 1 would have broken preflight, `validate_dashboard.py` and the unattended queue for all 40 countries. Fixed by the pilot overlay, explicit naming, and the patches to the runner, supervisor and status page (B1a, Phase 1c).
- **Count types.** The confirmed→`sCh` fallback would have produced a series that tracks reporting rules rather than transmission:
  - source priority picks weekly winners regardless of count type;
  - the coverage rule would have suppressed WHO's 2021 total of 1,609;
  - a `count_basis` column would have been dropped by MOSAIC-pkg;
  - WHO already puts confirmed totals in `sCh`.

  Replaced by separate series and a curated count-basis table (Phase 3a–b).
- **JHU triage.** Phantom rows aren't placeholders: 21541's phantom row is the only national 2021 total. 21542's national rows are 2024 only (95 confirmed). 2008 and 2013 have JHU rows, so they aren't irreducible gaps (Phase 4b).
- **Zeros.** Sentinel zeros, WHO's 2020 zero and gap weeks would all have entered as zeros. Replaced by `zero_policy: none` (Phase 3c).
- **Collection 21301.** An AI row couldn't override it because JHU outranks AI. It is now held out through the count-basis table (Phase 4b).
- **Undistributed totals.** Undistributed years would later have been filled as `assumed_zero`, and the template inputs were misdescribed. Fixed by specifying the weeks undistributed rows claim, and by making `undistributed` the default for Nepal (Phase 3d).
- **Prompt delivery.** Prompt placeholders never reach agents, and rule 7 sits in six agent files. Guidance is now delivered through the profile (Phase 1d, 5c).
- **Cross-country harvest.** `xref_harvest.py` blocks Nepal (Phase 5f).
- **Regression gate.** The gate wasn't deterministic (Phase 0).
- **Smaller fixes:**
  - The heatmap regex would have changed Somalia (2c).
  - The prefix check was at the wrong line (2a).
  - `get_iso_codes.py` would have wiped the new mapping fields (1a).
  - The converter needed a single-country option and has to keep rows with only confirmed counts (4a).
  - Skipped rows now go to their own log (4a).
  - The Bikram Sambat validator rule was redundant (B12).
  - The AGE regex needed word boundaries (5e).
  - The pilot tag is now enforced (5e).
  - Test fixtures moved out of `data/` (Phase 0).
- **Success criteria.** The criteria measured 1970–2025 annual coverage, which the baseline already nearly meets. They now measure count-type consistency in the 2018–2025 window (Phase 6).
- **Line numbers.** Two references were wrong: the WHO name map is at `:68`, and `REGION_PREFIXES` is at `:519`.
