---
name: cross-country-source-harvesting
description: >
  Harvest cholera figures for OTHER MOSAIC countries from multi-country documents that any
  country's agents already collected - ECDC Communicable Disease Threats Reports, WHO
  multi-country cholera situation reports / epidemiological updates, Weekly Epidemiological
  Record (WER) annual cholera reports, WHO AFRO outbreak bulletins, Africa CDC weekly reports,
  UNICEF/OCHA regional updates. Use when starting a country (pull what other countries'
  documents already say about it), after registering any multi-country source (push its
  other-country figures), when running the global sweep, or when auditing rows tagged
  [XREF-HARVEST]. Covers the py/xref_harvest.py pipeline, the agent extraction protocol,
  the screening decisions, the weekly-builder gate, and the guardrails (no zeros from absence
  in a list, reporting windows are not epidemiological periods, preliminary totals get revised,
  derivative restatements, country-name traps).
---

# Cross-country source harvesting

Agents search one country at a time, so a multi-country document found for country A is
mined for A only. On 2026-10-07, 49 such documents held 389 MOSAIC-country cholera figures,
and only 58 (15%) had been used by the country they describe. The ECDC CDTR for week 35 of
2026 has paragraphs with figures for 10 MOSAIC countries. Six countries found it
independently, and only Angola used its own paragraph.

Harvesting takes the hard part (finding and validating the document) as done and needs **no
WebSearch**. It is cheap, but it is also the easiest way to inject duplicates, false zeros and
figures assigned to the wrong country. Every figure goes through `py/xref_harvest.py`, which
verifies it mechanically, screens it against everything the target country already has, and
simulates the weekly builder before writing it.

Read [reference.md](reference.md) before you extract from a series for the first time. It
covers series formats, worked examples and the decision table.

Run every command with `python3 -I -B`: `-I` because the tool reads downloaded, untrusted
documents, and `-B` because `-I` ignores `PYTHONDONTWRITEBYTECODE`. Do not wrap the tool in
`py/with_lock.py`; it takes its own lock (`reference/.xref_tool.lock`).

## Who may run what

Countries run in parallel, and `reference/xref/` is shared. The tool serialises its own
writes, so the rules below are about ownership and freshness, not file safety.

| Role | Commands |
|---|---|
| Any per-country agent | `queue $ISO` (read-only). `fetch --url URL --name NAME --citing $ISO` (one document, into its own cache folder). `verify FILE` (read-only). |
| Agent 1 (and the orchestrator, if Agent 1 is skipped) | `apply --run xref-$ISO-$(date +%Y%m%d) --iso $ISO --dry-run`, read every line, then the same without `--dry-run`. It writes only this country's files. Candidates already logged as added are skipped, and each row is re-screened against the country's current data and passed through the builder gate just before it is written. None of that can catch a figure the queue misread, so read the dry run. |
| Agent 7 | `rollback --run RUN --iso $ISO --reason "…"`. Never `--all` from a country run. |
| Global sweep (maintainer or runner, between country runs) | `registry`, `fetch`, `aliases`, `excerpt`, `parse`, `screen`, `apply --all`, `rollback --all`. |

Per-country agents never write another country's data files, because that country may be
mid-workflow in another process. Figures for other countries go into a candidates file, and
the sweep screens and applies them.

## Roles

| Role | What to do |
|---|---|
| Orchestrator, before Agent 1 | `python3 -I -B py/xref_harvest.py queue $ISO > /tmp/${ISO}_xref_queue.txt`. Pass the file to Agents 1 and 5. |
| Agent 1 | Apply the `ADD` items before searching (commands above). This is not a search batch and does not count toward the 3-batch minimum. |
| Agent 2 | `LOG_SUBNATIONAL` items are leads. Re-read the passage before adding any sub-national row through `py/add_observation.py`. |
| Agent 3 | `LOG_ZERO` items are **unverified zero claims**. Validate each one like any other zero. A country missing from a multi-country list is never a zero. |
| Agent 4 | Extract the annual cholera report tables of any WER issue you open, for every MOSAIC country. Do **not** extract from WER weekly notification tables (see guardrails). |
| Agent 5 (owner of the push) | For each multi-country document this country registered, run `fetch --url`, extract the figures for the other MOSAIC countries per the protocol into `reference/xref/candidates/agent_${ISO}_a5_$(date +%Y%m%d).csv`, then run `verify`. Also reconcile the `CONFLICT` and `CORROBORATES` items in your queue. |
| Agent 6 | `CONFLICT` and `CONFLICT_ZERO` items are evidence about this country's gaps. Adjudicate them. |
| Agent 7 | Audit rows whose `processing_notes` contain `[XREF-HARVEST` (use `reference/xref/harvest_log.csv` for the list). Re-verify at least 10, or all if there are fewer. Report `CONFLICT_BUILDER` items to the maintainer; they need a builder fix, not a data edit. |

