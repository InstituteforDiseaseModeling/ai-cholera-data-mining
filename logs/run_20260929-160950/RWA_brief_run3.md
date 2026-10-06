# RWA — Run Window 3 shared brief (every agent reads this FIRST)

Written by the workflow orchestrator, 2026-09-29 16:15 local.
Working directory: `/Users/johngiles/MOSAIC/ai-cholera-data-mining` (all paths below are relative to it).

## 1. Situation

- Country: **Rwanda (RWA)**. This is **run window 3**, an unattended re-run launched by
  `bash run_all_countries.sh --unattended --publish-progress --parallel 4` (pid 76250).
  AGO, COG and MRT are running **in parallel in other processes** — never touch their files.
- Rwanda has already had two heavy run windows (2026-09-28). The dataset is mature:
  **321 live rows (max Index 335), 197 metadata sources (max Index 197), 13 retracted rows,
  6 presence rows, validator ERROR 0 / WARN 0**. Any row you add gets Index > 335; any source > 197.
- Effective coverage at start: **88.8% (605 of 681 months), 76 months missing, 19 gap periods**,
  months_ai_only 590, latest observation 2026-09-06. Baseline-only (JHU+WHO) coverage is 1.9%.
- Hard kill of this whole country process: ~00:09 local on 2026-09-30. Your prompt gives you a
  personal deadline. **Respect it: check `date` before starting each batch.** A batch you cannot
  finish before your deadline must not be started (partial batches are forbidden by the protocol).

## 2. The 19 remaining gaps (reference/effective_surveillance_gaps_detailed.csv, RWA rows, read-only)

| # | gap_start | gap_end | days | era | prior-run classification (Agents 6/7, 2026-09-28) |
|---|---|---|---|---|---|
| G1 | 1990-01-01 | 1990-12-31 | 365 | historical | Surveillance gap: absent from WER 1991 Table; RPF war from 1 Oct 1990; regional cholera on 3 borders. No row. |
| G2 | 2002-01-01 | 2002-12-31 | 365 | modern | Surveillance gap for cholera (meningitis was notified via DON); regional epidemic on every border. No row. |
| G3a | 2010-01-01 | 2010-04-30 | 120 | modern | Presence with unknown counts (MoH FY2009-10, metadata 165, six districts; timing unresolved). |
| G3b | 2010-06-01 | 2011-10-31 | 518 | modern | No recognised outbreak, surveillance operating (MoH AR FY2010-11 = metadata 168; FY2011-12 = metadata 166, both mined). Omission-based only, NOT zero-written. No weekly records found. |
| G3c | 2011-12-01 | 2011-12-31 | 31 | modern | As G3b. |
| G4 | 2013-01-01 | 2013-02-28 | 59 | modern | RBC 2013 weekly bulletins/Annex-1 not recovered (2013 editions overwritten on rbc.gov.rw). |
| G5 | 2014-05-01 | 2015-01-31 | 276 | modern | RBC weekly bulletins not recovered (RBC inventory says 12-month outbreak-free interval). |
| G6 | 2015-03, 2015-05..06, 2015-09..10, 2015-12 | | 31/61/61/31 | modern | RBC bulletins not recovered. |
| G7 | 2017-02, 2017-06..07, 2017-10..12 | | 28/61/92 | modern | RBC bulletins not recovered/read. Ishywa (Rusizi) 49 cases Aug-Sep 2017 sits just before Oct-Dec. |
| G8 | 2019-02, 2019-06..07, 2019-11..12 | | 28/61/61 | modern | RBC 2019 weekly bulletins archived on Wayback; wk7, 8, 13, 23-31, 44-48 never downloaded (Wayback refused connections). |
| G9 | 2020-03-01 | 2020-03-31 | 31 | modern | RBC ESR bulletin not recovered (COVID lockdown from 21 Mar 2020; routine ESR reporting continued). |
| G10 | 2026-09-01 | 2026-09-29 | 29 | recent | **Reporting lag in a LIVE outbreak**: national 24-88 sCh/week through the week 2026-08-31..09-06 (last row, Index 59, WHO dashboard source 14 = 24). Must stay empty rather than zero unless a source gives numbers. |

