# NGA (Nigeria) - Orchestrator targeting brief, 2026-10-04

Written by the workflow orchestrator for the Opus 5.5 re-run cycle (started
2026-09-29). Every agent (1-7) in this NGA run is given this file. It replaces
nothing in CLAUDE.md or `./templates/template_search_protocol.txt`. It adds the
Nigeria-specific targets that the national-month gap file cannot show, plus
what the 2026-09-21/22 cycle already learned, so this cycle does not spend
queries re-learning it.

## 1. Starting state (measured by the orchestrator before Agent 1)

| Metric | Value |
|---|---|
| `./data/NGA/cholera_data_ai.csv` | 3,391 rows (125 national, 2,414 state, 852 LGA) |
| `./data/NGA/metadata_ai.csv` | 439 sources (Level 1: 362, Level 2: 48, Level 3: 29) |
| `./data/NGA/cholera_presence_ai.csv` | 49 presence-without-count records |
| Validator (`python py/validate_quality.py NGA`) | ERROR 0, WARN 113 (90 CFR>15%, 21 same_period_conflict, 1 multiyear, 1 single-day), INFO 135 |
| Effective coverage (JHU+WHO+AI) | 680/682 months = 99.7%, months_ai_only 27, 1 gap period |
| Baseline-only coverage (JHU+WHO) | 653/682 months = 95.7%, 3 gap periods |
| Latest observation / latest positive | 2026-09-09 / 2026-08-31 |

## 2. Effective gap rows (`./reference/effective_surveillance_gaps_detailed.csv`, NGA)

```
country,iso_code,gap_start,gap_end,days,months,years,era
Nigeria,NGA,2026-09-01,2026-10-04,34,1,0.09,recent
```
No NGA rows in `effective_surveillance_gaps_annual.csv`.

**Read the 99.7% with care.** National *month* coverage is close to complete
because one annual row credits twelve months at once. That says nothing about
weekly resolution or about states. The real remaining targets are below.

## 3. Finer-resolution targets (computed by the orchestrator from all three layers)

### A. National weekly resolution: weeks with NO national row of 8 days or less in any layer
- **2026 ISO weeks 35-40 (2026-08-24 to 2026-10-04).** This is the live epidemic tail. The national weekly series (WHO dashboard feature service, metadata 44) ends 2026-08-23. The WHO baseline file `cholera_data_who.csv` ends at 2026-05-17.
- **2020 ISO weeks 1-45 (2020-01-01 to 2020-11-08).** No layer has national weekly rows. JHU starts 2020-11-09. NCDC published weekly cholera situation reports in 2020 and weekly epidemiological reports (WER). WHO AFRO weekly bulletins also cover this.
- **2022:** 15 of 52 weeks have no weekly national row. **2023:** about 11. **2014:** 13.
- **2000-2013: no sub-annual national rows at all**, apart from scattered months in 2000-2002, 2010 and 2013. The national series for those years is annual totals only. That includes the 2010 epidemic (about 41,787 cases), 2011 (about 23,000) and 2013 (about 6,600). Weekly or monthly national counts from NCDC/FMOH weekly epidemiology reports (the WER series started around 2009-2011), WHO AFRO weekly bulletins, OCHA/ReliefWeb sitreps and WHO DON would all be new information.
- **1976-1999:** national rows are WHO annual totals only. WER weekly notification tables give sub-annual national counts for epidemic years (1991, 1992, 1995-1997, 1999). The prior cycle established that Nigeria is absent from the WER notification tables in 1984, 1987 and 1989.