## Global sweep

```bash
python3 -I -B py/xref_harvest.py registry
python3 -I -B py/xref_harvest.py fetch --workers 6     # checks each document's series header
#   IRIS throttles hard: requests are spaced 1.5 s per host; if it still times out, run
#   `fetch --exclude-host iris.who.int` now and `fetch --only-host iris.who.int` later
python3 -I -B py/xref_harvest.py aliases               # ReliefWeb report pages <-> their PDF attachments
python3 -I -B py/xref_harvest.py excerpt               # agent inputs -> cache/xref_excerpts/
python3 -I -B py/xref_harvest.py parse                 # ECDC paragraphs + AFRO bulletin tables
#   agents extract the other series per the protocol -> reference/xref/candidates/agent_*.csv
python3 -I -B py/xref_harvest.py verify reference/xref/candidates/agent_<file>.csv
python3 -I -B py/xref_harvest.py screen
python3 -I -B py/xref_harvest.py apply --run xref-YYYYMMDD --all --dry-run   # one line per candidate
python3 -I -B py/xref_harvest.py apply --run xref-YYYYMMDD --all
python py/validate_quality.py                          # ERROR must stay 0
python3 py/with_lock.py dashboard -- bash update_dashboard.sh
```

Read the dry run line by line before applying, and open the source for anything surprising.
On 2026-10-08 that reading caught a calendar-month row mistaken for a cumulative snapshot
(Malawi), a preliminary total that a later bulletin revised (Angola), and source entries titled
with ReliefWeb navigation text (Somalia). All three are now rules in the tool.

After applying, compare each country's weekly series with the previous build (git
`HEAD:data/{ISO}/cholera_weekly_{ISO}.csv`): year totals, and the weeks inside each new row's
period and inside the country's zero rows. The gate checks all three, but a total that moves at
all deserves a look.

## Agent extraction protocol

Input: an excerpt from `cache/xref_excerpts/` (from the sweep), or the cached `text.txt` that
`fetch --url` printed. Output: rows in your own candidates file, using exactly this header:

```
doc_key,target_iso,location,tl,tr,period_type,sch,cch,deaths,quote,extractor,notes
```

1. **One row per explicitly stated figure** for a MOSAIC country and period. Cover every
   MOSAIC country in the document.
2. **`quote` is copied verbatim from the cached full text,** OCR errors included. It must
   start and end on whole words, contain every number you record, and name the country. The
   one exception is a paragraph that opens with a country heading ("Angola: Since …"): the
   quote may be the sentence inside that paragraph.
3. **No arithmetic, no approximations.** Record only numbers the document states as counts.
   Never derive increments, sums or differences. Skip "over/about/nearly/estimated/~/plus
   de/cerca de…" figures.
4. **Dates and `period_type` exactly as stated:**
   - `weekly`: one week.
   - `period`: a stated epidemiological interval of at least 7 days.
   - `ytd`: 1 January to the as-of date.
   - `prior_year_ytd`: the same, for a comparison year.
   - `annual`: a calendar year.
   - `outbreak_cumulative`: from a stated start.
   - `reporting_window`: anything counted "since the last update", "new cases since …", "in the
     last 28 days" or "this week" by report date. It is logged and never written.

   **Every date must be printed for that figure.** A printed epidemiological week may be
   converted to its ISO week (Monday to Sunday), and a start given only as a month may be set
   to its 1st. A report, bulletin or publication date is **never** an as-of date: a note such
   as "as-of date taken from the bulletin date" is rejected, and so is any period ending more
   than 14 days after the document's publication. If you cannot tell which type a figure is, or
   its period is not printed, skip it.
5. **Counts.** `sch` is the suspected or total cases as reported. `cch` is filled only when the
   document says laboratory-confirmed. Fill `deaths` only when stated for the same country and
   period.