A month counts as covered when >50% of its days fall inside an informative observation
(a count row or a labelled zero row). Presence rows do not count.

## 3. Coverage probe (read-only — use this, never regenerate the shared files)

```bash
python -c "import sys,json;sys.path.insert(0,'py');import analyze_effective_gaps as g;from datetime import date;m=json.load(open('reference/country_mapping.json'))['countries'];d,a,c,r=g.analyse('RWA',m['RWA']['name'],['JHU','WHO','AI'],date.today(),7);print(c);[print(x['gap_start'],x['gap_end'],x['days'],x['era']) for x in d]"
```

## 4. HARD RULES for this run (in addition to CLAUDE.md and templates/template_search_protocol.txt)

1. **Do NOT run** `python py/analyze_effective_gaps.py` (without the in-memory form above),
   `python py/analyze_baseline_gaps_optimized.py`, `bash update_dashboard.sh`,
   `python py/update_dashboard_data.py`, `python py/build_weekly_timeseries.py`, or any `git` command
   that writes (add/commit/push/checkout). These rebuild files shared with the three sibling countries
   or collide on `.git/index.lock`. The runner does all of this after RWA exits.
2. **Never hand-edit** `data/RWA/cholera_data_ai.csv` or `data/RWA/metadata_ai.csv`.
   New rows: `python py/add_observation.py {register-source|add|add-zero|add-presence} RWA ...`.
   Changes to existing rows/sources: `python py/revise_observation.py RWA --index N ... --reason "..." --agent K`
   (`--append-note`, `--confidence`, `--sch/--cch/--deaths/--tl/--tr/--location`, `--set-evidence`,
   `--delete` = retract with tombstone; `--meta-index N --set-description/--set-status` for metadata).
3. **Write a FRESH canonical log** `data/RWA/search_log_agent_{N}.txt` (create/overwrite it with `>`
   before your first query, then append per batch). The Sep-28 logs were archived to
   `data/RWA/search_log_agent_{N}_legacy_*.txt` — read them for what was already searched, never
   append to them. Agent 1's log already holds a 4-line INITIALIZATION header: append below it.
4. **Minimum 3 full batches of 20 queries** (Agent 7 excepted). Then stop at 3 consecutive batches
   <5% yield or 12 batches, or at your deadline. Yield = queries that produced >=1 NEW committed row /
   20, as a percent 0-100. A document fetch (WebFetch of a known URL / Wayback capture) counts as a
   query slot when it is how you pursue a lead — log each one as a numbered query.
5. **A row needs a number** (sCh/cCh/deaths) or a labelled zero (`add-zero` with
   `--evidence Documented_Absence|Inferred_Absence` and `--surveillance`). Presence-without-count goes
   to `add-presence`. `Surveillance_Gap` is never a zero row.
6. **Double counting:** any sub-national row in a period that has a national row (or vice versa) must
   carry, via `--note`, one of the exact phrases
   `National total - includes provinces not individually listed` or
   `Provincial subset - do not sum with national row`.
7. **Location convention** already in the file: `AFR::RWA`, `AFR::RWA::{Kigali|Eastern|Northern|Southern|Western}`,
   `AFR::RWA::{Province}::{District}` using the post-2006 five provinces and 30 districts (e.g.
   `AFR::RWA::Western::Rusizi`, `AFR::RWA::Western::Rutsiro`). Pre-2006 prefectures map to their modern
   province: `AFR::RWA::Western::Gisenyi`, `AFR::RWA::Western::Cyangugu`, etc. Keep this convention.
8. Before you finish: `python py/validate_quality.py RWA` must exit 0, then record state:
   ```bash
   python -c "import sys;sys.path.insert(0,'py');from workflow_state import write_agent_state;\
   write_agent_state('RWA',agent_num=N,batches_completed=B,batch_yields=[...percent values...],\
   rows_added=R,sources_discovered=S,stopping_reason='...',gaps_filled=[...],\
   gaps_validated_absent=[...],gaps_remaining=[...])"
   ```
   `rows_added`/`sources_discovered` = rows/sources YOU created in this window (count by Index range).
   Do not overwrite other agents' entries (the function replaces only your own agent_num).

## 5. Method warnings learned the hard way (2026-09-28)

