# RWA — Run Window 4 shared brief (every agent reads this FIRST)

Written by the workflow orchestrator, 2026-09-29 19:15 local (PDT).
Working directory: `/Users/johngiles/MOSAIC/ai-cholera-data-mining` (all paths below are relative to it).

## 0. THERE IS NO TIME LIMIT

**You have no deadline, no wall-clock budget, no "return by HH:MM" and no time box.** Do not invent
one, do not estimate "how long a batch takes" in order to stop, and do not stop or trim work because
of elapsed time. Run window 3 (16:09-19:07 today) failed exactly this way: the orchestrator split an
assumed time allowance across agents, and Agents 1-3 stopped at 5 batches while still yielding
25-80% per batch. Those stops are void; that is why you are being redeployed.

**The ONLY stopping rule (Agents 1-6):** at least 3 batches of 20 queries; then keep going until
**3 consecutive batches are below 5% yield** (5% itself is NOT below 5%) **or 12 batches in total**
have been run (batches from earlier sessions of this cycle count toward the 12 and toward the
consecutive run). Yield = queries that produced >=1 NEW committed row in `data/RWA/cholera_data_ai.csv`
(count rows OR labelled zero rows) / 20, in percent (0-100). Never above 100%. Presence rows, revisions
and retractions do not count as yield (log them anyway). Agent 7 has no batch limit.

The runner's per-country process limit (48 h) is a hang detector, not a budget. Ignore it.

## 1. Situation at the start of run window 4 (19:09 local)

- Country: **Rwanda (RWA)**. Runner: `bash run_all_countries.sh --unattended --publish-progress --parallel 4`
  (pid 27566, run dir `logs/run_20260929-190752/`). AGO, COG and MRT run **in parallel in other
  processes** — never touch their files, and never rebuild shared files (section 4).
- Dataset: **429 live rows (max Index 444), 281 metadata sources (max Index 281), 14 retracted rows,
  7 presence rows**; `python py/validate_quality.py RWA` → exit 0, ERROR 0, WARN 0, INFO 142.
  New rows get Index > 444, new sources Index > 281 (the tools allocate them; just never reuse).
- Effective coverage (runner-refreshed `reference/effective_surveillance_gaps_*.csv`, 19:08):
  **615 of 681 months = 90.3%**, 66 months missing, **14 gap periods**, months_ai_only 600,
  months_with_positive_cases 481, latest observation **2026-09-13** (16 days stale).
  Baseline-only (JHU+WHO) coverage is 1.9% (13 months); RWA has no JHU file.
- The previous window's agents 1-3 appended complete per-batch logs to `data/RWA/search_log_agent_{1,2,3}.txt`,
  Agent 4 to `data/RWA/search_log_agent_4.txt` (10 batches, then the session ended — no summary, no state entry).
  Agents 5-7 have NOT run in this cycle (their canonical logs do not exist yet; Sep-28 work is in
  `data/RWA/search_log_agent_{5,6,7}_legacy_2026-09-28.txt`).

## 2. The 14 remaining gaps (reference/effective_surveillance_gaps_detailed.csv, RWA rows, read-only)

