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
    "BGD": {
        "name": "Bangladesh", "iso2": "BD", "subregion": "South Asia",
        "adm1": ["Barishal", "Chattogram", "Dhaka", "Khulna", "Mymensingh", "Rajshahi",
                 "Rangpur", "Sylhet"],
        "adm1_legacy": {
            "spellings_pre_2018": ["Barisal (= Barishal)", "Chittagong (= Chattogram)",
                                   "Chittagong Division (= Chattogram)"],
            "divisions_before_splits": ["Dhaka (included Mymensingh until 2015)",
                                        "Rajshahi (included Rangpur until 2010)",
                                        "Chittagong (included Sylhet until 1995)",
                                        "Khulna (included Barisal until 1993)"],
            "pre_1971": ["East Pakistan (WHO reported 'Pakistan' as one country)",
                         "Dacca (= Dhaka)"],
        },
        "major_cities": ["Dhaka", "Chattogram", "Khulna", "Rajshahi", "Sylhet", "Barishal",
                         "Rangpur", "Mymensingh", "Cox's Bazar", "Narayanganj", "Gazipur",
                         "Cumilla"],
        "neighbors": ["IND", "MMR"],
        "search_languages": ["bn", "en"],
        "disease_terms": ["cholera", "কলেরা",
                          "ডায়রিয়া (diarrhoea: context only, never counted as cholera)",
                          "acute watery diarrhoea (AWD: not cholera unless the source says cholera)",
                          "Vibrio cholerae O1 / O139 (laboratory)"],
        "health_domains": ["dghs.gov.bd", "iedcr.gov.bd", "icddrb.org", "mohfw.gov.bd"],
        "season": ("Hyperendemic, bimodal: pre-monsoon peak Mar-May and post-monsoon peak "
                   "Sep-Dec. Flood-associated surges 1988, 1998, 2004, 2007, 2022 (Sylhet), "
                   "2024 (Feni). O139 Bengal emerged 1992-93. Rohingya camps in Cox's Bazar "
                   "since Aug 2017 (~0.9-1 M people)"),
        "regional_sources": [
            "WHO SEARO (searo.who.int) and WHO Bangladesh country office (who.int/bangladesh)",
            "WHO Weekly Epidemiological Record annual cholera reports incl. 2025 (iris.who.int, "
            "cdn.who.int) - Table 3 gives tested/positive; read the case definition each year",
            "WHO Cox's Bazar EWARS weekly bulletins and ISCG situation reports (cdn.who.int, "
            "rohingyaresponse.org) - camp data, sub-national only",
            "WHO multi-country cholera situation reports / epidemiological updates",
            "icddr,b Health and Science Bulletin, Glimpse, annual reports (icddrb.org, "
            "dspace.icddrb.org); Journal of Health, Population and Nutrition (JHPN)",
            "IEDCR outbreak investigation reports and the National Cholera Control Plan "
            "2019-2030 (iedcr.gov.bd, dghs.gov.bd)",
            "DGHS Health Bulletins (annual) and emergency-operations daily reports",
            "IFRC GO / DREF operations (go.ifrc.org); ReliefWeb - use py/reliefweb.py",
        ],
        "archive_hints": [
            "Cholera Research Laboratory (Dacca) annual reports and Matlab trial reports, "
            "1960-1978 (dspace.icddrb.org)",
            "icddr,b library and DSpace repository; Bangladesh Medical Research Council Bulletin",
            "WHO SEARO archives and WHO IRIS (WER 1970-2000 cholera tables)",
            "The Daily Star and Prothom Alo archives",
            "Wayback Machine for old.dghs.gov.bd and iedcr.gov.bd (refused connections or "
            "need a login in testing)",
        ],
        "country_notes": [
            "PILOT COUNTRY (Bangladesh, BGD). Outside the 40 MOSAIC countries; processed only "
            "because it was named. These rules override the general ones where they differ. "
            "Plan: docs/technical/bangladesh-pilot-plan.md.",
            "WHAT MATTERS: Bangladesh has almost no national count of suspected cholera. Most "
            "of its numbers are diarrhoea, sentinel samples or camp counts. The goal is to "
            "record what each number counts, not to maximise coverage. A wrong national "
            "number is worse than none.",
            "FIVE STREAMS - classify every figure before entering it: (1) NATIONAL "
            "NOTIFICATIONS to WHO (WER annual tables; 1971-2000 small and very incomplete); "
            "(2) SENTINEL SURVEILLANCE (icddr,b 2% systematic sample at Dhaka hospital, "
            "Matlab, the IEDCR/icddr,b national cholera surveillance at ~22 hospitals from "
            "2014, later 20 suspected cases sampled per site per week) - WHO's annual totals "
            "since 2023 (23,369 / 24,758 / 22,709) come from this stream: diarrhoea patients "
            "enrolled, not national cholera; (3) COX'S BAZAR CAMPS (WHO/ISCG EWARS; the WHO "
            "dashboard row 'Bangladesh' is the camps only); (4) DIARRHOEA/AWD totals (DGHS, "
            "IEDCR, flood reports) - NOT cholera; (5) BURDEN ESTIMATES (e.g. ~110,000 a year, "
            "Ali et al. 2015) - model output, never an observation. Also: DGHS DHIS2 / Health "
            "Bulletin counts coded 'cholera' (ICD-10 A00) are a clinical label (count type "
            "mixed), and O139 was reported separately in 1992-93.",
            "LOCATIONS: SEAR::BGD (national), SEAR::BGD::<Division>[::<District>]. AFR:: is "
            "rejected. py/add_observation.py writes the [BGD-PILOT] tag for you; "
            "py/validate_quality.py errors on any AI row without it. Cox's Bazar camps: "
            "SEAR::BGD::Chattogram::Cox's Bazar (JHU's 'Chittagong Division::Cox's Bazar' and "
            "'Chattogram::BD-11' are the same place; JHU 21127 at BD-11 is camp AWD, not "
            "cholera). Matlab is in Chandpur district: SEAR::BGD::Chattogram::Chandpur (JHU "
            "uses BD-09). icddr,b Dhaka hospital: SEAR::BGD::Dhaka::Dhaka.",
            "NEVER AT SEAR::BGD: camp counts, sentinel-site counts, one-hospital counts. Put "
            "them at the site's own location. If a source gives only a national total from "
            "sentinel sites, enter it at SEAR::BGD and say 'sentinel' in processing_notes; "
            "Agent 7 records its coverage. Never scale a sample count up to a national figure.",
            "CASE DEFINITIONS: sCh = suspected cholera as the source defines it; cCh = culture-, "
            "PCR- or RDT-positive cholera (say which in processing_notes). NEVER put diarrhoea, "
            "AWD or AGE totals in sCh or cCh unless the source itself calls them cholera. Quote "
            "the source's case definition for every national figure.",
            "SENTINEL POSITIVITY: tested/positive counts by site go in "
            "./data/BGD/sentinel_positivity_ai.csv (columns: Location, TL, TR, site, tested, "
            "positive, test_method, serogroup, sampling, source_index, source, "
            "processing_notes), not in cholera_data_ai.csv. Register the source first with "
            "py/add_observation.py register-source. Write with Python's csv module; never "
            "hand-edit. The validator checks it. Matlab (population-based) first.",
            "COUNT TYPES: ./reference/count_basis/BGD.csv records what every national source-"
            "year counts and its coverage (national / subset / sample). strict_basis is on: "
            "the weekly builder uses NO national value, AI rows included, until it has an "
            "entry there. Agent 7 adds an AI:<metadata Index> entry with a quoted case "
            "definition for every national AI row with a count. Read the table before "
            "searching: at set-up every national source-year is held out.",
            "NO ZERO ROWS: Bangladesh is hyperendemic. add-zero and sCh=0 are refused. Do not "
            "record absence anywhere.",
            "AGENT 3 IS REPURPOSED: do not validate zero transmission. Map the surveillance "
            "system year by year 1970-2025: which streams existed (WHO notification, icddr,b "
            "2% surveillance, Matlab HDSS, national cholera surveillance 2014-, IEDCR AWD/"
            "EWARS, Cox's Bazar EWARS from 2017, DHIS2), their case definitions, sentinel "
            "site lists, sampling fractions and test methods. Agent 3 writes no rows to "
            "cholera_data_ai.csv; its search log is the evidence for Agent 7's count-basis "
            "entries.",
            "GAP FILES: Bangladesh's gap files are in ./reference/pilot/, not the shared "
            "40-country files. Coverage % there counts any row and is not a measure of success.",
            "SOURCES: ./reference/priority_sources_pilot.txt lists Bangladesh's pre-authorized "
            "domains (in addition to ./reference/priority_sources.txt). Use the profile's "
            "regional_sources in place of WHO AFRO / Africa CDC and archive_hints in place of "
            "francophone/lusophone archives. ReliefWeb via py/reliefweb.py (may need "
            "SSL_CERT_FILE=/etc/ssl/cert.pem).",
            "PRIORITIES: (1) what JHU 429's 2018-2022 national figures count (566 / 503 / 212 / "
            "477 / 1,191; probably sentinel laboratory positives); (2) the WER case definition "
            "for each year with a national figure, 1971-2000 and 2023-2025 (Table 3 "
            "tested/positive, age split); (3) any national suspected cholera count for "
            "2001-2022 (DGHS Health Bulletins, IEDCR); (4) sentinel positivity series, Matlab "
            "first; (5) Cox's Bazar weekly series 2017-2026 at sub-national level. Do not "
            "spend the query budget on single-hospital clinical studies.",
            "AGENT 7 TRIPWIRES: retype any year typed national suspected where the source "
            "shows an under-5 share above 30% or tested / cases above 50% (signatures of "
            "sentinel or diarrhoea data); flag any national suspected year below 1% of the "
            "~110,000 burden estimate as incomplete. search_report.txt must include a "
            "1970-2025 table: stream(s) present, what each counts, with quoted source text.",
        ],
    },
}