6. **Zeros.** Record a zero only for an explicit `0` or "no cases" stated for that country and
   period. Never record one for a country missing from a list, or listed under "no updates have
   been reported by …". Zero rows are logged for Agent 3, never written.
7. **`location`.** Use `AFR::{ISO}` for national figures and `AFR::{ISO}::{Unit}` only when the
   document names the unit. Zanzibar, Somaliland, Cabinda and similar are sub-national.
8. **Skip:**
   - imported cases;
   - vaccination figures;
   - AWD figures not labelled cholera. `screen` judges this from the quote's own words and the
     document's footnotes for that country, not from your notes. Somalia and Ethiopia are
     exempt, because AWD/cholera is their national case definition;
   - figures from outbreaks the document calls unconfirmed (e.g. "gastroenteritis of unknown
     origin");
   - non-MOSAIC countries.
9. Set `extractor` to your agent name and date, and use `notes` for column meaning and
   footnotes. **Run `verify` and fix every reject before you finish.**

## What `screen` decides (and `apply` re-checks)

Mechanical checks come first:

- the quote is found verbatim on token boundaries;
- every count is a whole number inside the target's part of the quote;
- the country is named in the quote or its paragraph heading, and not inside a longer name
  such as "Democratic Republic of the Congo";
- the period type matches the span, and cumulatives of 8 days or less are logged
  (`LOG_SHORT`): the builder would read them as observed weeks;
- the dates are printed for the figure and end no more than 14 days after publication;
- there is no reporting-window wording, approximation, imported-case wording, or sub-national
  qualifier.

Then come the consistency checks against every national row of the target (AI, JHU, WHO,
any span). A national row is coded `AFR::{ISO}` or `EMR::{ISO}`: JHU codes all of Somalia
`EMR::SOM`. JHU rows marked `Phantom: True` (derived, not reported) are left out.

- a figure restated with shifted dates counts as corroboration (`CORROBORATES`), not new data;
- a national figure equal to one of the target's sub-national rows for the same period is
  `DUPLICATE_SUBNATIONAL`;
- a document the target already cites (under any URL or alias) keeps the target's own coding:
  `LOG_TARGET_CITES`;
- a part must not exceed the row that encloses it, and a whole must not fall below a row or
  the sum of weeks it contains;
- cumulative series that share a start date must keep rising, and a total that a later
  document of the same series revises is `CHAIN_SUPERSEDED`. Only national figures with a
  usable decision can supersede one: never a sub-national, window, zero or AWD figure;
- a positive figure is `CONFLICT_ZERO` when fewer than 7 of its days fall outside the target's
  zero rows and no finer positive row already records cases inside it;
- equal-or-finer coverage is measured at week resolution. Earlier snapshots of the same
  cumulative chain (identical start date) do not count as coverage of a later total.

Last come CLAUDE.md's rules: a second independent source for figures over 1,000 cases, and CFR
outliers over 20% are logged (15-20% caps the weight at 0.60, 10-15% at 0.70).

**The builder gate.** Just before writing, `apply` runs the weekly builder for the country with
and without the row, and holds the row as `CONFLICT_BUILDER` if it would:

1. lower a year by more than max(2, 1%), unless the new total is closer to that year's official
   (JHU/WHO) annual;
2. raise a year the row does not cover by more than max(2, 1%, a quarter of the row);
3. add more cases to the whole series than the row carries;
4. turn documented-zero weeks into estimates;
5. leave the weeks inside its own period further from its count than they were (BDI 2020:
   68 → 83 cases against a row of 70);
6. move cases into zero periods (inferred or untagged) beyond what it repairs inside its own
   period. ZMB 2017's year-to-date rows were allowed to move a builder surplus out of Jan-May,
   which their counts forbid, into an inferred-zero window: the counts are the stronger
   evidence.

The builder's coverage rule is not monotone, so a correct row can still damage the weekly series;
the fix belongs in the builder, never in forcing the row in (`--no-gate` exists for testing
only).

| Decision | Written? |
|---|---|
| `ADD` | yes, by `apply`, finest periods first, each re-screened and gated just before writing |
| `CORROBORATES`, `CONFLICT`, `CONFLICT_ZERO`, `CONFLICT_HARVEST` | no; evidence for Agents 5 and 6 to adjudicate |
| `CONFLICT_BUILDER` | no; a builder limitation, not a data conflict. Report it |
| `SKIP_COVERED`, `DUPLICATE`, `DUPLICATE_SUBNATIONAL`, `CHAIN_SUPERSEDED`, `LOG_TARGET_CITES` | no |
| `LOG_*` (ZERO, SUBNATIONAL, WINDOW, SHORT, AMBIGUOUS, AGGREGATE, DEFINITION, CFR_OUTLIER, UNCORROBORATED, NOCOUNT) | no; leads |
| `REJECT_*` | no; failed verification |

Among same-period candidates the official series wins (WER > WHO_MC > AFRO_OEW > AFRICA_CDC >
ECDC > UNICEF > OCHA). After that, the later document wins as a revision. A document without
a publication date is dated by the "as of" date in its own title (ReliefWeb page titles), or
else ordered by the latest as-of date among its figures.

**Source entries.** `apply` reuses the target's metadata entry only for the exact URL that was
verified, and only if it is Active and at the series' reliability level. Otherwise it registers
a neutral entry titled from the document itself: never another country's label, never a file
name, never page navigation text.

## Guardrails (each one is a failure that has already happened)

- **Absence from a list is not a zero.** The 2026-10-07 audit relabelled 106 such zeros and
  deleted 4.
- **Reporting windows are not epidemiological periods.** Somalia's ECDC "since 12 July" row
  covered weeks 27-32 and had to be retracted. WHO's "last 28 days" columns are the same kind
  of figure.
- **Preliminary totals get revised.** JCISA bulletin 10 gave Angola 168 cases to 19 February
  2017. Bulletin 12 revised those weeks to 200 and gave week 8 as 11. Writing both totals would
  have implied 43 cases in week 8.
- **Dates come from the figure, not the bulletin.** 38 extracted rows took their as-of date
  from a report or publication date and were set aside on 2026-10-07. `screen` now rejects
  them.
- **Aggregators restate primary data.** Screening keeps their figures out wherever primary
  data already exist. A figure that only restates an existing row is `CORROBORATES`.
- **A correct row can still break the weekly series.** Four correct Zambia 2018 weekly rows
  would have made the builder drop a 5,426-case increment, and later push 294 cases into 2017.
  A correct Burundi 2020 total put 83 cases into its own 70-case period. The gate holds such
  rows.
- **Region prefixes.** JHU codes Somalia `EMR::SOM`. An `AFR::`-only filter hid all 736 of
  its JHU rows, and nine harvested Somalia weeks that copied them were written, then rolled
  back. (`py/build_weekly_timeseries.py` still reads `AFR::` only, so Somalia's JHU weeks are
  absent from its weekly series.)
- **AWD footnotes vary.** "Includes cholera cases and Acute Watery Diarrhoea AWD cases" is the
  same footnote as "includes cholera and AWD". A Namibia 2008-09 total of 287 nearly went in
  as cholera.
- **Country names.** DRC wraps across lines ("Democratic Republic of the / Congo") and has many
  spellings ("RD Congo", "Congo DR", "Zaire"). Guinea-Bissau and Equatorial Guinea are not
  Guinea, Niger State and the Niger River are not Niger, and Zaire Province is in Angola.
- **WER weekly notification tables are excluded.** They print several columns side by side, so
  one text line mixes countries and diseases. A verbatim quote can then pair numbers with the
  wrong country, and nothing can detect it. They need a page-image pass, which has not been
  built yet.
- **Unconfirmed outbreaks.** A WHO AFRO bulletin event row described as gastroenteritis or
  shigellosis is not cholera. The Republic of the Congo's 1,365 "cases" in 2023 were exactly
  that.
- **Moving targets.** Never cite a live page whose content is replaced, such as ECDC's
  cholera-monthly page.
- **Untrusted downloads.** Always run with `python3 -I -B`, and read cached files as text only.
  Image-only PDFs (many 2026 Africa CDC reports) have no text, so they cannot be verified.
  Never transcribe them by eye.

## Search log

Harvesting is not a search batch and does not change your yield. Log one line:
`=== XREF HARVEST === docs N, candidates C, verify rejects R` (Agents 4 and 5), or
`=== XREF APPLY === applied A, re-screened out S, builder-gated G` (Agent 1).