### B. State (ADM1) coverage: states with any count row, by year, all layers
```
1970:1 1971:19 1972:6 1973:20 1974:36 1975:30 1976-1981:0 1982:1 1983-1990:0 1991:2 1992:1
1993-1994:0 1995:1 1996:6 1997:1 1998:0 1999:4 2000:1 2001:4 2002:1 2003:1 2004:2 2005:5
2006:2 2007:1 2008:3 2009:4 2010:19 2011:13 2012:11 2013:8 2014:8 2015:9 2016:6 2017:14
2018:37 2019:31 2020:37 2021-2025:37 2026:9
```
- **2026: only 9 of 37 states** have a row (Adamawa, Bauchi, Borno, Enugu, Kano, Kebbi, Plateau, Sokoto, Zamfara). UNICEF (metadata 213) reports 35 states affected. Missing: Abia, Akwa Ibom, Anambra, Bayelsa, Benue, Cross River, Delta, Ebonyi, Edo, Ekiti, FCT, Gombe, Imo, Jigawa, Kaduna, Katsina, Kogi, Kwara, Lagos, Nasarawa, Niger, Ogun, Ondo, Osun, Oyo, Rivers, Taraba, Yobe.
- **2010-2017:** 6-19 states per year. Missing in 2014: Abia, Adamawa, Akwa Ibom, Anambra, Bayelsa, Cross River, Delta, Ebonyi, Edo, Ekiti, Enugu, Gombe, Imo, Katsina, Kebbi, Kogi, Kwara, Lagos, Nasarawa, Niger, Ogun, Ondo, Osun, Oyo, Plateau, Rivers, Taraba, Yobe, Zamfara. Run `python /tmp/NGA_orch/profile4.py` for every year's missing list; the matrix is saved at `/tmp/NGA_orch/state_year_matrix.csv`.
- **1976-2009:** 0-6 states per year.
- A missing state-year is NOT automatically a gap. The state may genuinely have had no cholera. Where an NCDC state table explicitly lists a state with 0, that is a documented zero (Agent 3's territory).

### C. Within-year state resolution
State rows for 2021-2023 are mostly single full-year (1 Jan-31 Dec) rows from NCDC year-end tables. Weekly or monthly state counts for those years would add real resolution: NCDC weekly sitreps print a weekly state table as well as a cumulative one.

## 4. What the 2026-09-21/22 cycle established (do not re-learn it)

Archived logs are in `./data/NGA/prior_run_logs_20260922/` (the full prior report is `search_report.txt` there). Grep them for a topic before searching it; do not read them whole, because they total about 500 KB.

**Access routes that work:**
- ReliefWeb returns HTTP 200 to curl when given an ordinary browser User-Agent. Its report landing pages carry full LGA tables in the HTML.
- Europe PMC `/fullTextXML` returns machine-readable table markup where PMC serves a CAPTCHA.
- The WHO IRIS API answers curl's DEFAULT user agent and refuses a browser one.
- Dead ministry domains (e.g. fmh.gov.ng) survive in the Wayback Machine. Run `file` on every download: five of eight archived "PDFs" were error pages.
- WHO `cholera_adm0_week` FeatureServer (metadata 44): `https://services.arcgis.com/5T5nSi527N4F7luB/arcgis/rest/services/cholera_adm0_week/FeatureServer/0/query?where=...&outFields=*&f=json`. **Use its `date_wk` field for dates.** WHO's 2026 epi week N is ISO week N+1, so deriving dates from the week number puts a row one week early. This is a known pipeline bug in the WHO baseline converter and is not yours to fix. On 2026-09-22 the service returned count=0 for 2026 epi weeks >= 34 for every country, a global publication lag. **Re-query it now.**
- ncdc.gov.ng returned Cloudflare 522 site-wide on 2026-09-21/22. **Re-probe it.** It may be up now.

**Closed on evidence in the prior cycle.** Do not re-run the same queries. Re-open only through a genuinely new route, and say which route in your log.
- NCDC's cholera situation-report series appeared to stop at epi week 39 of 2024, and no 2024 annual report was found. The prior cycle enumerated the full NCDC report inventory. Re-check only whether 2025/2026 cholera sitreps have since appeared.
- Q4 2024 sub-national outside Borno/Adamawa/Yobe.
- UNICEF WCARO regional cholera updates 2014-2015: per-country tables are raster images.
- 2026 non-Borno state geography via NCDC products. **New routes still open:** state ministry and state CDC press briefings (Kano State CDC has one row already), state commissioners quoted in the national press (Punch, Vanguard, Premium Times, Daily Trust, Channels, The Guardian NG, Leadership, Nigeria Health Watch), Hausa-language outlets (BBC Hausa, Aminiya, DW Hausa, VOA Hausa), and WHO AFRO / IFRC / MSF / UNICEF / OCHA products published after 2026-09-10. State counts from Level 3 news are acceptable at confidence 0.3-0.6 with an exact quote.
- The 1980s by general web search. The prior auditor thought the data is probably not digitised. Agent 4 should still try archival routes the prior cycle did not: AJOL journals, Nigerian theses, Google Books snippets of FMOH annual reports, and state statistical yearbooks.

**Known traps:**
- **Gwoza 2024.** The July 2024 BAY Health Sector Bulletin prints 452 Gwoza "suspected cholera" cases. The same paragraph says cholera was EXCLUDED. Read the prose around every table.
- **Sokoto 2008.** FMOH said "we tested for cholera and they were all negative".
- **NCDC Weekly Epidemiological Report 2026 rows (metadata 34)** are a laboratory-linked IDSR stream of about 3% of national cases. They are NON-PRIMARY. The WHO dashboard rows (metadata 44) are PRIMARY for national 2026 weekly. Do not "correct" one by the other. All 21 same_period_conflict pairs were adjudicated in processing_notes on 2026-09-22.
- **Charnley et al. 2022** is ONE dataset registered three times (metadata 359 canonical, 58 and 413 duplicates). It never corroborates itself.
- **Index 13 / national 2022.** 23,550 was the week-47 cumulative, not the full year. The full-year figure is 23,763 / 592 (Index 3501).
- **NCDC cumulative tables are cumulative.** Convert to increments only by subtracting two cumulative reports of the same series. Write cumulative rows as TL = start of series, TR = report date. Never sum cumulative rows through time.

## 5. Rules for this run (all agents)

1. **No time limit.** The only stopping rule for Agents 1-6 is the yield rule: at least 3 batches of 20 queries, then stop at 3 consecutive batches below 5% yield, or at 12 batches. Yield = queries that committed at least one new row / 20, in percent.
2. **Do NOT run `python py/analyze_effective_gaps.py`** without changes. Countries run in parallel and the `reference/effective_*` files are shared. Read them only. For an NGA-only recomputation in memory:
   ```python
   import sys; sys.path.insert(0,'py')
   from analyze_effective_gaps import analyse
   from datetime import date
   d,a,c,r = analyse('NGA','Nigeria',['JHU','WHO','AI'], date.today(), 7)
   ```
3. **Do NOT run `update_dashboard.sh`, `py/update_dashboard_data.py`, or any git command.** The runner owns them.
4. **Context safety.** `./data/NGA/cholera_data_ai.csv` is 6 MB (very long processing_notes). `./data/NGA/cholera_data_jhu.csv` is 15 MB / 75,745 rows. **Never `cat`, `Read` or `head` either file whole.** Query with pandas and print only the short columns (`Index, Location, TL, TR, sCh, deaths, cCh, source_index, confidence_weight`), or truncate processing_notes to about 150 characters. Filter by period or location first.
5. **Write only through `python py/add_observation.py`** (`register-source`, `add`, `add-zero`, `add-presence`). Before any `add`, check existing AI, JHU and WHO rows for the same location and period so you do not duplicate.
6. **Double counting.** Every sub-national row inside a period that has a national row must say `Provincial subset - do not sum with national row` (or `District subset - ...`). A national row must say `National total - includes provinces not individually listed`. Use `--note`.
7. **Cumulative vs increment:** state which in `--note`.
8. **Search log:** `./data/NGA/search_log_agent_{N}.txt`. Agent 1's file was initialised by the orchestrator, so append to it. Agents 2-7 start a fresh file (overwrite the old one; it is archived). Write one block per batch in the protocol shape.
9. **Finish with** `python py/validate_quality.py NGA` (exit 0), then `write_agent_state(...)` with `batch_yields` in PERCENT units.
10. **Amending existing rows** (append an adjudication or double-counting phrase, re-weight, retract with tombstone, correct a metadata Description): use `python py/revise_observation.py NGA --index N --append-note "..." --reason "..."` (see `--help`). Never hand-edit.
11. **Rows must carry information.** Repeated cumulative snapshots from the same series whose counts are identical to the previous snapshot add little; prefer the issues where values change, the latest/closing issue, and any issue that closes a period. Increments derived by subtracting two cumulative issues of the same series are valuable - label them "derived increment".

## 6. Session constraint discovered mid-run (orchestrator, 2026-10-04 ~19:25 PDT)

**WebSearch is exhausted for this NGA session.** The 200-call session budget
(`CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION`) was consumed by the end of Agent 3.
The orchestrator confirmed it with a test call ("200 of 200 WebSearch calls").
It cannot be raised from inside a running session. Agents 4-7 therefore work through
**WebFetch and curl direct routes only**. Each direct query counts as one query
in the batch, and is logged with its URL.

Route status tested by the orchestrator at about 19:25 PDT:

| Route | Status | Use |
|---|---|---|
| ncdc.gov.ng | 200 (UP; it was 522 in Sept) | sitreps, WER issues, advisories |
| ReliefWeb RSS `https://reliefweb.int/updates/rss.xml?search=...` | 200 | 20 items per call; narrow with date words or half-year windows; landing pages carry tables |
| ReliefWeb API v2 | 403 (needs an approved appname) | do not use |
| ReliefWeb API v1 | 410 retired | do not use |
| Europe PMC REST search and `/fullTextXML` | 200 | citation chains, full-text tables |
| Crossref API `api.crossref.org/works?query=` | 200 | reference lists, citing works |
| WHO GHO OData `ghoapi.azureedge.net/api/{INDICATOR}?$filter=SpatialDim eq 'NGA'` | 200 | other notifiable diseases (health-system functioning) |
| Wayback CDX `web.archive.org/cdx/search/cdx?url=...` | 200 | dead links, old NCDC/FMOH pages |
| AJOL search | 200 | Nigerian journals |
| Google Books old feed `google.com/books/feeds/volumes?q=` | 200 | FOS Annual Abstracts, yearbooks (v1 API is rate-limited, 429) |
| WHO IRIS | timeout | retry later; Wayback copies of IRIS PDFs as fallback |
| AllAfrica | unreachable | try Wayback copies |
| DuckDuckGo / Bing HTML scraping | unreliable (0 results / query ignored) | do not rely on it |

The WHO 2026 week-shift in `cholera_data_who.csv` was repaired on 2026-09-22 by
`py/fix_who_week_shift.py`. The baseline now carries WHO's own week-start dates,
so correctly dated AI weekly rows align with it. Do not duplicate WHO baseline
weeks 2026 W1-W19 into the AI layer.