| # | gap_start | gap_end | days | era | classification so far (run windows 1-3) |
|---|---|---|---|---|---|
| G1 | 1990-01-01 | 1990-12-31 | 365 | historical | Surveillance gap: absent from WER 1991 table AND its addendum (WER 66(20):146); RPF war from 1 Oct 1990; MSF CRASH 1982-93 history mentions no cholera (context only). Regional epidemic (Zaire 468). No row. |
| G2 | 2002-01-01 | 2002-12-31 | 365 | modern | Omission only: WER 2003 'Cholera, 2002' omits Rwanda; IRIN 2002 chronology logs meningitis (636/83) but no cholera; USAID/OCHA relay an UNCONFIRMED media line "300 suspected cases of cholera ... Ruhengeri" (Jan 2002 Nyiragongo influx) — not committable alone. No row. |
| G3a | 2010-01-01 | 2010-04-30 | 120 | modern | Presence with unknown counts (MoH FY2009-10 = metadata 165, six districts, timing unresolved). Row 159 (Nkombo 48, AFENET) ends 2010-06-09. |
| G3b | 2010-06-01 | 2011-10-31 | 518 | modern | Outbreak-table omission (MoH FY2010-11 = metadata 168; FY2011-12 = 166 lists 24/10/2011 Nyamasheke 14, 13/2/2012 Rubavu 13). Surveillance operating; no positive absence statement → no zero written. |
| G3c | 2011-12-01 | 2011-12-31 | 31 | modern | As G3b. |
| G4 | 2013-01-01 | 2013-02-28 | 59 | modern | Source loss: RBC 2013 wk1-8 editions not on server or Wayback (1,458 filenames tested). WHO AFRO 3 Jun 2013 regional table omits Rwanda (= non-reporting, not a zero). |
| G5 | 2014-05-01 | 2015-01-31 | 276 | modern | Source loss: no 2014 wk17-52 edition online/Wayback; RBC inventory implies a 12-month outbreak-free interval (omission only). |
| G6 | 2015-03 / 2015-05..06 / 2015-09..10 / 2015-12 | | 31/61/61/31 | modern | Source loss; 2015 = regional epidemic (Tanzania/Burundi refugee crisis); UNHCR/IFRC/MIDIMAR refugee reporting mentions cholera only as a risk. |
| G7 | 2019-06-01 | 2019-06-30 | 30 | modern | RBC wk24 file is non-PDF; wk25/26 truncated on the live site and in every Wayback capture. |
| G8 | 2020-03-01 | 2020-03-31 | 31 | modern | RBC wk9-13 and the March 2020 monthly never captured; 404 live. |
| G9 | 2026-09-01 | 2026-09-29 | 29 | recent | **LIVE OUTBREAK reporting lag.** Last rows: RBC wk37 (7-13 Sep 2026) district rows 336-341 (Rusizi/Rutsiro/Rubavu). RBC wk38 (14-20 Sep) / wk39 bulletins and a WHO dashboard refresh were not yet posted at 17:29. Must stay empty unless a source gives numbers — never zero-fill. |

A month counts as covered when >50% of its days fall inside an informative observation
(a count row or a labelled zero row). Presence rows do not count.

## 3. Coverage probe (read-only, writes nothing — use this, never regenerate the shared files)

```bash
python -c "import sys,json;sys.path.insert(0,'py');import analyze_effective_gaps as g;from datetime import date;m=json.load(open('reference/country_mapping.json'))['countries'];d,a,c,r=g.analyse('RWA',m['RWA']['name'],['JHU','WHO','AI'],date.today(),7);print(c);[print(x['gap_start'],x['gap_end'],x['days'],x['era']) for x in d]"
```

## 4. HARD RULES (in addition to CLAUDE.md and templates/template_search_protocol.txt)

1. **Do NOT run** `python py/analyze_effective_gaps.py` (use the in-memory probe above),
   `python py/analyze_baseline_gaps_optimized.py`, `bash update_dashboard.sh`,
   `python py/update_dashboard_data.py`, `python py/build_weekly_timeseries.py`, `python py/generate_coverage_heatmap.py`,
   or any `git` command that writes (add/commit/push/checkout/stash). They rebuild files shared with the
   three sibling countries or collide on `.git/index.lock`. The runner does all of this after RWA exits.
2. **Never hand-edit** `data/RWA/cholera_data_ai.csv` or `data/RWA/metadata_ai.csv`.
   New rows: `python py/add_observation.py {register-source|add|add-zero|add-presence} RWA ...`.
   Changes to existing rows/sources: `python py/revise_observation.py RWA --index N ... --reason "..." --agent K`
   (`--append-note`, `--confidence`, `--sch/--cch/--deaths/--tl/--tr/--location`, `--set-evidence`,
   `--delete` = retract with tombstone; `--meta-index N --set-description/--set-status` for metadata).
   **Always pass `--reporting-date`** (zero rows: TR + 1 day) — blank reporting dates raise WARNs.
