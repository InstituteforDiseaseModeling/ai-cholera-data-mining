# Context Transfer — Compile a 2015+ WHO + JHU + High-Confidence-Zero cholera surveillance dataset for MOSAIC-pkg

**Audience:** an agent working in `/Users/johngiles/MOSAIC/MOSAIC-pkg/` (with read access to the sibling repos).
**Author:** prepared from an analysis session in `/Users/johngiles/MOSAIC/ai-cholera-data-mining/` (2026-06-18).
**Status:** design + findings handoff. Nothing in MOSAIC-pkg has been changed yet.

---

## 1. Goal

Extend MOSAIC's observed cholera surveillance (the data the model is fit against) from its current **2023-02-01 start back to 2015-01-01**, and improve per-country coverage, by combining **three layers**:
1. **WHO** observed cases (recent, ~2023+; 15 countries on the WHO dashboard)
2. **JHU** observed cases (the dense 2015–2022 backbone)
3. **High-confidence, surveillance-CONFIRMED zero-transmission** weeks (informative zeros)

The guiding constraint from the project lead: the window should be **mostly supported by WHO + JHU, with high-confidence zero documentation filling gaps** — *not* by model interpolation or assumptions.

---

## 2. Current state of MOSAIC-pkg data (verified)

- Observed data lives in **`MOSAIC-pkg/data/config_default.rda`** as `config_default$reported_cases` and `config_default$reported_deaths` — integer matrices **40 locations × daily**, NA allowed.
- **Window: 2023-02-01 → 2026-10-29**, set by `date_start` in **`MOSAIC-pkg/data-raw/make_config_default.R`** (~line 9) and **`MOSAIC-pkg/model/LAUNCH.R`** (`DATE_START`/`DATE_STOP`, ~lines 7–8). `date_stop` is derived from the LSTM psi forecast max date.
- Built from **`MOSAIC-data/processed/cholera/weekly/cholera_surveillance_weekly_combined.csv`** via **`process_cholera_surveillance_data()`** (`MOSAIC-pkg/R/process_cholera_surveillance_data.R`), source priority **WHO > JHU > AI > SUPP**, with **`include_ai = FALSE` by default**. Weekly is downscaled to daily by **`downscale_weekly_cholera_data()`**; daily combined file is `MOSAIC-data/processed/cholera/daily/cholera_surveillance_daily_combined.csv`.
- The likelihood **`calc_model_likelihood()`** (`MOSAIC-pkg/R/calc_model_likelihood.R`, via `calc_log_likelihood()`) consumes those matrices with a **Negative-Binomial** time-series likelihood. **NA observations are masked out**; a location needs **≥3 finite observations** to contribute. → A confirmed **0** is informative (constrains transmission); an **NA** contributes nothing. This 0-vs-NA distinction is central to this whole task.
- **The upstream weekly combined file already contains JHU back to ~2010** — MOSAIC is simply discarding it via `date_start`. So extending the window back is largely "admit data MOSAIC already has," **not** an import problem for cases.
- **Confirmed problem:** within the current window many countries have large gaps; e.g. **Angola (AGO) has data only from Jan 2025** — all of 2023–2024 empty.

---

## 3. The other data source (the AI-enhanced repo)

`/Users/johngiles/MOSAIC/ai-cholera-data-mining/data/{ISO}/` (the 40 MOSAIC countries) contains:
- `cholera_data_jhu.csv`, `cholera_data_who.csv` — baselines (same lineage as MOSAIC-data).
- `cholera_data_ai.csv` — **AI-discovered rows** (the enhancement). 14-col schema: `Index,Location,TL,TR,deaths,sCh,cCh,CFR,reporting_date,source_index,source,confidence_weight,processing_notes,source_database`. Includes outbreak rows AND **zero-transmission rows** (sCh=0) whose `processing_notes` carry an **evidence-type tag**: `Documented_Absence`, `Inferred_Absence`, or `Surveillance_Gap`.
- `cholera_weekly_{ISO}.csv` — an **integrated weekly product** (JHU+WHO+AI merged + gap-filled). Columns: `iso_code,year,iso_week,week_start,week_end,sCh,deaths,source,confidence_weight,disaggregation_method`. **NOTE: this weekly file does NOT carry the evidence-type tag** — only `disaggregation_method` ∈ {observed, documented_zero, assumed_zero, fourier_*}. (Implication below.)

