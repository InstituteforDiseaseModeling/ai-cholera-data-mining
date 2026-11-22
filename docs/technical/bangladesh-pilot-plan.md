# Development Plan: Bangladesh (BGD) as a Second Pilot Country

**Status:** revised 2026-11-22 after two red-team reviews (pipeline engineering, epidemiology; see `## Changes from the first draft`). Branch `feature/bangladesh-pilot` (from `main` at `c594b1fa`). Work items A–F are set-up; G (the run) waits for the user's review.
**Builds on:** `docs/technical/nepal-integration-plan.md`. Its Phases 0–3 made the pipeline generic: the pilot overlay `reference/pipeline_countries.json`, `py/scope.py`, region prefixes, the typed builder path, `zero_policy: none`, count-basis tables, `reference/pilot/` gap files, the dashboard's pilot section, and the MOSAIC-pkg guard (MOSAIC-pkg branch `feature/ai-pilot-iso-guard`, unmerged). This plan covers only what Bangladesh needs on top.

## Why Bangladesh is harder than Nepal

Bangladesh's problem is not missing data. Almost none of it is a national count of suspected cholera:

| Stream | What it counts | In the baseline |
|---|---|---|
| **National notifications** (WHO annual / WER) | Country reports to WHO. 1950–1970 were reported for Pakistan; JHU attributes them to Bangladesh (unverified). 1971–1979 and 1987–2000: 8 to 10,403 a year, with completeness swinging more than 100-fold (1991: 8; 1993, the O139 epidemic year: 78). No rows 1980–86 or 2001–2014. 2015–2017 phantom zeros | JHU 429, `SEAR::BGD` |
| **Sentinel surveillance** | icddr,b 2 % systematic sample (Dhaka hospital), Matlab (Chandpur district, BD-09; population-based since the 1960s Cholera Research Laboratory trials), the IEDCR/icddr,b national cholera surveillance (22 hospitals, 2014–), 20 suspected cases sampled per site per week in later years. **WHO annual totals since 2023 come from this stream:** WER 99(36) Table 3 for 2023 shows 19,661 of 23,369 RDT-tested, 57 % under 5, and WHO attributes the rise from 1,191 to "increased surveillance and reporting". 2018–2022 (566 / 503 / 212 / 477 / 1,191) are probably sentinel laboratory positives (unverified) | JHU 429 (2018–2024), JHU 21363 (2014-05 to 2018-06: 26,221 diarrhoea patients enrolled / 1,604 *V. cholerae* O1 at `SEAR::BGD`, Khan et al. 2020 CID), JHU 20035, 12223, 12641 (Dhaka O1/O139 isolates), 10940 (BD-09 = Matlab) |
| **Cox's Bazar camps** (~0.9–1 M people; the district is ~2.9 M) | AWD and confirmed cholera in the Rohingya camps (WHO/ISCG EWARS) | **WHO dashboard row "Bangladesh"** (2023–2026: 153 / 575 / 91 / 34; update #33 labels it "Bangladesh (Cox's Bazar)"), **JHU 21505** (2023–2024 cumulative chains at `SEAR::BGD`; 42 per 100,000 on 376 cases implies ~0.9 M), JHU 21127 (`Chattogram::BD-11`, camp **AWD** stored as sCh, up to 4,617 a week), 21149, 21560, 21562, 21563 (`Chittagong Division::Cox's Bazar`) |
| **Diarrhoea / AWD** | DGHS/IEDCR diarrhoea totals, flood surges (1988, 1998, 2004, 2007, 2022 Sylhet, 2024 Feni), icddr,b Dhaka hospital surges | Not in the baseline. The main trap for agents |
| **Clinical "cholera" (ICD-10 A00)** | DGHS DHIS2 / Health Bulletin outpatient counts coded cholera | Not in the baseline. A clinical label: `mixed` |
| **Burden estimates** | Model output (Ali et al. 2015: ~110,000 cases a year) | Never an observation |

## Goal and honest expectations

Produce `./data/BGD/` with the JHU/WHO baseline, an AI layer from the 7-agent workflow (Agent 3 repurposed), a curated `./reference/count_basis/BGD.csv`, the typed-builder outputs, and a sentinel-positivity sidecar.