3. **Logs.** Continuing agents (1-4): APPEND to your canonical log `data/RWA/search_log_agent_{N}.txt`
   under a header `=== RUN WINDOW 4 CONTINUATION (<start time>) ===` — never truncate it; the earlier
   batches are part of your yield record. New agents (5-7): create `data/RWA/search_log_agent_{N}.txt`
   fresh before your first query, then append per batch. Never write to any `_legacy_` log.
   Log every batch as soon as it ends in the template shape (=== BATCH n | PHASE p | RWA ===, numbered
   queries with category tags, Sources found / Registered, Rows added + Indices, Successful queries k/20,
   Yield, Consecutive sub-5% batches, Decision). A Wayback capture / WebFetch of a known URL counts as a
   query slot when it is how you pursue a lead — number it.
4. **A row needs a number** (sCh/cCh/deaths) or a labelled zero (`add-zero` with
   `--evidence Documented_Absence|Inferred_Absence` and `--surveillance operational|partial|disrupted|unknown`).
   Presence-without-count → `add-presence`. `Surveillance_Gap` is never a zero row.
5. **Double counting:** any sub-national row in a period that has a national row (or vice versa) must
   carry, via `--note`, one of the exact phrases
   `National total - includes provinces not individually listed` or
   `Provincial subset - do not sum with national row`.
6. **Location convention** already in the file: `AFR::RWA`, `AFR::RWA::{Kigali|Eastern|Northern|Southern|Western}`,
   `AFR::RWA::{Province}::{District}` with the post-2006 five provinces / 30 districts (e.g. `AFR::RWA::Western::Rusizi`).
   Pre-2006 prefectures map to their modern province: `AFR::RWA::Western::Gisenyi`, `AFR::RWA::Western::Cyangugu`, etc.
7. **Checkpoint after EVERY batch** (so an unexpected session end leaves a resumable record): append the
   batch block to your log, then write your state entry with CUMULATIVE numbers for this cycle and
   `stopping_reason='IN PROGRESS - batch B complete, yield rule not yet met'`. When you stop, write the
   final entry with the real reason ("3 consecutive batches below 5% (batches x,y,z)" or "12 batches").
   ```bash
   python -c "import sys;sys.path.insert(0,'py');from workflow_state import write_agent_state;\
   write_agent_state('RWA',agent_num=N,batches_completed=B,batch_yields=[...percent values, ALL batches this cycle...],\
   rows_added=R,sources_discovered=S,stopping_reason='...',gaps_filled=[...],\
   gaps_validated_absent=[...],gaps_remaining=[...])"
   ```
   `rows_added`/`sources_discovered` = rows/sources YOUR agent number created in THIS CYCLE (window 3 +
   window 4, by Index range) — continuing agents keep their window-3 numbers and lists and add to them.
   The function replaces only your own agent_num entry and preserves all other keys.
8. `python py/validate_quality.py RWA` must exit 0 (ERROR 0; fix any WARN you caused) before you finish.

## 5. Method warnings learned the hard way

- **RBC 2017-2022 bulletin PDFs carry hidden, unrendered template text** such as `Cholera: 1 suspected case`
  and `814 cases were reported`. Text-layer extraction fabricates a case in every bulletin. Extract ONLY
  from what the rendered page shows (render pages to images and read them, or visually cross-check the
  disease table). Row 291 (2022 wk23) verified real on the rendered page; rows 307 and 330 (zeros) likewise.
  2026 "actions" columns are copied template text; the 2026 wk37 EBS box repeats wk36 verbatim.
- **Suspect-only weeks (rule applied by Agent 3, keep it consistent):** (a) lab-/culture-negative per the source
  = discarded (row 358 retracted; zeros 413/435/437); (b) suspects with no lab result = sCh; (c) where an
  affirmative national zero-report to WHO covers the year (2018 row 63, 2024 row 10) the zero is kept,
  suspects noted, weight reduced where rendered-verified.