---

## 4. Key findings — rely on these; do not re-derive

**Coverage at a 2015 start** (per-country observed case data, of 12 years):
- Tiers: **14 STRONG** (≥9 yrs: COD, NGA, BFA, LBR, CIV, CAF, COG, GHA, TGO, TZA, BEN, MOZ, UGA, ZMB), **15 MODERATE** (4–8 yrs: AGO, BDI, CMR, ETH, GIN, GNB, KEN, MLI, MWI, NER, SLE, SOM, SSD, TCD, ZWE), **3 WEAK** (MRT, NAM, RWA), **8 NO case data** (BWA, ERI, GAB, GMB, GNQ, SEN, SWZ, ZAF).
- Mean coverage: **observed-only 42%; +high-conf zero (≥0.8) 66%; +all documented zero 77%.** Countries ≥50% covered: **14 → 28 → 35**. All 8 zero-data countries gain real confirmed-absence data.

**Only 15 countries are on the WHO weekly dashboard** (recent 2023+ data): AGO, BDI, COD, COG, ETH, KEN, MWI, MOZ, NAM, NGA, RWA, SOM, SSD, TZA, ZMB (+CONGO). The **~25 others are JHU-only and effectively go dark after ~2023–2024** — that is where AI recent gap-fill would matter most (separate, later effort; see §8).

**Composition of the 2015+ integrated weekly product** (what you'd get if you imported it wholesale — DON'T): 42% observed, 24% documented_zero≥0.8, **11% documented_zero@0.70**, **3% assumed_zero**, **21% fourier interpolation**. → **~34% is modeled/assumed, not observed.**

**Quality of the AI zero-transmission rows** (n=151): **54% Documented_Absence, 29% Inferred_Absence, 16% untagged, 1% surveillance_gap.** Critically, **Inferred_Absence rows carry confidence weights up to 0.90** — so `confidence_weight ≥ 0.8` alone does NOT separate confirmed from assumed. **You must filter on the evidence-type tag, not the weight.**

**Known data-quality issues to handle:**
- **KEN** `cholera_weekly_KEN.csv` is duplicated (~835 weeks vs ~598 expected).
- **~51 legacy "source-attribution debt" rows** in AGO/BFA/ETH/KEN/MWI `cholera_data_ai.csv` where the `source` label doesn't exist in `metadata_ai.csv` (source_index still resolves). Documented; not auto-fixable.
- Most AI **case** rows are **cumulative / annual / provincial aggregates flagged "do not sum"** — they cannot be placed as weekly observations and must NOT be summed into national weeklies.
- The AI corpus is explicitly an **experimental, not-human-validated pilot** (per its own CLAUDE.md).

---

## 5. The method (3 layers, 3 trust treatments)

**Build on MOSAIC's existing WHO+JHU merge. Inject ONLY a curated AI-zero layer. Import no interpolation.**