- **The pilot will very likely produce no usable national suspected series.** At baseline every national source-year is held out: notifications as `unknown` until an agent quotes a WER case definition for that year, the sentinel and camp streams by coverage. A notification year typed `suspected` later still carries the under-reporting caveat and is not for calibration.
- **Its value** is the stream separation, a year-by-year account (1970–2025) of which stream exists and what it counts, the sentinel positivity data (the usable trend and seasonality signal, with Matlab the only series with a population denominator), and a Cox's Bazar sub-national record.
- Coverage % will look good (any row counts). It is not a success measure. **Success = no misleading national series.**
- Not a model-ready series. MOSAIC-pkg has no Bangladesh inputs.

## Hard constraints

- The 40 MOSAIC countries' outputs do not change: `py/regression_snapshot.py take --as-of 2026-11-18` vs `reference/regression/snapshot_c6a1d680_asof_2026-11-18.json`, 84/84 identical, after every item.
- Nepal's outputs do not change: `take --as-of 2026-11-18 --pilots NPL` (new option; rebuilds Nepal's four builder files, pilot gap rows and validator findings into a temp dir) vs the snapshot taken before item A.
- Bangladesh enters no default loop; it runs only when named.
- No edits to MOSAIC-pkg, MOSAIC-data/raw, jhu_cholera_data, ees-cholera-mapping or laser-cholera.
- **MOSAIC-pkg exposure.** MOSAIC-pkg `main` reads every `cholera_weekly_*.csv` under this checkout's `data/` (`process_AI_cholera_data.R:62,71`). Nepal's file is already there (75 observed weeks). During set-up, Bangladesh's builder output goes to the scratchpad only. Before the run (which writes `data/BGD/cholera_weekly_BGD.csv`), the user decides whether to merge the guard branch.

## Design

1. **Settings** in `reference/pipeline_countries.json`: `pilot: true`, `pilot_tag: "[BGD-PILOT]"`, `jhu_name: "Bangladesh"`, `who_name: "BANGLADESH"`, prefix `SEAR`, `template_pool: none`, `count_basis_table: true`, `zero_policy: none`, plus two new settings (default off, so the 40 and Nepal are unaffected):
   - `strict_basis: true` — every national value (sCh or cCh, any layer, including AI rows) needs a count-basis entry; without one it is held out as `unresolved`. (Default behaviour types an untyped AI sCh as suspected and any untyped cCh as confirmed.)
   - `warn_estimate_terms: true` — validator WARN `pilot_estimate_mention` on national AI rows with a count whose notes say estimated / extrapolated / projected / modelled / burden.