- RBC bulletin URL patterns (direct or Wayback):
  - 2017+: `https://rbc.gov.rw/fileadmin/user_upload/bulletin/{YYYY}/The%20bulletin%20week%20{WW}%20from%20...pdf`
    (names vary; 2026 files alternate underscore/space forms and contain typos such as "31sf"; the ROOT folder
    `/fileadmin/user_upload/bulletin/` also holds 2017 wk23-30 and 2018 wk1 files)
  - index page: `https://rbc.gov.rw/publications/health-surveillance-emergency-preparedness-reponse`
  - 2012-2016: `https://rbc.gov.rw/IMG/pdf/weekly_epidemiological_bulletin_week_{WW}.pdf`,
    `.../IMG/pdf/weekly_epidemiological_updates_week_{WW}.pdf` (overwritten year-on-year: the Wayback
    capture timestamp decides which year you have)
  - 2005-2008 MoH: `http://www.moh.gov.rw/docs/pdf/epydemiology_newsletter/bulletin_epidemiologique_n{NN}.pdf`
  - Wayback raw file: `https://web.archive.org/web/{timestamp}id_/{original_url}`; CDX list:
    `https://web.archive.org/cdx/search/cdx?url=rbc.gov.rw/fileadmin/user_upload/bulletin/2019/*&output=json&fl=timestamp,original,statuscode&filter=statuscode:200&collapse=urlkey`
  - Wayback rate-limits (HTTP 429 / connection refused) after bursts: pace, retry with backoff, and log
    failures honestly — a failed fetch is not evidence of absence.
- WHO Global Cholera/AWD Dashboard weekly country dataset (metadata 14, `who.maps.arcgis.com` item
  6d435a537d534bac95b072fd6d999355) last modified 2026-09-28 08:15 UTC at 17:29 today; its epiwk labels
  run one week behind date_wk (date_wk 2026-08-31 = epiwk 35). The WHO baseline `data/RWA/cholera_data_who.csv`
  (59 rows, 2025-03-17..2026-05-03) is read-only; do not duplicate baseline weeks (builder prefers WHO > AI per week).
- IRIS (iris.who.int) is blocked from this host; use Wayback/ReliefWeb/PMC mirrors. Europe PMC intermittently 503.

## 6. Open leads and conflicts handed over by window 3 (see each agent's log HANDOVER block)

- Recency: RBC wk38/wk39 2026 bulletins; WHO dataset refresh (weeks 37-39 2026). Gap G9.
- 2009: IRIN/TNH node/246932 = 29-30 Sep 2009 (ProMED 20090930.3411): "At least 50 cases ... northwestern
  region ... no deaths ... free of the disease for a decade" — WHO GHO 2009 = 67 equals the Rusizi outbreak
  alone; the NW cluster may be additional (not committed: no admin unit, no start date).
- 2016: New Times, Kanama sector (Rubavu) Aug 2016 "Over 60 people were isolated" — approximate, body unavailable.
- 2002: USAID/OCHA "300 suspected cases ... Ruhengeri ... not confirmed" (find the primary or corroboration).
- Conflicts for Agent 5: row 277 (Rusizi Aug-Sep 2017 = 49, news) vs RBC weekly Rusizi 100 (rows 414-421);
  row 405 (2017 wk46) table 5 vs narrative 4; row 167 (Nyamasheke 2014 inventory, assumed window to 30 Apr) vs
  documented zero wk16 (row 433); 2025 wk22 WHO 15 vs RBC 7; row 40 (WHO GHO 2012 = 9 = AFENET Nkamira) vs RBC
  inventory 84; RBC 2026 wk36 EBS national 24 vs district line-list 11; WHO 2021 = 74 / 2022 = 24 not visible
  in the RBC weekly series (no 2021/2022 weekly zeros until resolved); 2023 Kibogora box (3/6/9) vs narrative 5;
  2023 wk10 "8 confirmed" vs wk9 split; row 294 (2019 wk50) facility only from text layer.
- Geography ready for partition (Agent 2): 2017 national weekly rows 395-396, 400-421 carry facility names in
  their notes (Nkombo/Nkanka/Rusizi HC/Gihundwe = Rusizi; Kigufi HC/Gisenyi/Nyundo/Gacuba II = Rubavu;
  Kibogora = Nyamasheke; Murunda/Mushubati = Rutsiro; Kijote TC/Bigogwe = Nyabihu). 2012 wk46/47/49 rows
  93/71/94 and 2013 wk35-45 rows 95-100 name Kinunu HC (Rutsiro) / Nkombo, Bugarama Islamic HC (Rusizi), but
  RBC-inventory rows 163-166 use assumed 28-day windows that may already include them — decide the partition
  first. 2023 wk32/33 national weekly (1, 2; Rubavu RDT) could split Rubavu segment row 140 by week.