### Layer 1 — Cases (WHO + JHU)
- Source: MOSAIC's own `process_cholera_surveillance_data()` output, `disaggregation_method == observed` only.
- Overlap priority: **WHO > JHU** (already MOSAIC's rule).
- Set **`date_start = 2015-01-01`**.

### Layer 2 — High-confidence zeros (curated from the AI repo)
**Build this from `cholera_data_ai.csv` directly, NOT from `cholera_weekly_*.csv`** (the weekly file lacks the evidence-type tag needed to exclude inferred absences). For each AI row, keep it only if ALL hold:
- `sCh == 0` (zero-transmission row),
- `processing_notes` contains **`Documented_Absence`** (exclude `Inferred_Absence`, `Surveillance_Gap`, and untagged),
- `confidence_weight ≥ 0.8`,
- `Location` is **national** (`AFR::{ISO}`, not provincial),
then **expand each row's `TL`→`TR` period into ISO weeks** = confirmed-zero weeks.
- Also exclude the **0.70-weight JHU "documented_zero"** weeks (likely "no report" ≠ confirmed absence) — leave NA.

### Layer 3 — Everything else → `NA`
Drop all `fourier_*`, `assumed_zero`, inferred/untagged zeros. **Do not impute.** Let MOSAIC's model interpolate at fit time; never import another model's fills as data.

### Merge rule (per country-week) — prevents the traps
1. Positive cases reported (any source, WHO>JHU) → value = cases. **A positive always overrides a zero.**
2. Else a curated Documented_Absence week (Layer 2) → value = **0**.
3. Else → **`NA`**.
Apply the analogous rule to **deaths** (deaths = 0 only on a Documented_Absence week; else NA).

---

## 6. Pre-clean the AI input before merging (one-time)
- Dedupe **KEN** (collapse to ~598 weeks).
- **Drop cumulative "do-not-sum"** AI case rows (quarantine for cross-validation; never merge into weeklies).
- Exclude/repair the **~51 attribution-debt rows** if any fall in the zero layer.
- Ensure **no national + provincial double-count** (national series uses national rows only).

---

## 7. Implementation steps (reuse MOSAIC machinery)
1. Produce a single **`cholera_zero_transmission_ai.csv`** (the curated Layer 2, weekly, columns at least: `iso_code, week_start, week_end, value=0, source="AI_zero", evidence_type, confidence_weight`) into `MOSAIC-data/processed/cholera/`.
   - *This export can be generated on the ai-cholera-data-mining side; the spec in §5 Layer 2 is sufficient to regenerate/verify it. Coordinate on who produces it.*
2. Extend **`process_cholera_surveillance_data()`** to merge it as a **zeros-only source** (add `AI_zero` so it can never inject positive cases) under the §5 merge rule. Carry `source`, `evidence_type`, `confidence_weight` through per week for auditability/likelihood weighting.
3. `downscale_weekly_cholera_data()` → daily.
4. Set **`date_start = 2015-01-01`** in `data-raw/make_config_default.R` (and `model/LAUNCH.R`); rebuild **`config_default.rda`**.

---

## 8. Out of scope for this task (note, don't do now)
- Using AI **case** rows to fill the ~25 non-WHO-dashboard countries' 2024–2026 hole — requires disaggregating cumulative figures into period increments first. Separate effort.
- Cleaning the full AI corpus / attribution debt beyond the rows that enter Layer 2.

---

## 9. Validation gates (must pass before shipping config_default.rda)
- No week has **both** positive cases and a zero flag.
- `deaths ≤ cases` everywhere; no future dates; `TL ≤ TR ≤ reporting_date` on source rows.
- Per-country **% real coverage** (observed + Documented_Absence) matches the §4 expectation; previously-blank countries (SEN, GMB, GAB, …) show **documented** absence, not fabricated zeros.
- **Diff new vs old `config_default` over the 2023+ overlap**: existing values must be unchanged — only earlier years added and confirmed zeros gained.
- Confirm **no `fourier`/`assumed_zero`/inferred content** leaked into the matrices (every non-NA, non-positive cell traces to a Documented_Absence source).

---

## 10. Decisions to confirm with the project lead
- `date_start` = **2015-01-01** (recommended) vs 2017 (slightly cleaner, loses 2015–16 outbreaks).
- Zero filter = **Documented_Absence + cw ≥ 0.8 + national** (recommended; excludes inferred even at cw 0.9).
- Whether to **down-weight** zeros vs observed cases in the likelihood (the `confidence_weight` column enables this).

---

## 11. Key file/function reference
- `MOSAIC-pkg/data/config_default.rda` — target object (`reported_cases`, `reported_deaths`, `date_start`, `date_stop`).
- `MOSAIC-pkg/data-raw/make_config_default.R` — builds it; **set `date_start` here**.
- `MOSAIC-pkg/model/LAUNCH.R` — `DATE_START`/`DATE_STOP`.
- `MOSAIC-pkg/R/process_cholera_surveillance_data.R` — WHO/JHU/AI/SUPP merge (`include_ai`, priority); **extend here**.
- `MOSAIC-pkg/R/downscale_weekly_cholera_data.R` — weekly→daily.
- `MOSAIC-pkg/R/calc_model_likelihood.R`, `R/calc_log_likelihood.R` — likelihood (NegBin, NA-masked, ≥3 obs).
- `MOSAIC-data/processed/cholera/weekly/cholera_surveillance_weekly_combined.csv` and `.../daily/cholera_surveillance_daily_combined.csv`.
- AI repo: `/Users/johngiles/MOSAIC/ai-cholera-data-mining/data/{ISO}/cholera_data_ai.csv` (evidence-type in `processing_notes`), `cholera_weekly_{ISO}.csv` (no evidence-type — do not use for the zero filter).
