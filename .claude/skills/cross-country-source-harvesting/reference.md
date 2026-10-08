# Cross-country source harvesting: reference

Companion to `SKILL.md`. It covers the series formats, how to read each one, worked examples
of good and bad candidate rows, and the screening rules in detail.

## Period types

| `period_type` | TL | TR | Constraint `screen` enforces | Written? |
|---|---|---|---|---|
| `weekly` | first day of the week | last day | span 6-8 days | yes |
| `period` | stated start | stated end | span at least 7 days | yes |
| `ytd` | 1 January | as-of date | starts 1 January of TR's year; more than 8 days | yes |
| `prior_year_ytd` | 1 January of the comparison year | its as-of date | a year before the document; more than 8 days | yes |
| `annual` | 1 January | 31 December | one calendar year | yes |
| `outbreak_cumulative` | stated start | as-of date | 9-400 days (8 or less: `LOG_SHORT`; over 400: `LOG_AMBIGUOUS`) | yes |
| `reporting_window` | "since" date | "as of" date | none | **never** (`LOG_WINDOW`) |

Any type other than `annual` spanning more than two years is `LOG_AGGREGATE`.

**Dates.** Every date must be printed for the figure itself.

- A printed epidemiological week may be converted to its ISO week, Monday to Sunday
  ("2017 - Week 19" ends 14 May 2017). Say so in `notes`.
- A start printed only as a month may be set to the 1st of that month.
- A report, bulletin or publication date is never an as-of date. A note saying the as-of date
  was taken from one is rejected (`REJECT_DATES`).
- "As of" dates are data dates. Do not move them to the publication date. A TR more than 14
  days after the document's publication is rejected.

## Series

### ECDC Communicable Disease Threats Report (ECDC). Parsed automatically.

The monthly cholera item has one paragraph per country:

> **Angola:** Since 12 July 2026 and as of 9 August 2026, 524 new cases, including four new
> deaths, have been reported. Since 1 January 2026 and as of 9 August 2026, 5 903 cases,
> including 120 deaths, have been reported. In comparison, in 2025 and as of 4 August 2025,
> 27 666 cases, including 773 deaths, were reported.

`parse` emits three candidates. Their quotes are the individual sentences, and `screen`
attributes each to Angola through the "Angola:" heading:

- `reporting_window` 2026-07-12..2026-08-09, 524/4 (logged);
- `ytd` 2026-01-01..2026-08-09, 5903/120;
- `prior_year_ytd` 2025-01-01..2025-08-04, 27666/773.

Ignore:

- "New cases have been reported from …" and "no updates have been reported by …" (lists, never
  zeros);
- "In addition, N new cases were reported or collected retrospectively …" (global).

Never cite the live `cholera-monthly` page. Cite the dated CDTR PDF.

### WHO AFRO Weekly Bulletin on Outbreaks and Other Emergencies (AFRO_OEW). Parsed automatically.

The "All events currently being monitored" table has these columns:

```
Country | Event | Grade | Date notified to WCO | Start of reporting period |
End of reporting period | Total cases | Cases confirmed | Deaths | CFR
```

- **Fatality-rate check.** `parse` keeps a cholera row only if deaths/total matches the printed
  CFR, so "5 591 196 166" cannot be misread.
- **Start date.** A 1 January start after notification is a reporting-period reset, and the
  count starts there: Kenya was notified 6-Mar-17, reported from 1-Jan-18, and its 5,756 cases
  are for 2018. Otherwise the start is the earlier of the two dates. The columns are sometimes
  swapped; Cameroon 2021's narrative says "since the beginning of this year".
- **Wrapped names.** A country name is joined from the line above or below only from the
  country column, and only from name words.