- **RBC 2017-2022 bulletin PDFs carry hidden, unrendered template text** such as
  `Cholera: 1 suspected case` and `814 cases were reported`. A text-layer extraction therefore fabricates
  a cholera case in every bulletin. Extract ONLY from what the rendered page shows (read the PDF as
  images / the rendered page, or cross-check the disease table visually). Row 291 (2022 wk23) was
  verified real on the rendered page; rows 307 and 330 (zeros) verified the same way.
- RBC bulletin URL patterns (for direct fetch or Wayback):
  - 2017+: `https://rbc.gov.rw/fileadmin/user_upload/bulletin/{YYYY}/The%20bulletin%20week%20{WW}%20from%20...pdf`
    (exact filenames vary: "The bulletin Week 17 from 22nd to 28th April, 2019.pdf"; 2026 files use
    underscores: `.../bulletin/2026/The_bulletin_week_35_from_24th_to_30th_August_2026.pdf`)
  - 2012-2016: `https://rbc.gov.rw/IMG/pdf/weekly_epidemiological_bulletin_week_{WW}.pdf`,
    `.../IMG/pdf/weekly_epidemiological_updates_week_{WW}.pdf`, `.../IMG/pdf/the_bulletin_week_30_from_25th_to_31_july_2016.pdf`
    (files were overwritten year-on-year, so a Wayback capture's timestamp decides which year you have)
  - 2005-2008 MoH: `http://www.moh.gov.rw/docs/pdf/epydemiology_newsletter/bulletin_epidemiologique_n{NN}.pdf`
  - Wayback raw-file form: `https://web.archive.org/web/{timestamp}id_/{original_url}`; list captures with
    `https://web.archive.org/cdx/search/cdx?url=rbc.gov.rw/fileadmin/user_upload/bulletin/2019/*&output=json&fl=timestamp,original,statuscode&filter=statuscode:200&collapse=urlkey`
  - Wayback rate-limits (HTTP 429 / connection refused) after bursts: pace requests, retry with backoff,
    and log failures honestly rather than treating them as absence.
- The WHO Global Cholera and AWD Dashboard weekly country dataset (metadata 14,
  `who.maps.arcgis.com` item 6d435a537d534bac95b072fd6d999355) supplied national weekly rows 42-59
  through 2026-08-31..09-06. A refreshed download may now carry weeks 37-39 of 2026.
- WHO baseline file `data/RWA/cholera_data_who.csv` is read-only (JHU file does not exist for RWA).
  Do not duplicate baseline weeks; the weekly builder prefers WHO > JHU > AI for the same week.
- Existing conflict adjudications (Agent 5, 2026-09-28): 2008 rows 38/302/303 conflict recorded verbatim;
  2012 row 40 (WHO GHO 9) vs RBC inventory 84 → row 40 conf 0.5; rows 182/70 restate the WHO 2025 weekly
  series (sum 312); rows 2 and 236 are the same 2005-06 Kigali outbreak at two levels; row 162 is
  single-source. Metadata 6 Date_Range says 2018-2024 but the source is dated Aug 2015.

## 6. What the previous windows already exhausted (do not re-spend budget here without a new angle)

WHO GHO; WER annual cholera tables 1970-2025 via IRIS (RWA absent in the 1990 and 2002 tables); the
299-item DON archive; both WHO dashboard datasets; OWID; HDX; RBC/MoH bulletins 2005-2008, 2012-2014,
2016-2023, 2025-2026 (wk35); MoH annual reports FY2009-10, FY2010-11, FY2011-12; PubMed; ReliefWeb; ProMED;
ECDC; Africa CDC; GTFCC; IFRC/MSF/UNICEF; Kinyarwanda/French media (New Times, IGIHE, Kigali Today,
Imvaho Nshya); Gallica (Malatre 1989 Gisenyi 1987); WHO EHA Great Lakes SitReps 1997-2000; Internet
Archive CDX for bulletin/2019, 2020, 2021, 2022.
Full detail: `data/RWA/workflow_state_pre_opus55_2026-09-29.json` and the `_legacy_` logs.

## 7. Current workflow_state

`data/RWA/workflow_state.json` holds this window's run metadata (`run_window_3`) and the entries of the
agents that have already finished in this window. Read it before you start.