2. **Coverage, separate from basis.** The count-basis table gains an optional `coverage` column: `national` (default when blank or absent, so `NPL.csv` is unchanged), `subset` (camps, one district or city) or `sample` (sentinel sites, systematic samples). If any entry for a row's source key and year has coverage other than `national`, the builder holds out the **whole row** (both fields) with reason `coverage <c> - not a national count`. This fixes the leak where an untyped cCh on a camp or sentinel row would enter the national confirmed series. Sample counts are never scaled up.
3. **Basis meanings.** `age` now reads "non-specific diarrhoea (AGE, AWD, diarrhoea totals)"; AWD is not cholera unless the source says cholera. Clinical A00 counts are `mixed`.
4. **Zeros:** `zero_policy: none`. Hyperendemic: no absence row of any kind; the 2015–2017 phantom zeros are held out.
5. **Agent 3 repurposed** (brief via `country_notes` and the orchestrator's pilot section): map the surveillance system year by year — streams, case definitions, sentinel site lists, sampling fractions, test methods. Writes no rows; its log is the evidence base for Agent 7's count-basis entries.
6. **Sentinel positivity sidecar** `./data/BGD/sentinel_positivity_ai.csv`: `Location, TL, TR, site, tested, positive, test_method, serogroup, sampling, source_index, source, processing_notes`. Weekly or monthly tested/positive by site. The builder does not read it. The validator checks columns, integers, positive ≤ tested, dates and `source_index`.
7. **Locations.** National `SEAR::BGD`; divisions `SEAR::BGD::<Division>`; camps `SEAR::BGD::Chattogram::Cox's Bazar` (JHU's `Chittagong Division::Cox's Bazar` and `Chattogram::BD-11` mean the same place); sentinel counts at the site's own location (icddr,b Dhaka hospital → `SEAR::BGD::Dhaka::Dhaka`; Matlab → `SEAR::BGD::Chattogram::Chandpur`). A sentinel or camp figure stored at `SEAR::BGD` gets a `coverage` entry from Agent 7.

## Work items (one commit each; gates after each)

**A. Scope.** Overlay entry; `py/xref_harvest.py` BGD pattern (`\bBangladesh\b|বাংলাদেশ|Cox's Bazar`) out of the `XOT` block-list in the same commit (its import-time `SCOPE` assertion fails otherwise); `MMR` added to `OUT_OF_SCOPE_NEIGHBORS` in `py/build_country_profiles.py`; `py/tests/test_scope.py` updated (two pilots; a different out-of-scope example); "currently Nepal" wording in `CLAUDE.md`, `py/scope.py`, `run_all_countries.sh` comments, rule 7 of the six agent files and `workflow-orchestrator.md` (plus the repurposed-Agent-3 brief).

**B. Builder.** Optional `coverage` column; whole-row hold-out; `strict_basis`. Tests: a `subset` row with both fields is held out of both series; a strict AI row without an entry is held out; NPL fixture unchanged.

**C. Validator.** `strict_basis` → WARN `pilot_count_basis_missing` on every national AI row with a count and no `AI:<Index>` entry; `pilot_estimate_mention`; sentinel sidecar checks. All behind settings, so Nepal's findings do not change. Tests.

**D. Baseline and count-basis table.** `python py/convert_jhu_to_workflow.py --iso BGD` (drops 12 age/sex rows; logs skipped rows including 12641's O1/O139 isolate columns and 21560's culture-only rows to `data/BGD/jhu_skipped_rows.csv`); `python py/convert_who_to_workflow.py --only BGD`; `py/protect_baselines.py`. Table:

| source_key | years | field | basis | coverage | status | evidence |
|---|---|---|---|---|---|---|
| JHU:429 | 1950–1970 | sCh | unknown | national | provisional | reported for Pakistan; attribution unverified |
| JHU:429 | 1971–2000 | sCh | unknown | national | provisional | notifications; type per year only on a quoted WER definition |
| JHU:429 | 2015–2017 | sCh | unknown | national | provisional | phantom zeros |
| JHU:429 | 2018–2022 | sCh, cCh | unknown | — | provisional | probably sentinel lab positives; Agent 1 priority 1 |
| JHU:429 | 2023–2024 | sCh | age | sample | verified (2023) / inferred (2024) | WER 99(36) Table 3 |
| JHU:429 | 2023–2024 | cCh | confirmed | sample | verified / inferred | culture positives among sentinel enrolees |
| WHO:dashboard | 2023–2026 | sCh | suspected | subset | verified | update #33 "Bangladesh (Cox's Bazar)" |
| JHU:21505 | 2023–2024 | sCh | suspected | subset | inferred | incidence per 100k implies ~0.9 M |
| JHU:21363 | 2014–2018 | sCh | age | sample | inferred | Khan 2020: diarrhoea patients enrolled |
| JHU:21363 | 2014–2018 | cCh | confirmed | sample | inferred | *V. cholerae* O1 among enrolees |

**E. Reference data and agent guidance.** Profile in `py/country_profiles_data_pilot.py` (8 divisions with legacy names; cities; IND, MMR; bn, en; terms; domains; bimodal season; flood years incl. 2022, 2024); `regional_sources` (WHO SEARO / Bangladesh, WER annual reports incl. 2025, WHO Cox's Bazar EWARS bulletins on cdn.who.int, icddr,b Health and Science Bulletin, JHPN, IEDCR outbreak reports, National Cholera Control Plan 2019–2030, IFRC, ReliefWeb); `archive_hints` (Cholera Research Laboratory Dacca reports, dspace.icddrb.org, BMRC Bulletin, Daily Star / Prothom Alo, Wayback for old.dghs.gov.bd and iedcr.gov.bd); `country_notes` with the stream table, location rules, the sidecar, no AWD/diarrhoea/A00/estimates as cholera, no scaling of samples, no zero rows, the Agent 3 brief, and priorities: (1) what JHU 429 2018–2022 count; (2) WER case definitions year by year (1971–2000, 2023–2025); (3) any national suspected count 2001–2022 (DGHS Health Bulletins, IEDCR); (4) sentinel positivity series, Matlab first; (5) Cox's Bazar weekly 2017–2026 at sub-national level. Domains in `reference/priority_sources_pilot.txt`. Rebuild and verify profiles.

**F. First build and review gate.** Validator 0 errors; builder `--iso BGD --out-dir <scratchpad>` (expected: national suspected and confirmed series empty; every national row in `builder_holdout.csv` with a reason); `pytest`; both regression gates; `update_dashboard.sh` without `--publish` passes `py/validate_dashboard.py` (BGD in the pilot section), with generated files reverted afterwards if they only carry dates. **Stop for the user's review.**

**G. Pilot run (after review).** User decisions first: merge the MOSAIC-pkg guard? Check `claude auth status`. `bash run_all_countries.sh --only BGD --unattended`. Downloads in chunks under ~100 minutes. Agent 7 resolves every national source-year and writes `data/BGD/search_report.txt`. Publish only on the user's instruction, from the supervising session.

## Acceptance (for the run)

- Validator 0 errors and 0 `pilot_count_basis_missing` WARNs; every national source-year with a non-zero value resolves, with quoted evidence.
- No camp, sentinel, diarrhoea, A00 or modelled figure in `cholera_weekly_BGD.csv` or the confirmed series.
- **Tripwires (Agent 7):** any year typed national suspected where the source shows an under-5 share above 30 % or tested ÷ cases above 50 % is retyped; any national suspected year below 1 % of the ~110,000 burden estimate is flagged as incomplete.
- `search_report.txt` has a 1970–2025 table: stream(s) present, what each counts, quoted source text.
- The 40 countries and Nepal unchanged.

## Risks

| Risk | Mitigation |
|---|---|
| Camp or sentinel counts read as national | `coverage` hold-out (whole row); `strict_basis`; country rules; Agent 7 |
| Diarrhoea totals entered as cholera | country rules; `age` basis; `strict_basis` keeps untyped AI rows out |
| Burden estimates entered as observations | country rule; `pilot_estimate_mention` |
| The icddr,b literature eats the query budget | priorities put national typing first; sentinel data goes to the sidecar |
| Changes alter Nepal or the 40 | new settings default off; two regression gates after every item |
| MOSAIC-pkg ingests BGD | set-up builds to scratch; guard merge is a pre-run decision |
| Auth expiry / 2 h shell limit | checked before launch; chunked downloads; resume briefing |

## Follow-ups (not in this pilot)

- A relocation field in the count-basis table so camp data stored at `SEAR::BGD` feeds a Cox's Bazar sub-national series.
- A sub-national builder output for Cox's Bazar and Matlab.
- Data-driven tripwires (needs age and tested columns in the data schema).

## Changes from the first draft

- **WER 2023–2025 are sentinel diarrhoea enrolment, not national suspected cholera** (WER 99(36) Table 3). National suspected series now expected empty; 1971–2000 notifications `unknown` until a WER definition is quoted.
- **`partial` basis replaced by a `coverage` column** that holds the whole row; the first draft leaked JHU 21363's 1,604 sentinel positives into the national confirmed series and could not express "sCh, cCh" in one entry.
- **`strict_basis`**: untyped AI rows no longer default to suspected/confirmed for Bangladesh.
- **New WARNs behind per-country settings**, not "pilot countries", because on Nepal they would have fired 14 (estimates) and 82 (sentinel wording) times; the sentinel-wording WARN was dropped in favour of `strict_basis`.
- **Sentinel positivity sidecar** added; Matlab is BD-09 (Chandpur) and dates from the 1960s, not 1996.
- **Cox's Bazar**: one canonical location, JHU's two spellings named, 21127 flagged as AWD.
- **Missing streams added**: clinical A00 counts, flood surges 2022/2024, O139 reporting 1992–93, the 2025 WER, the National Cholera Control Plan, Cox's Bazar EWARS bulletins.
- **Pipeline fixes**: `--include` does not exist in `analyze_effective_gaps.py`; WHO converter needs `--only BGD`; MMR neighbour; xref assertion ordering; `test_scope.py`; Nepal snapshot rebuilds outputs rather than hashing tracked files; set-up builds to scratch because of the MOSAIC-pkg exposure.