- **Rows logged instead of written** (`LOG_SUBNATIONAL`, `LOG_DEFINITION`, `REJECT_IMPORTED`):
  - more than one cholera event for the same country (district events);
  - a parenthetical or sub-national qualifier, such as "Angola (Cabinda)";
  - an event the row's own narrative confines to one province (ADM1 in
    `reference/country_profiles.json`, however many districts in it: "fourteen districts in
    Luanda Province") or, when it names no province, to one named district ("from Kariba
    district"). It stays national if the narrative names two or more provinces, counts them
    ("four regions", "11 health districts", "Twenty-nine districts" where districts are the
    ADM1, as in Malawi and Uganda), says countrywide or nationwide, or gives the country the
    total ("Malawi has reported a total of 63").
  - The narrative is the row's own block: the text after its CFR cell, then the following
    lines up to the next table row. Share clauses ("41% (28) of cases reported from Bujumbura
    Centre health district") describe part of the event, not where the event is, and are
    ignored. A CFR is not a share.
  - The rule is a heuristic, and it errs in both directions. A national event wrongly logged is
    only a lost harvest. A local event wrongly kept national is a real error, which the
    screening and the dry-run reading must catch;
  - a narrative describing an unconfirmed outbreak (gastroenteritis, shigellosis, AWD);
  - imported cases.
- **Event cumulatives.** An event's rows across successive bulletins form a cumulative chain.
  The weekly builder turns a chain into increments within each layer, provided it keeps
  rising, and drops zero increments. A later bulletin repeating the same total adds nothing:
  once the earlier row is written, the repeat is `CORROBORATES`.

### Weekly Epidemiological Record (WER). Agents extract annual reports only.

- **Annual reports** ("Cholera in 1985", "Cholera, 2018"): table rows give a country, its cases
  (and imported cases) and its deaths for one year, so they are `annual`.
  - Multi-year comparison tables give one `annual` per year column, but only where the column
    alignment is unambiguous.
  - Countries outside Africa with only imported cases are not MOSAIC countries.
- **Provisional "first N months" summaries** give 1 January to the end of month N: `ytd`.
- **2023+ monthly multi-country updates** published in the WER: read them as WHO_MC.
- **Weekly notification tables are excluded.** That covers "Diseases subject to the
  Regulations", "Notifications received" and "Infected areas". They print several columns side
  by side, so quotes taken from them can pair numbers with the wrong country undetectably.
  `excerpt` and `screen` skip and reject them.
- **Table 2 zero rows** in the annual reports (a country listed with 0 cases) are explicit
  zeros: they are logged for Agent 3, never written. A country absent from the table is not a
  zero.

### WHO multi-country cholera situation reports and epidemiological updates (WHO_MC). Agents.

- **Country tables of cumulative cases and deaths "since 1 January YYYY"** are `ytd` to the
  as-of date printed in the table title or footnote.
- **"Cases in the last 28 days" columns** are counted by report date: `reporting_window`.
  Never write them as a period.
- **Columns with a "§" or "*" footnote:** record the footnote in `notes`.
- **Regional prose** ("…Mozambique (39 101 cases), Zambia (4531)…") is `ytd` or `annual`, but
  only if the sentence states the period. The count must sit next to its own country.

### Africa CDC weekly epidemic intelligence reports (AFRICA_CDC). Agents.

- "Since the beginning of YYYY, N cases (M deaths) … in Country" is `ytd` to the report's data
  date.
- "In epi-week W, N new cases" is a `reporting_window`, unless the week's dates are printed and
  the count is for that week only, in which case it is `weekly`.
- Annual-summary issues listing "Country (cases; deaths)" are `annual`, but only if the list is
  introduced as cholera for that year. Skip mixed-disease lists.
- Many 2026 issues are image-only PDFs, so skip them.

### UNICEF regional (ESARO/WCARO, Regional Cholera Platform, JCISA) and OCHA regional (UNICEF_REG, OCHA_REG). Agents.

- Country tables with "since 1 January" columns are `ytd`. Weekly columns are `weekly` only
  when the week dates are printed, or the week number is and the series' own convention gives
  its end ("Week 8, (ending 26 February)").
- **JCISA bulletins (2017)** print weekly columns W1-W12, a "2017 Cumulative total" and a
  comment column ("Latest report 19/02/17", "nr" = no report). The comment fixes the as-of
  date. The columns are ISO weeks ("Week 12, (ending 26 March)"), so extract **every** weekly
  cell as a `weekly` row, not just the latest week; the first sweep took only week 8. Later
  bulletins revise earlier weeks, so take each week from the latest bulletin that prints it:
  `screen` then supersedes or conflicts out the earlier totals (see Chains), and the
  cumulative becomes a restatement of its weeks.
- **ESARO weekly prose** ("During week 9 (week ending 4 March 2018), 174 new cases were
  reported compared to 148 cases reported in week 8 (week ending 25 February 2018)") gives one
  `weekly` row per week whose end date is printed. A week whose dates are not printed is
  skipped.
- A figure attributed to one region is national only when the document attributes it to the
  country too. Somalia 2019 week 9 ("45 new cases were reported from Banadir Region") was
  written as national because the highlights say "Somalia reported the highest number of new
  cases (45 cases)".
- A zero cell is an explicit zero, so it is logged. A blank cell or "-" is not a zero.
- Rounded figures ("over 2,000 cases") are skipped.
- ReliefWeb report pages are titled from the page's own title line, without ReliefWeb's
  primary-country tag ("… - Kenya | ReliefWeb"), and dated by the "as of" date in that title.

## Good and bad candidate rows

**Good.** The quote is the sentence inside the "Mozambique:" paragraph, verbatim, and the
period is explicit:

```
ecdc:2026:35,MOZ,AFR::MOZ,2026-01-01,2026-08-09,ytd,7698,,65,"Since 1 January 2026 and as of 9 August 2026, 7 698 cases, including 65 deaths, have been reported",agent-5 2026-10-07,"ECDC CDTR wk35, paragraph 'Mozambique:'"
```

**Bad**, and why:

| Row | Problem |
|---|---|
| `…,MLI,…,2026-08-17,2026-08-26,period,0,…,"Mali is absent from ECDC's update"` | Zero from absence, and the quote is not verbatim |
| `…,AGO,…,2026-06-14,2026-07-12,period,303,…,"Since 14 June 2026 and as of 12 July 2026, 303 new cases"` | A reporting window labelled `period`: `screen` catches the wording |
| `…,COG,…,"Congo (8401), and Angola (4914)"` | The text just before reads "the Democratic Republic of the", so this is DRC: `REJECT_COUNTRY` |
| `…,KEN,…,"Kenya reported over 1,000 cases"` | Approximate figure |
| `…,TZA,…,"United Republic of Tanzania (Zanzibar) 245 3"` | Sub-national: `LOG_SUBNATIONAL` |
| `…,MOZ,…,"… 19-Oct-21 19"` | The quote cuts the printed 191: `REJECT_UNVERIFIED` |
| `…,ETH,…,2025-01-01,2025-03-14,ytd,…,notes "as-of date = bulletin date"` | The as-of date is not printed for the figure: `REJECT_DATES` |

## Screening details

- **National rows** are those coded `AFR::{ISO}` or `EMR::{ISO}` (JHU codes Somalia
  `EMR::SOM`), minus JHU rows marked `Phantom: True`.
- **Consistency** is checked against every positive national row of the target (AI, JHU and
  WHO layers, any span) that overlaps the candidate or starts within 3 days of it:
  - counts within max(1, 2%) and overlap of at least 50% of either period: `CORROBORATES`
    ("restated");
  - same start, cumulative types: the later must be at least the earlier (2% tolerance),
    otherwise `CONFLICT`;
  - both ends within 7 days but a different count: `CONFLICT`;
  - inside an existing row but more than 1.1× its count: `CONFLICT`;
  - containing an existing row (or weeks summing to) more than 1.1× its own count: `CONFLICT`;
  - mutual overlap of at least 50% with a different count: `CONFLICT`;
  - equal (within 2%) to the sum of the weeks or non-overlapping rows it contains:
    `CORROBORATES`.
- **Sub-national duplicates.** The same count as one of the target's sub-national rows
  overlapping at least 50% of either period: `DUPLICATE_SUBNATIONAL`.
- **Documents the target already cites,** under any URL, identical text or ReliefWeb alias:
  `LOG_TARGET_CITES`. Its own agents read the document, and their coding (often sub-national,
  or deliberately not recorded) stands.
- **Zero coverage.** A positive figure is `CONFLICT_ZERO` when fewer than 7 of its days fall
  outside the target's zero rows and no positive row at least as fine as the candidate records
  cases inside it. Adjudicate by retracting or trimming the zero, or rejecting the figure.
- **Equal-or-finer coverage.** The share of the candidate's days already covered by rows
  (positive or zero) no coarser than max(7 days, its span). For cumulative types, earlier
  snapshots of the same chain are left out: positive rows with the **identical** start date,
  longer than 8 days, ending before TR. (A calendar-month row starting 2 days before an
  outbreak is not a snapshot of it: Malawi March 2022.) At 0.5 or above it is `SKIP_COVERED`.
- **Chains and clusters.**
  - One `ADD` per target and period (both ends within 3 days): the official series first, then
    the later document. The rest are `DUPLICATE` (same count) or `CONFLICT_HARVEST`.
  - A cumulative must not exceed a later existing AI cumulative from the same start, or fall
    below an earlier one: `CONFLICT`. One that exceeds a later verified candidate total from
    the same start is `CHAIN_SUPERSEDED`.
  - **Revisions.** A `ytd` or `outbreak_cumulative` candidate is `CHAIN_SUPERSEDED` when a
    later document of the same series gives a total from the same start to a later date AND
    the count for exactly the interval in between, and the two disagree with it by more than
    max(2, 5%). Undated documents are ordered by their title's as-of date, else by the latest
    as-of date among their figures.
  - Only national candidates whose decision is ADD, CORROBORATES, CONFLICT, SKIP_COVERED,
    DUPLICATE, CHAIN_SUPERSEDED, CONFLICT_HARVEST, LOG_TARGET_CITES, LOG_SHORT or
    LOG_UNCORROBORATED can supersede another. (A Manicaland 6,064 once superseded Zimbabwe's
    national 11,735.)
- **Two-source rule.** Over 1,000 cases needs a second, different-series figure overlapping at
  least 50% within a factor of 1.5. Otherwise it is `LOG_UNCORROBORATED`.
- **CFR.** Over 20% (with at least 20 cases) is `LOG_CFR_OUTLIER`. Between 15% and 20% the
  weight is capped at 0.60, between 10% and 15% at 0.70.
- **Weights** come from the series: WER, WHO_MC and AFRO_OEW 0.90; AFRICA_CDC 0.80; ECDC 0.75;
  UNICEF 0.75; OCHA 0.70. The weight never exceeds the cited source's reliability ceiling
  (Level 1: 1.0; Level 2: 0.9).

## Apply

- Rows are written finest period first, each re-assessed against the country's data as it
  stands at that moment (a repeat of a row written a moment earlier becomes `CORROBORATES`).
- **Builder gate.** For each row, `apply` copies the country's AI, JHU and WHO files to
  `cache/xref_gate/`, appends the row, and runs `build_weekly_timeseries.process_country` on
  both versions. Weeks count pro rata where they straddle a period's edge. It holds the row as
  `CONFLICT_BUILDER` if:
  - a year would fall by more than max(2, 1%), unless the new total is closer to that year's
    official annual (the median of its JHU/WHO national calendar-year rows);
  - a year the row does not cover would rise by more than max(2, 1%, 25% of the row);
  - the whole series would gain more than the row's count +2% +2;
  - a documented-zero week would become an estimate;
  - the cases inside the row's own period would end further from its count than before, by more
    than max(2, 5%);
  - the cases inside the country's other zero rows (inferred or untagged, longer than a week)
    would rise by more than max(2, 2%) plus whatever the row repaired inside its own period.
- The target's metadata entry is reused only for the exact URL that was verified, and only if
  it is Active and at the series' level. Otherwise a neutral entry is registered, titled from
  the document itself. A heading that names its own publisher (JCISA, UNICEF, OCHA, WHO)
  stands alone, undated documents are labelled "(data to DATE)", and `Date_Range` spans all of
  the document's rows for the target in the run. An entry the target already had keeps its
  own `Date_Range`, because no tool widens it.
- `reporting_date` is the document's publication date when known and not before TR. Otherwise
  it is the latest date the document reports (an undated JCISA bulletin 12 → 26 March 2017),
  and failing that TR.
- Every row is logged to `reference/xref/harvest_log.csv` immediately, with the tool's hash.
  A log begun under an older header is migrated automatically.
- Rollback checks the run tag and values before deleting anything, and deletes through
  `py/revise_observation.py`.