## 7. What earlier windows already exhausted (do not re-spend queries here without a NEW angle)

WHO GHO; WER annual cholera tables 1970-2025 (RWA absent in the 1990 and 2002 tables); the 299-item DON archive;
both WHO dashboard datasets; OWID; HDX; RBC/MoH bulletins 2005-2008, 2012-2014, 2016-2023, 2025-2026 (to wk37);
RBC 2017 wk23-52 and 2019 ESR weekly reports; MoH annual reports FY2009-10/2010-11/2011-12; AFENET annual reports
2007/2010/2012/2013/2015; PubMed/Europe PMC; ReliefWeb; ProMED; ECDC; Africa CDC; GTFCC; IFRC/MSF/UNICEF/UNHCR;
MSF CRASH and Speaking Out volumes; UPenn IRIN 1997-99; WHO EHA Great Lakes SitReps 1997-2000 (5361-5399);
Kinyarwanda/French media (New Times, IGIHE, Kigali Today, Imvaho Nshya, Kinyarwanda month-name queries);
Gallica (Malatre 1989 Gisenyi 1987; Remy & Dejours 1988); Internet Archive CDX for bulletin/2019-2022.
Full detail: `data/RWA/workflow_state_pre_opus55_2026-09-29.json`, the canonical logs, and the `_legacy_` logs.

## 8. Current workflow_state

`data/RWA/workflow_state.json` holds the per-agent entries for this cycle plus `run_window_3` and
`run_window_4` metadata. **`run_window_3.orchestrator_decisions` item 4 ("Time budget ...") is VOID** —
see `run_window_4.orchestrator_decisions`. Read the file before you start.

## 9. ORCHESTRATOR FINDING (21:40): national weekly rows can silently displace annual totals

`py/build_weekly_timeseries.py` (read-only for you; do not run it) builds the national series from
`AFR::RWA` rows only. Within one source layer (all our rows are layer AI), a non-weekly national row
with a count (e.g. an annual total) is **skipped entirely when >= 50% of its ISO weeks
(`COVERAGE_THRESHOLD = 0.50`) already carry a weekly national row with a count — explicit weekly zeros
included**. Weeks left without any row then become `assumed_zero`. So a year whose weekly national
series is incomplete but covers >= 26 weeks loses its annual total.

- **2023 is already affected:** 31 national weekly rows (wk14-52, sum 60 sCh) → the annual WER/WHO 207
  (row 60, conf 0.95) is dropped; wk1-13 have no national row although the Jan-Mar Western Province
  outbreak (row 278, 90 sCh, 2023-01-05..03-05) and the Nyamasheke/Karongi wk11-13 cases (rows 279-282)
  exist only as sub-national rows. The built 2023 series therefore reads ~60 instead of ~207.
- **2016 is at risk:** writing the 2016 bulletin weekly zeros (wk1-13, 22, 25-27, 34, 36-40, 42-52 per
  Agent 2) would cross 50% while the bulletin positives sum to ~190 against WHO annual 355 (row 41).
- Other years with an annual national row currently stay below the threshold (2005 4/52, 2012 5/52,
  2015 5/52, 2021 1/52, 2022 1/52). 2013/2014/2017/2019 have no annual national row (sub-annual
  national rows can be displaced the same way).

Rules from now on:
1. Before writing ANY national (`AFR::RWA`) weekly row or weekly zero, check the year: if the national
   weekly rows would reach >= 50% of the year's weeks while their sum is materially below the year's
   annual national total, do not write them until the positive weeks are complete; log the evidence
   and hand it to Agent 5.
2. Agent 5 owns the repair of 2023 (and any similar year): complete the national weekly series from the
   rendered RBC bulletins (national weekly counts for wk1-13 and any week whose cases sit only in
   sub-national rows), or — where only a multi-week figure exists and the source makes it the national
   total — add a national row for that span with `National total - includes provinces not individually
   listed`. Never invent a national figure from districts the source does not state are the only
   affected ones. Record the before/after 2023 national weekly sum.
