"""
Country profile source data for PILOT countries (reference/pipeline_countries.json).

Same fields as py/country_profiles_data_a.py, plus three that only pilots use:

  regional_sources  replaces the WHO AFRO / Africa CDC source lists in the
                    search protocol and agent prompts
  archive_hints     replaces the francophone/lusophone colonial-archive hints
  country_notes     country-specific rules, pasted verbatim at the top of every
                    subagent prompt by the workflow orchestrator. This is the
                    only per-country channel that reaches the agents: the
                    runner starts `claude -p ISO --agent workflow-orchestrator`
                    and the orchestrator reads reference/country_profiles.json.

Merged by py/build_country_profiles.py into ./reference/country_profiles.json.
See docs/technical/nepal-integration-plan.md.
"""

PROFILES_PILOT = {
    "NPL": {
        "name": "Nepal", "iso2": "NP", "subregion": "South Asia",
        "adm1": ["Koshi", "Madhesh", "Bagmati", "Gandaki", "Lumbini", "Karnali",
                 "Sudurpashchim"],
        "adm1_legacy": {
            "zones_pre_2015": ["Mechi", "Koshi", "Sagarmatha", "Janakpur", "Bagmati",
                               "Narayani", "Gandaki", "Lumbini", "Dhaulagiri", "Rapti",
                               "Karnali", "Bheri", "Seti", "Mahakali"],
            "development_regions_pre_2015": ["Eastern", "Central", "Western",
                                             "Mid-Western", "Far-Western"],
            "numbered_provinces_2015_2023": ["Province 1 (= Koshi)", "Province 2 (= Madhesh)",
                                             "Province 5 (= Lumbini)"],
        },
        "major_cities": ["Kathmandu", "Lalitpur", "Bhaktapur", "Birgunj", "Biratnagar",
                         "Pokhara", "Nepalgunj", "Dhangadhi", "Butwal", "Janakpur"],
        "neighbors": ["IND", "CHN"],
        "search_languages": ["ne", "en"],
        "disease_terms": ["cholera", "हैजा", "acute watery diarrhoea",
                          "झाडापखाला (diarrhoea/AGE: context only, never counted as cholera)",
                          "acute gastroenteritis (AGE: context only, never counted as cholera)"],
        "health_domains": ["edcd.gov.np", "dohs.gov.np", "mohp.gov.np", "nphl.gov.np",
                           "nhrc.gov.np"],
        "season": ("Monsoon Jun-Sep; Kathmandu Valley urban outbreaks (2016, 2022, 2024); "
                   "Terai (Madhesh, Lumbini: Kapilvastu 2021, Birgunj 2025) and far-west hill "
                   "outbreaks; 1990-91 major epidemic (WHO annual 23,888 and 30,648)"),
        "regional_sources": [
            "WHO SEARO (searo.who.int) and WHO Nepal country office (who.int/nepal)",
            "WHO Weekly Epidemiological Record annual cholera reports (iris.who.int)",
            "WHO multi-country cholera situation reports / epidemiological updates",
            "EDCD EWARS weekly bulletins and outbreak situation reports (edcd.gov.np; "
            "mirrored on ReliefWeb - use py/reliefweb.py)",
            "DoHS annual reports (dohs.gov.np; indexed by Nepali fiscal year)",
            "IFRC GO / DREF operations (go.ifrc.org)",
            "Nepal Health Research Council journals (jnhrc.com.np, elibrary.nhrc.gov.np)",
        ],
        "archive_hints": [
            "NHRC eLibrary (elibrary.nhrc.gov.np)",
            "Gorkhapatra and Kathmandu Post archives",
            "WHO SEARO archives and WHO IRIS (WER 1970-2000 cholera tables)",
            "Wayback Machine for edcd.gov.np and dohs.gov.np (both refused connections in testing)",
        ],
        "country_notes": [
            "PILOT COUNTRY (Nepal, NPL). Outside the 40 MOSAIC countries; processed only "
            "because it was named. These rules override the general ones where they differ.",
            "LOCATIONS: use SEAR::NPL (national), SEAR::NPL::<Province>[::<District>]. AFR:: is "
            "rejected for Nepal. py/add_observation.py writes the [NPL-PILOT] tag into "
            "processing_notes for you; py/validate_quality.py errors on any AI row without it.",
            "GAP FILES: Nepal's gap files are in ./reference/pilot/ (same file names as "
            "./reference/effective_surveillance_*.csv), not in the shared 40-country files.",
            "CASE DEFINITIONS: suspected/AWD outbreak totals go in sCh; culture- or "
            "RDT-confirmed counts go in cCh. NEVER put acute gastroenteritis (AGE, "
            "झाडापखाला) or general diarrhoea totals in sCh or cCh: Nepal reports AGE "
            "(about 7-8k cases a year at sentinel sites) separately from cholera.",
            "WHO/WER ANNUAL FIGURES: quote the case definition the source used. Some WHO "
            "annual totals for Nepal are confirmed-only (2016: 169 = the confirmed count; "
            "2023: 7; 2024: 95). If a WHO/WER figure is confirmed-only, enter it as cCh, not sCh.",
            "EWARS: EWARS weekly counts come from sentinel hospitals (40 in 2015, 118 in "
            "2022) and are lab-confirmed. Record them as cCh at SEAR::NPL and say 'sentinel "
            "hospitals' in processing_notes.",
            "NO ZERO ROWS: do not add zero rows for Nepal (add-zero and sCh=0 are refused). "
            "Record years or weeks with no cases reported, and sentinel zero weeks, in "
            "./data/NPL/cholera_presence_ai.csv or your search log instead. Agent 3 "
            "(zero-transmission) documents absence evidence in its log only.",
            "BIKRAM SAMBAT DATES: convert every BS date and fiscal year to Gregorian "
            "(fiscal year 20XX/YY starts on Shrawan 1, about mid-July; e.g. FY 2077/78 = "
            "mid-Jul 2020 to mid-Jul 2021) and quote the original in processing_notes.",
            "COUNT TYPES: the weekly builder uses only rows whose count type is recorded in "
            "./reference/count_basis/NPL.csv. Read it before searching; many entries are "
            "'provisional' or 'unknown'. Agent 7 adds an entry (source_key AI:<metadata "
            "Index>) for any AI source that reports WHO/WER annual figures, with a quote as "
            "evidence, and upgrades 'provisional' entries it can verify.",
            "HELD-OUT YEARS: the gap files count every row as coverage, but these years have "
            "NO usable national suspected count as of 2026-11-20 (see "
            "./data/NPL/builder_holdout.csv and ./data/NPL/cholera_period_totals_NPL.csv): "
            "2007-2009, 2011-2015, 2017-2020 (plus the true gap 1999-2006). The 2011-2014 JHU "
            "figures (collection 21301) look like AGE; 2012, 2016 and 2023-2024 WHO annual "
            "figures are confirmed-only. Treat these years as gaps for suspected cases.",
            "SOURCES: ./reference/priority_sources_pilot.txt lists Nepal's pre-authorized "
            "domains (in addition to ./reference/priority_sources.txt). Use the profile's "
            "regional_sources in place of WHO AFRO / Africa CDC and archive_hints in place "
            "of francophone/lusophone archives.",
            "UNREACHABLE SITES: edcd.gov.np and dohs.gov.np refused connections in testing. "
            "Use the Wayback Machine and ReliefWeb (py/reliefweb.py; may need "
            "SSL_CERT_FILE=/etc/ssl/cert.pem).",
            "PRIORITIES: (1) a documented count type for every source-year 2018-2025; "
            "(2) the 2021 conflict: 2,023 (Kapilvastu, JHU 21541) vs WHO annual 1,609; "
            "(3) the 2024 conflict: WHO dashboard 360 vs 95 confirmed; (4) suspected totals "
            "for the EWARS years 2020-2022; (5) gaps 1999-2006 (Agents 1 and 4) and 1982-88 "
            "(Agent 4: NHRC eLibrary, Gorkhapatra, WHO SEARO archives).",
        ],
    },
}
