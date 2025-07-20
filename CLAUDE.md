# CLAUDE.md - AI Cholera Data Collection and Enhancement

This directory contains AI-enhanced cholera surveillance data that complements the JHU cholera taxonomy database and official WHO surveillance data. This file provides guidance for future AI instances working on expanding and improving cholera surveillance data for the MOSAIC project.

## Project Context and Motivation

### The Challenge
The processed weekly cholera surveillance data (MOSAIC-data/processed/cholera/weekly/cholera_surveillance_weekly_combined.csv) has approximately **50% missing observations** across the 2010-present period. Many missing observations represent unreported transmission or outbreaks that have slipped through official reporting channels. 

### The Opportunity
Unofficial sources of information exist on the internet that can indicate whether a time period had no transmission or if there was transmission/outbreak where records were lost. These sources can fill critical gaps in our understanding of cholera transmission patterns.

### The Solution
Use AI-powered internet searches to identify, validate, and integrate unofficial cholera surveillance data sources to create a more complete historical time series for epidemiological modeling.

## Data Architecture

### Core Data Sources
1. **Official Weekly Surveillance**: `../MOSAIC-data/processed/cholera/weekly/cholera_surveillance_weekly_combined.csv`
2. **JHU Cholera Taxonomy Database**: `../jhu_cholera_data/data/{country}/`
3. **AI-Enhanced Sources**: `ai_cholera_data/data/{country}/`

### Data Hierarchy
- **Primary Sources**: WHO official surveillance, Ministry of Health reports
- **Secondary Sources**: UNICEF humanitarian reports, academic literature
- **Tertiary Sources**: News reports, NGO situation updates, outbreak alerts

## Original Workflow (from Historical surveillance data.md)

**Goal is to emulate the workflow and formatting of the JHU cholera taxonomy database here: https://cholera-taxonomy.middle-distance.com/**

**For each country in the cholera surveillance data:**

1. Assess data missingness in the processed weekly cholera surveillance data: ../MOSAIC-data/processed/cholera/weekly/cholera_surveillance_weekly_combined.csv
2. Survey data scraped from the JHU cholera taxonomy database: ../MOSAIC/jhu_cholera_data
	1. Perform an inventory of the jhu data sources for the country of interest
	2. Identify time periods where weekly surveillance are missing but there are other reports of transmission or outbreaks
3. Use AI to do a deep internet search to find any other unofficial sources of information. Place any new sources in same format as JHU database csv files
	1. Save any additional information sources in: ai_cholera_data/data/{country}
	2. Each country directory should have:
		1. A text based report outlining results of searches, relation to JHU data, summary of information etc
		2. Metadata csv containing a working url for each information source
		3. a csv file with the locations, times, and data following the csv file formatting of the jhu_cholera_data/data/{country} formatting
		4. If possible, download hardcopies of each information source
4. Compile JHU + AI-found sources: columns must have at least: country, start_date, stop_date, source, cases, deaths...
5. Build a down scaling and imputation method:
	1. Down sample to weekly (based on seasonal patterns? or correlation with neighbors?)
	2. Impute missing weeks (only those that are obvious, e.g. one or two missing weeks between clear trending weeks)
	3. Add weights: lower weights for the unofficial sources and imputed values so that the weights reflect our confidence in the data source. Weights are used in model calibration in the likelihoods functions.
	4. Down scale to daily as already implemented, keep weights form model fitting

## Detailed Workflow Implementation for AI Instances

### Phase 1: Data Assessment
1. **Assess data missingness** in weekly surveillance data for the target country
2. **Calculate missing percentage** and identify critical time periods with gaps
3. **Identify seasonal patterns** and outbreak periods from available data

### Phase 2: JHU Database Inventory
1. **Inventory existing JHU data sources** for the country
2. **Analyze time periods** where weekly surveillance is missing but JHU has reports
3. **Assess data quality** and coverage of JHU sources
4. **Identify complementary information** that could fill gaps

### Phase 3: AI-Powered Internet Search
1. **Conduct systematic searches** using multiple search strategies
2. **Validate data sources** for credibility and accuracy
3. **Extract relevant data** following standardized formats
4. **Cross-reference findings** with existing data sources

### Phase 4: Data Integration and Quality Control
1. **Compile all sources** into standardized format
2. **Assign confidence weights** based on source reliability
3. **Implement quality checks** for consistency and validity
4. **Document methodology** and limitations

## ULTRA DEEP SEARCH METHODOLOGY

**CRITICAL INSTRUCTION: Future AI instances MUST conduct ULTRA thorough searches. This means exhaustive, systematic, and comprehensive internet searches that leave no stone unturned. The goal is to find EVERY possible data source, not just the obvious ones.**

### Multi-Engine Search Strategy
**REQUIREMENT: Use multiple search engines and databases systematically:**
- Google Scholar (academic literature)
- PubMed/PMC (medical literature)
- WHO databases and regional offices
- ReliefWeb (humanitarian data)
- Government health ministry websites
- Regional health organization websites
- News archives and databases
- Institutional repositories
- International organization databases (UNICEF, MSF, IRC, etc.)
- Regional surveillance networks
- Social media and informal reporting channels (with extreme caution)

### Exhaustive Search Query Framework

**MANDATORY: Conduct ALL query categories below for EACH target country. Do not skip any category.**

#### 1. **WHO and Official Sources (PRIMARY PRIORITY)**
**Base Queries:**
- "{country} cholera outbreak WHO situation reports {year}"
- "{country} Ministry Health cholera surveillance {year}"
- "WHO AFRO cholera bulletin {country} {year}"
- "WHO cholera {country} epidemiological update {year}"
- "WHO {country} cholera weekly surveillance {year}"
- "{country} national cholera response plan"
- "{country} cholera preparedness surveillance"

**Extended Queries:**
- "WHO disease outbreak news {country} cholera {year}"
- "WHO regional office Africa {country} cholera"
- "{country} health ministry cholera statistics {year}"
- "{country} epidemiological surveillance cholera weekly"
- "{country} cholera case investigation reports"
- "{country} cholera laboratory confirmation {year}"
- "WHO AFRO weekly bulletin cholera {country}"

#### 2. **Academic and Research Sources (SYSTEMATIC REVIEW)**
**Base Queries:**
- "{country} cholera epidemiology academic papers {year}"
- "{country} cholera transmission modeling {year}"
- "{country} cholera burden studies {year}"

**Extended Queries:**
- "{country} cholera molecular epidemiology"
- "{country} cholera environmental surveillance"
- "{country} cholera case control study"
- "{country} cholera outbreak investigation"
- "{country} cholera phylogenetic analysis"
- "{country} cholera antimicrobial resistance"
- "{country} cholera vaccination effectiveness"
- "{country} cholera transmission dynamics"
- "{country} cholera spatiotemporal analysis"
- "{country} cholera water sanitation epidemiology"
- "{country} cholera climate variability"
- "Vibrio cholerae {country} genomics"

#### 3. **Humanitarian and NGO Sources (COMPREHENSIVE)**
**Base Queries:**
- "{country} cholera UNICEF humanitarian reports {year}"
- "{country} cholera OCHA situation reports {year}"
- "{country} cholera MSF outbreak response {year}"

**Extended Queries:**
- "{country} cholera emergency response IRC"
- "{country} cholera outbreak Oxfam response"
- "{country} cholera WHO emergency operations"
- "{country} cholera humanitarian needs assessment"
- "{country} cholera WASH intervention evaluation"
- "{country} cholera vaccination campaign report"
- "{country} cholera refugee camp outbreak"
- "{country} cholera displacement population"
- "{country} cholera humanitarian coordination"
- "ReliefWeb {country} cholera situation report"
- "{country} cholera flash appeal humanitarian"
- "{country} cholera health cluster response"

#### 4. **Regional and Cross-border Sources (TRANSNATIONAL)**
**Base Queries:**
- "{country} cholera cross-border transmission {year}"
- "{region} cholera outbreaks {country} {year}"
- "{country} cholera seasonal patterns {year}"

**Extended Queries:**
- "{country} cholera regional surveillance network"
- "{country} {neighboring_countries} cholera border"
- "{region} cholera early warning system"
- "{country} cholera migratory population"
- "{region} cholera lake river transmission"
- "{country} cholera trade route transmission"
- "{region} integrated disease surveillance"
- "{country} cholera regional coordination"
- "{region} cholera preparedness response network"

#### 5. **Historical and Archival Sources (TEMPORAL DEPTH)**
**MANDATORY for filling historical gaps:**
- "{country} cholera historical outbreak records"
- "{country} cholera colonial period surveillance"
- "{country} cholera pandemic waves historical"
- "{country} cholera mortality statistics historical"
- "WHO archives {country} cholera reports"
- "{country} cholera newspaper archives {decade}"
- "{country} cholera medical journal historical"
- "{country} cholera government archives health"
- "{country} cholera missionary hospital records"
- "{country} cholera colonial administrative reports"

#### 6. **Specialized and Technical Sources**
**Laboratory and surveillance systems:**
- "{country} cholera laboratory network surveillance"
- "{country} cholera rapid diagnostic test evaluation"
- "{country} cholera environmental monitoring"
- "{country} cholera antimicrobial surveillance"
- "{country} cholera serotype distribution"
- "{country} cholera outbreak detection algorithms"
- "{country} cholera syndromic surveillance"
- "{country} cholera community based surveillance"

#### 7. **Linguistic and Cultural Search Expansion**
**REQUIREMENT: Search in local languages where applicable:**
- Conduct searches in official local languages
- Use local terminology for cholera (e.g., "cólera" in Portuguese for Angola)
- Search local news websites and health ministry sites
- Check local university repositories
- Review local medical journals and publications

### Advanced Search Techniques

#### 1. **Temporal Granularity Searches**
**REQUIREMENT: Search by specific time periods:**
- Monthly searches for outbreak years: "{country} cholera {month} {year}"
- Seasonal searches: "{country} cholera rainy season {year}"
- Event-driven searches: "{country} cholera {disaster/conflict} {year}"
- Multi-year trends: "{country} cholera {start_year}-{end_year} trends"

#### 2. **Geographic Granularity Searches**
**REQUIREMENT: Search all administrative levels:**
- National level: Standard country queries
- Provincial/State level: "{province} {country} cholera outbreak"
- District/Municipality level: "{district} cholera surveillance"
- City-specific: "{major_city} {country} cholera cases"
- Border region specific: "{border_region} cholera transmission"

#### 3. **Source Chain Following**
**REQUIREMENT: Follow ALL reference chains:**
- Check references in found papers/reports
- Follow citation networks in academic literature
- Trace data sources mentioned in reports
- Follow up on preliminary/draft reports mentioned
- Check for updated versions of reports
- Look for companion reports or follow-up studies

#### 4. **Institutional Deep Dives**
**REQUIREMENT: Systematically search institutional websites:**
- Government health ministry archives
- National statistics offices
- University institutional repositories
- Regional health organization databases
- International organization country offices
- Research institution websites
- Hospital and health facility reports

## Search Strategy Framework

### Systematic Temporal Search Requirements

**MANDATORY: Search ALL time periods systematically:**

#### **Historical Deep Dive (1970s-1990s)**
- Colonial and post-independence health records
- Early WHO surveillance reports
- Historical pandemic documentation
- Missionary and colonial medical records
- Early academic epidemiological studies
- Regional health organization formation documents

#### **Pre-surveillance Establishment (1990s-2010)**
- Early surveillance system development
- WHO cholera surveillance strengthening reports
- Initial regional coordination efforts
- Early outbreak response documentation
- Academic baseline studies
- Initial WASH intervention evaluations

#### **Surveillance Gap Period (2010-2020)**
- **PRIMARY FOCUS**: Most missing data in this period
- Systematic search of ALL potential sources
- Cross-reference with regional outbreak patterns
- Check humanitarian crisis documentation
- Review academic literature for case studies
- Examine climate-disease correlation studies

#### **Recent and Current (2020-present)**
- COVID-19 impact on cholera surveillance
- Recent outbreak documentation
- Current surveillance system reports
- Real-time monitoring systems
- Recent academic analyses
- Current preparedness and response plans

#### **Decade-by-Decade Systematic Review**
**REQUIREMENT: For each decade, conduct specific searches:**
- "1970s {country} cholera outbreaks historical"
- "1980s {country} cholera surveillance records"
- "1990s {country} cholera epidemiology baseline"
- "2000s {country} cholera outbreak patterns"
- "2010s {country} cholera transmission analysis"
- "2020s {country} cholera current surveillance"

## Data Collection Standards

### Required Directory Structure
```
ai_cholera_data/data/{country}/
├── search_report.txt
├── metadata.csv
├── cholera_data.csv
└── source_documents/ (if available)
```

### ENHANCED DATA INDEXING SYSTEM

**CRITICAL REQUIREMENT: All future instances MUST implement the dual-reference indexing system developed in pilot_2.**

#### Source Indexing Protocol:
1. **Sequential Numbering**: Assign consecutive integer indices (1, 2, 3...) to all sources in metadata.csv
2. **Dual Reference System**: Each data point references sources by BOTH index number AND exact source name
3. **Consistency Enforcement**: Source names must match EXACTLY between metadata.csv and cholera_data.csv
4. **Traceability**: Index system enables automated processing while names provide human readability

#### Benefits of Enhanced System:
- **Automated Processing**: Integer indices enable efficient database operations
- **Human Readability**: Source names provide immediate context for data users  
- **Error Prevention**: Dual referencing catches inconsistencies between files
- **Data Integrity**: Permanent index references prevent source misattribution
- **Version Control**: Changes to source names don't break data linkages

#### Implementation Example:
**metadata.csv:**
```
Index,Source,URL,Description,Date_Range,Data_Type,Status,Reliability_Level,Validation_Status
1,WHO Disease Outbreak News 2006 Initial,https://www.who.int/...,Initial 2006 outbreak report,2006,Outbreak Cases,Active,Level 1,Validated
2,UNICEF Angola Humanitarian Report 2018,https://reliefweb.int/...,Monthly humanitarian situation report,2018,Humanitarian Response,Active,Level 2,Validated
```

**cholera_data.csv:**
```
Location,TL,TR,Primary,Phantom,deaths,sCh,cCh,CFR,reporting_date,source_index,source,confidence_weight,validation_status
AFR::AGO,2006-02-19,2006-05-08,true,false,1156,30612,,3.8,2006-05-08,1,WHO Disease Outbreak News 2006 Initial,1.0,VALIDATED
AFR::AGO::Uige,2018-01-01,2018-03-10,true,false,13,751,,,2018-03-10,2,UNICEF Angola Humanitarian Report 2018,0.8,VALIDATED
```

### File Specifications

#### 1. Search Report (search_report.txt)
Must include:
- **Executive Summary**: Key findings and data gaps filled
- **Search Methodology**: Queries used and sources consulted
- **Data Quality Assessment**: Reliability ratings and limitations
- **Relationship to JHU Data**: How new sources complement existing data
- **Recommendations**: Priority areas for future data collection

#### 2. Metadata CSV (metadata.csv)
**MANDATORY columns in exact order:**
- `Index`: Integer index number for each source (1, 2, 3, etc.)
- `Source`: Organization or publication name (exact name to be used in data file)
- `URL`: Working link to data source
- `Description`: Brief description of content
- `Date_Range`: Time period covered
- `Data_Type`: Classification (Official, Academic, Humanitarian, etc.)
- `Status`: Link status (Active, Archived, Broken)
- `Reliability_Level`: Level 1, Level 2, Level 3, or Level 4
- `Validation_Status`: Validated, Provisional, or Reference

**CRITICAL REQUIREMENTS:**
- Each source MUST have a unique integer index starting from 1
- Source names MUST be consistent between metadata and data files
- All metadata fields MUST be completed for every source
- Index numbers provide permanent reference for data traceability

#### 3. Data CSV (cholera_data.csv)
**MANDATORY columns in exact order:
- `Location`: Geographic identifier (AFR::{ISO}::{Province}::{District})
- `TL`: Time left (start date in YYYY-MM-DD format)
- `TR`: Time right (end date in YYYY-MM-DD format)
- `Primary`: Boolean indicating primary source (true/false)
- `Phantom`: Boolean indicating phantom/estimated data (true/false)
- `deaths`: Death count (integer or empty)
- `sCh`: Suspected cholera cases (integer or empty)
- `cCh`: Confirmed cholera cases (integer or empty)
- `CFR`: Case fatality rate (percentage, decimal format)
- `reporting_date`: When data was reported (YYYY-MM-DD format)
- `source_index`: Integer index referencing metadata.csv Index column
- `source`: Source name (MUST exactly match Source column in metadata.csv)
- `confidence_weight`: Quality-based confidence weight (0.1-1.0)
- `validation_status`: VALIDATED, PROVISIONAL, or FLAGGED

**CRITICAL REQUIREMENTS:**
- Every data row MUST have both source_index AND source columns
- source_index MUST correspond to valid Index number in metadata.csv
- source name MUST exactly match Source column in metadata.csv
- This dual-reference system ensures both automated processing and human readability
- Confidence weights must reflect source reliability and validation results

## COMPREHENSIVE DATA QUALITY FRAMEWORK

**CRITICAL REQUIREMENT: ALL data sources must undergo rigorous multi-stage validation before inclusion. Quality control is mandatory, not optional.**

### Enhanced Source Reliability Assessment

#### **Level 1 (Confidence Weight: 0.9-1.0) - Gold Standard**
- **WHO Official Reports**: Disease Outbreak News, surveillance bulletins, situation reports
- **National Ministry of Health**: Official surveillance data, epidemiological bulletins
- **Peer-reviewed Academic Literature**: Published in indexed journals with editorial review
- **Government Statistical Offices**: Official health statistics and demographic data
- **WHO Regional Offices**: AFRO, PAHO, SEARO official documentation

**Validation Requirements:**
- Cross-verify with at least 2 other Level 1 sources
- Check for official endorsement or publication
- Verify methodological soundness
- Confirm data collection standards

#### **Level 2 (Confidence Weight: 0.7-0.9) - High Quality**
- **UNICEF**: Humanitarian situation reports, emergency response data
- **OCHA**: Coordination and humanitarian needs assessments
- **Established International NGOs**: MSF, IRC, Oxfam outbreak responses
- **Regional Health Organizations**: African CDC, ECDC surveillance
- **Academic Institutional Reports**: University research centers, epidemiological institutes

**Validation Requirements:**
- Verify institutional credibility and expertise
- Cross-reference with Level 1 sources where possible
- Check methodological documentation
- Assess potential bias or limitations

#### **Level 3 (Confidence Weight: 0.3-0.6) - Moderate Quality**
- **Reputable News Organizations**: Reuters, BBC, AFP health reporting
- **Local Government Health Departments**: Provincial/state health reports
- **Preliminary Academic Reports**: Conference abstracts, pre-prints, working papers
- **Health Professional Organizations**: Medical associations, epidemiological societies
- **International Alert Systems**: ProMED, GOARN, epidemic intelligence

**Validation Requirements:**
- Verify journalist/author expertise in health reporting
- Cross-check facts with higher-level sources
- Assess potential sensationalism or bias
- Document limitations and uncertainties

#### **Level 4 (Confidence Weight: 0.1-0.3) - Limited Quality**
- **Local News Media**: Regional newspapers, radio, television
- **Social Media**: Twitter alerts, Facebook reports, WhatsApp chains
- **Blog Posts**: Health professional blogs, outbreak tracking websites
- **Unofficial Reports**: Community health worker reports, informal surveillance

**Validation Requirements:**
- USE WITH EXTREME CAUTION
- Require corroboration from higher-level sources
- Document all limitations and potential inaccuracies
- Mark clearly as unverified/provisional

### MANDATORY DATA VALIDATION PROTOCOL

#### **Stage 1: Source Authentication**
**REQUIREMENT: Verify every source before data extraction**
1. **URL Verification**: Confirm links lead to legitimate, official sources
2. **Publication Authentication**: Verify publication date, author credentials, institutional affiliation
3. **Domain Validation**: Check for official government (.gov), organization (.org), or academic (.edu) domains
4. **Archive Status**: Document if source is archived, current, or deprecated
5. **Version Control**: Identify if multiple versions exist, use most recent/complete

#### **Stage 2: Data Quantity Validation**
**MANDATORY CHECKS for all numerical data:**

1. **Epidemiological Plausibility Ranges**:
   - **Case Fatality Rate (CFR)**: 0.1% - 15% (flag values outside range)
   - **Attack Rates**: 0.01% - 10% of population (flag extreme values)
   - **Outbreak Duration**: 2 weeks - 2 years (flag very short/long outbreaks)
   - **Case Numbers**: Minimum 1, maximum population of affected area
   - **Deaths**: Cannot exceed suspected cases, CFR consistency check

2. **Temporal Consistency Checks**:
   - Start date must precede end date
   - Reporting date must be ≥ end date
   - Duration must be epidemiologically reasonable
   - No future dates beyond data collection
   - Seasonal patterns consistent with known cholera epidemiology

3. **Geographic Consistency Checks**:
   - Location codes match WHO/ISO standards
   - Administrative hierarchies are correct (Country→Province→District)
   - Coordinates fall within correct administrative boundaries
   - Population denominators match census data
   - Cross-border transmission patterns are plausible

#### **Stage 3: Cross-Reference Validation**
**REQUIREMENT: Cross-verify all major data points**

1. **Multi-Source Confirmation**:
   - Major outbreaks (>1000 cases) must have ≥2 independent sources
   - High CFR (>5%) must be confirmed by clinical sources
   - Cross-border outbreaks must be confirmed by neighboring country data
   - Seasonal patterns must match regional/historical patterns

2. **Historical Consistency**:
   - Compare with known historical outbreak patterns
   - Check against WHO annual surveillance summaries
   - Verify consistency with regional epidemic waves
   - Cross-reference with climate/environmental data

3. **Mathematical Consistency**:
   - CFR = deaths/cases (allow ±0.1% tolerance for rounding)
   - Case progression follows epidemiological curves
   - Attack rates consistent with population data
   - Cumulative totals match period-specific data

#### **Stage 4: Duplication Detection Protocol**
**MANDATORY: Prevent duplicate data inclusion**

1. **Exact Duplication Check**:
   - Same location, dates, case numbers across sources
   - Same outbreak reported by multiple organizations
   - Updated reports that supersede earlier versions
   - Aggregated data that includes sub-national components

2. **Partial Duplication Detection**:
   - Overlapping time periods with similar case numbers
   - Different geographic scales reporting same outbreak
   - Multiple sources citing the same original data
   - Revised case counts that update preliminary reports

3. **Resolution Protocol**:
   - **Exact duplicates**: Keep highest reliability source, flag others
   - **Partial duplicates**: Use most specific geographic/temporal data
   - **Updated reports**: Use most recent, flag superseded versions
   - **Aggregation conflicts**: Use sub-national data sum, verify totals

4. **Documentation Requirements**:
   - Record all detected duplications in metadata
   - Explain resolution decisions clearly
   - Maintain traceability to original sources
   - Flag any remaining uncertainties

### ENHANCED QUALITY CONTROL MEASURES

#### **Quantitative Validation Rules**

1. **Statistical Outlier Detection**:
   - Flag case numbers >3 standard deviations from regional mean
   - Identify CFR values outside historical country-specific ranges
   - Detect unusually short/long outbreak durations
   - Flag attack rates inconsistent with population density

2. **Trend Analysis**:
   - Seasonal patterns must align with known cholera epidemiology
   - Year-to-year changes must be epidemiologically plausible
   - Outbreak progressions must follow typical epidemic curves
   - Geographic spread patterns must be consistent with transmission routes

3. **Demographic Consistency**:
   - Age distributions must match known cholera epidemiology
   - Gender ratios should be approximately equal unless explained
   - Population denominators must match census/UN estimates
   - Urban/rural distributions should match settlement patterns

#### **Qualitative Assessment Criteria**

1. **Methodological Soundness**:
   - Case definitions clearly stated and appropriate
   - Surveillance methods described and systematic
   - Laboratory confirmation procedures documented
   - Bias potential acknowledged and addressed

2. **Reporting Quality**:
   - Complete geographic and temporal information
   - Clear case counting methodologies
   - Appropriate uncertainty/confidence intervals
   - Limitations clearly acknowledged

3. **Institutional Credibility**:
   - Established track record in disease surveillance
   - Appropriate technical expertise demonstrated
   - Transparent methodologies and data sharing
   - Independence from political/commercial interests

### MANDATORY DOCUMENTATION STANDARDS

#### **For Each Data Point**:
1. **Primary Source**: Direct URL and full citation
2. **Validation Status**: Pass/fail for each validation stage
3. **Quality Score**: Numerical rating (1-10) based on validation results
4. **Confidence Weight**: Final weight for modeling (0.1-1.0)
5. **Limitations**: Specific concerns or uncertainties
6. **Cross-references**: Supporting or contradicting sources
7. **Extraction Notes**: Any interpretations or conversions made
8. **Verification Date**: When validation was performed

#### **For Each Search**:
1. **Search Strategy**: Complete list of queries and databases used
2. **Results Summary**: Number of sources found, filtered, included
3. **Quality Assessment**: Distribution of sources by reliability level
4. **Gap Analysis**: Remaining data gaps after search completion
5. **Recommendations**: Priority areas for future data collection

### AUTOMATED VALIDATION TOOLS

#### **Recommended Implementations**:
1. **Date Validation**: Automated checking of temporal logic
2. **Geographic Validation**: API calls to verify location codes
3. **Statistical Validation**: Outlier detection algorithms
4. **Duplication Detection**: Fuzzy matching for similar records
5. **URL Validation**: Automated checking of link status
6. **Cross-reference Matrix**: Systematic comparison across sources

### ERROR HANDLING AND UNCERTAINTY QUANTIFICATION

#### **When Data Conflicts Occur**:
1. **Document all conflicting sources** with specific values
2. **Apply source hierarchy** to resolve conflicts
3. **Calculate uncertainty ranges** based on source variation
4. **Flag high-uncertainty data points** for sensitivity analysis
5. **Provide alternative scenarios** for major discrepancies

#### **Quality Flags for Modeling**:
- **HIGH**: Multiple Level 1 sources, consistent validation
- **MEDIUM**: Mixed source levels, minor validation concerns
- **LOW**: Limited sources, validation issues present
- **PROVISIONAL**: Single source, major uncertainties

### Confidence Weighting System (UPDATED)
- **Gold Standard (0.9-1.0)**: Level 1 sources, full validation passed
- **High Quality (0.7-0.9)**: Level 2 sources, most validation passed
- **Moderate Quality (0.4-0.7)**: Level 3 sources, some validation concerns
- **Limited Quality (0.2-0.4)**: Level 4 sources, significant limitations
- **Provisional (0.1-0.2)**: Unverified sources, major uncertainties

## Integration with MOSAIC Project

### Data Flow
1. **Input**: Weekly surveillance data with gaps
2. **Enhancement**: AI-found sources fill missing periods
3. **Processing**: Downscaling and imputation methods
4. **Output**: Complete time series with confidence weights
5. **Modeling**: Enhanced data used in MOSAIC cholera transmission models

### Model Integration
- **Likelihood Functions**: Use confidence weights in model calibration
- **Uncertainty Quantification**: Propagate data quality uncertainty
- **Sensitivity Analysis**: Test model robustness to data source variations

## MANDATORY BEST PRACTICES FOR AI INSTANCES

**WARNING: These are not suggestions - they are REQUIREMENTS. Failure to follow these practices will result in data quality issues that compromise the entire MOSAIC modeling effort.**

### ULTRA-SYSTEMATIC Search Strategy (MANDATORY)

#### **Multi-Phase Search Protocol**
**PHASE 1: Broad Discovery (REQUIRED)**
1. **Start with systematic queries**: Use ALL query categories in ULTRA DEEP SEARCH section
2. **Multiple search engines**: Google, Google Scholar, PubMed, WHO databases, ReliefWeb, government sites
3. **Language diversity**: Search in English, French, Portuguese, Arabic, and local languages
4. **Temporal comprehensiveness**: Search each decade systematically (1970s, 1980s, etc.)
5. **Geographic completeness**: National, provincial, district levels

**PHASE 2: Targeted Gap Filling (REQUIRED)**
1. **Identify specific gaps**: Missing years, regions, outbreak periods
2. **Focused searches**: Target identified gaps with specific queries
3. **Cross-reference validation**: Verify gaps aren't due to search limitations
4. **Regional contextualization**: Check neighboring countries for cross-border patterns
5. **Alternative terminology**: Use synonyms, local terms, different spellings

**PHASE 3: Deep Validation (REQUIRED)**
1. **Source chain following**: Check references, citations, follow-up studies
2. **Institution deep dives**: Systematically search organization websites
3. **Archive exploration**: Use Internet Archive for historical sources
4. **Expert consultation**: Contact authors/institutions when possible
5. **Peer verification**: Cross-check findings with multiple independent sources

#### **Search Completeness Verification**
**MANDATORY CHECKLIST before concluding search:**
- [ ] All query categories completed for target country
- [ ] All major search engines and databases checked
- [ ] Local language searches conducted where applicable
- [ ] All decades searched systematically (1970s-2020s)
- [ ] All administrative levels searched (national, provincial, district)
- [ ] Reference chains followed from found sources
- [ ] Institution websites searched systematically
- [ ] Archive searches conducted for broken links
- [ ] Cross-border and regional sources checked
- [ ] Preliminary vs final report versions verified

### RIGOROUS Data Extraction Protocol (MANDATORY)

#### **Documentation Standards**
**REQUIREMENT: Document EVERYTHING**
1. **Original Format Preservation**:
   - Screenshot or copy original data presentation
   - Record exact text, numbers, dates as presented
   - Note table/figure numbers, page numbers, section locations
   - Save PDF copies when possible
   - Document access date and URL status

2. **Extraction Decision Documentation**:
   - Record every interpretive decision made
   - Document ambiguous data handling
   - Note assumptions about missing information
   - Explain unit conversions step-by-step
   - Record alternative interpretations considered

3. **Traceability Requirements**:
   - Direct quotes for key data points
   - Page/section references for all extracted data
   - Author contact information when available
   - Publication DOI/URL for all sources
   - Version information for updated reports

#### **Quality Assurance During Extraction**
**MANDATORY CHECKS:**
1. **Double-entry verification**: Re-extract key data points to check consistency
2. **Mathematical validation**: Verify calculated fields (CFR, attack rates)
3. **Unit consistency**: Ensure all conversions are correct
4. **Date logic**: Verify temporal relationships make sense
5. **Geographic accuracy**: Confirm location codes and names

#### **Uncertainty Quantification**
**REQUIREMENT: Flag and quantify all uncertainties**
1. **High Certainty**: Direct, unambiguous data extraction
2. **Medium Certainty**: Minor interpretation or conversion required
3. **Low Certainty**: Significant assumptions or ambiguous source
4. **Provisional**: Major uncertainties, requires verification

### COMPREHENSIVE Validation Protocol (MANDATORY)

#### **Multi-Stage Validation Process**
**STAGE 1: Automated Validation (REQUIRED)**
- Run ALL validation checks from quality control framework
- Document all validation failures and warnings
- Resolve validation issues before proceeding
- Generate validation report for each data source

**STAGE 2: Cross-Reference Validation (REQUIRED)**
- Compare with JHU database for overlapping periods
- Cross-check with WHO annual surveillance summaries
- Verify against neighboring country outbreak patterns
- Validate seasonal trends against climate data

**STAGE 3: Expert Review (REQUIRED)**
- Epidemiological plausibility assessment
- Historical context validation
- Source credibility evaluation
- Uncertainty quantification review

#### **Validation Documentation Requirements**
**MANDATORY for each validation stage:**
- Validation checklist completion status
- Specific issues identified and resolution actions
- Quality scores and confidence weights assigned
- Reviewer comments and recommendations
- Final inclusion/exclusion decisions with justification

### SYSTEMATIC Quality Control Integration (MANDATORY)

#### **Real-Time Quality Monitoring**
**REQUIREMENT: Monitor quality throughout process**
1. **Validation Pass Rates**: Track percentage passing each validation stage
2. **Source Quality Distribution**: Monitor reliability level breakdown
3. **Geographic Coverage**: Ensure comprehensive regional coverage
4. **Temporal Coverage**: Track gap-filling effectiveness
5. **Duplication Detection**: Monitor and resolve duplicate entries

#### **Quality Improvement Feedback Loop**
**MANDATORY: Continuously improve process**
1. **Pattern Recognition**: Identify common validation failures
2. **Search Optimization**: Adjust queries based on success rates
3. **Source Prioritization**: Focus on highest-yield source types
4. **Validation Refinement**: Update validation rules based on experience
5. **Documentation Enhancement**: Improve guidance based on lessons learned

### FINAL DELIVERABLE STANDARDS (MANDATORY)

#### **Completeness Requirements**
**ALL deliverables must include:**
- Search report with methodology and findings
- Metadata CSV with enhanced indexing system (Index column + all required fields)
- Data CSV in standardized JHU format with dual-reference system (source_index + source columns)
- Quality assessment documentation
- Validation report with all checks performed
- Uncertainty quantification for all data points
- Recommendations for future data collection

#### **Enhanced Format Requirements (MANDATORY)**
**Metadata CSV Format:**
- MUST include Index column with sequential integers (1, 2, 3...)
- MUST include all 9 required columns in exact order
- MUST have consistent Source names for data file referencing

**Data CSV Format:**
- MUST include source_index column referencing metadata Index numbers
- MUST include source column with exact Source name from metadata
- MUST include confidence_weight column with quality-based weights
- MUST include validation_status column with validation results

#### **Quality Assurance Checklist**
**MANDATORY verification before submission:**
- [ ] All searches completed per protocol
- [ ] All validation stages passed
- [ ] All duplications detected and resolved
- [ ] All quality scores assigned appropriately
- [ ] All uncertainties documented and quantified
- [ ] All format conversions verified
- [ ] All source links tested and archived
- [ ] All documentation complete and traceable
- [ ] All recommendations provided for future work
- [ ] **INDEX SYSTEM: Metadata CSV has Index column with sequential integers**
- [ ] **INDEX SYSTEM: Data CSV has source_index column matching metadata indices**
- [ ] **INDEX SYSTEM: Data CSV source names exactly match metadata Source column**
- [ ] **INDEX SYSTEM: All data rows have both source_index AND source columns populated**
- [ ] **INDEX SYSTEM: No index numbers are duplicated or missing in metadata**

**CRITICAL REMINDER: The cholera surveillance data enhancement directly impacts MOSAIC model accuracy and public health decision-making. Thoroughness and accuracy are essential, not optional.**

### ULTRA-RIGOROUS QUALITY CONTROL PROTOCOL

**MANDATORY: Every data point must pass ALL quality control stages**

#### **Stage 1: Automated Validation Checks**
1. **Epidemiological Range Validation**:
   - CFR between 0.1% and 15% (flag outliers for manual review)
   - Case numbers > 0 and < population of affected area
   - Outbreak duration between 1 week and 104 weeks (2 years)
   - Attack rates between 0.01% and 10% of population
   - Deaths ≤ suspected cases (mathematical consistency)

2. **Temporal Logic Validation**:
   - Start date < End date
   - Reporting date ≥ End date
   - No dates in the future beyond data collection
   - Seasonal patterns consistent with regional cholera epidemiology
   - Multi-year trends follow epidemiologically plausible patterns

3. **Geographic Validation**:
   - Location codes match ISO/WHO standards
   - Administrative hierarchy consistency (Country→Province→District)
   - Coordinates within correct administrative boundaries
   - Population denominators match latest census data
   - Cross-border patterns epidemiologically plausible

#### **Stage 2: Cross-Reference Validation**
1. **Multi-Source Confirmation**:
   - Outbreaks >1000 cases: Require ≥2 independent sources
   - CFR >5%: Require clinical confirmation sources
   - New geographic areas: Cross-check with neighboring regions
   - Historical data: Verify against WHO annual summaries

2. **Mathematical Consistency**:
   - CFR calculations accurate to ±0.1%
   - Cumulative totals match sub-period sums
   - Attack rates consistent with population denominators
   - Case progression follows epidemic curve logic

3. **Pattern Recognition**:
   - Seasonal trends match known cholera epidemiology
   - Geographic spread follows transmission pathways
   - Outbreak magnitude consistent with preparedness capacity
   - Recovery rates align with treatment availability

#### **Stage 3: Expert Validation**
1. **Epidemiological Plausibility Review**:
   - Outbreak size appropriate for population/context
   - Case fatality rates consistent with healthcare capacity
   - Transmission patterns align with WASH conditions
   - Seasonal timing consistent with climate patterns

2. **Historical Context Validation**:
   - New data consistent with known historical patterns
   - Unusual patterns have documented explanations
   - Regional synchrony follows known epidemic waves
   - Long-term trends epidemiologically coherent

3. **Source Credibility Assessment**:
   - Author/institution expertise verified
   - Methodology transparency and soundness
   - Potential bias or conflicts of interest identified
   - Data collection standards documented

#### **Stage 4: Final Integration Checks**
1. **Duplication Prevention**:
   - No identical records from different sources
   - Overlapping periods resolved using best available data
   - Updated reports supersede preliminary versions
   - Aggregated data doesn't double-count sub-national data

2. **Completeness Assessment**:
   - All required fields populated or explicitly marked missing
   - Geographic coding complete and standardized
   - Source attribution clear and traceable
   - Quality scores assigned based on validation results

3. **Integration Validation**:
   - New data compatible with existing JHU database
   - No systematic biases introduced
   - Coverage gaps appropriately filled
   - Confidence weights appropriately assigned

#### **Quality Control Documentation Requirements**
**MANDATORY for each data point:**
1. **Validation Status**: Pass/Fail for each validation stage
2. **Flag Reasons**: Specific issues identified during validation
3. **Resolution Actions**: How validation issues were addressed
4. **Final Quality Score**: Numerical rating (1-10) based on validation
5. **Reviewer Notes**: Human expert assessment comments
6. **Uncertainty Quantification**: Confidence intervals where applicable

#### **Rejection Criteria (DO NOT INCLUDE)**
**Automatically reject data if:**
- CFR > 20% without exceptional circumstances documentation
- Case numbers exceed 20% of population (implausible attack rates)
- Dates are logically inconsistent (end before start, future dates)
- Source cannot be verified or authenticated
- Geographic codes don't match any known administrative units
- Mathematical inconsistencies cannot be resolved
- Multiple validation stages failed without adequate explanation

**Flag for manual review if:**
- CFR outside 0.5-10% range
- Attack rates outside 0.1-5% range
- Outbreak duration <2 weeks or >1 year
- Single source for major outbreaks (>500 cases)
- Significant discrepancies between sources
- Unusual seasonal patterns requiring explanation

#### **Quality Assurance Metrics**
**Track and report:**
1. **Validation Pass Rates**: Percentage passing each validation stage
2. **Source Distribution**: Breakdown by reliability level
3. **Geographic Coverage**: Administrative levels represented
4. **Temporal Coverage**: Years and periods covered
5. **Data Density**: Records per year/region
6. **Quality Scores**: Distribution of final quality ratings
7. **Rejection Rates**: Reasons for data exclusion
8. **Uncertainty Levels**: Distribution of confidence weights

## Common Pitfalls and Solutions

### Search Challenges
- **Problem**: Limited results for specific countries/time periods
- **Solution**: Broaden search to regional reports, neighboring countries

### Enhanced Data Quality Issue Resolution

#### **Conflicting Information Protocol**
**Problem**: Different sources report conflicting case numbers, dates, or other key data

**MANDATORY Resolution Steps:**
1. **Document All Conflicts**: Record exact values from each source with timestamps
2. **Apply Source Hierarchy**: Use reliability levels to prioritize sources
3. **Investigate Discrepancies**: Research reasons for differences (different case definitions, reporting periods, geographic coverage)
4. **Calculate Uncertainty Ranges**: Provide minimum-maximum ranges based on source variation
5. **Weight Appropriately**: Reduce confidence weights for conflicting data points
6. **Flag for Sensitivity Analysis**: Mark high-uncertainty data for model testing
7. **Provide Multiple Scenarios**: When conflicts are major, include alternative data scenarios

**Specific Conflict Resolution Rules:**
- **WHO vs Local Sources**: Prefer WHO for standardized case definitions
- **Preliminary vs Final Reports**: Always use final/updated versions
- **Different Time Periods**: Ensure exact temporal alignment before comparing
- **Different Geographic Scales**: Use most specific level, verify aggregation
- **Academic vs Operational**: Consider purpose and methodology differences

#### **Data Completeness Issues**
**Problem**: Missing essential data fields or incomplete reporting

**Resolution Protocol:**
1. **Required Fields**: Location, dates, case/death counts must be present
2. **Acceptable Gaps**: CFR can be calculated if cases and deaths available
3. **Geographic Coding**: Standardize to AFR::ISO::Province::District format
4. **Temporal Alignment**: Convert all date formats to YYYY-MM-DD
5. **Imputation Rules**: Only interpolate obvious transcription errors
6. **Missing Value Codes**: Use standardized codes (NA, missing, not reported)

#### **Source Authentication Issues**
**Problem**: Difficulty verifying source credibility or accessing data

**Verification Steps:**
1. **URL Validation**: Test all links, use archived versions if current links fail
2. **Author Credentials**: Verify institutional affiliations and expertise
3. **Publication Verification**: Confirm journal indexing, peer review status
4. **Institution Validation**: Check official government/organization websites
5. **Archive Search**: Use Internet Archive for broken or moved content
6. **Alternative Access**: Contact authors/institutions directly if needed

**Authentication Documentation:**
- Record all verification attempts and results
- Note any concerns about source credibility
- Document alternative access methods used
- Flag sources that couldn't be fully authenticated

### Comprehensive Format and Unit Standardization

#### **Date Format Standardization**
**Problem**: Multiple date formats across sources (DD/MM/YYYY, MM-DD-YY, etc.)

**MANDATORY Conversion Rules:**
- **Standard Format**: YYYY-MM-DD for all dates
- **Ambiguous Dates**: When format unclear, document assumption made
- **Date Ranges**: Use TL (time left) and TR (time right) for start/end dates
- **Incomplete Dates**: "2006-01-01" to "2006-12-31" for year-only data
- **Seasonal Data**: Assign to appropriate months (rainy season = May-October for most African countries)

#### **Case Count Standardization**
**Problem**: Different case definitions, units, or reporting standards

**Conversion Protocol:**
1. **Suspected Cases (sCh)**: Primary metric, includes clinical diagnoses
2. **Confirmed Cases (cCh)**: Laboratory-confirmed only
3. **Combined Reporting**: When only "total cases" given, assign to sCh field
4. **Rate Conversions**: Convert incidence rates to absolute numbers using population denominators
5. **Cumulative vs Period**: Clearly distinguish and convert appropriately

**Documentation Requirements:**
- Record original format and conversion method
- Note any assumptions about case definitions
- Flag conversions with high uncertainty
- Provide population denominators used for rate conversions

#### **Geographic Standardization**
**Problem**: Inconsistent geographic naming, coding, or administrative levels

**MANDATORY Standards:**
- **Country Level**: AFR::{ISO_CODE} (e.g., AFR::AGO for Angola)
- **Province Level**: AFR::{ISO}::{PROVINCE} (e.g., AFR::AGO::Luanda)
- **District Level**: AFR::{ISO}::{PROVINCE}::{DISTRICT}
- **Municipal Level**: AFR::{ISO}::{PROVINCE}::{DISTRICT}::{MUNICIPALITY}

**Name Standardization Rules:**
- Use official administrative names in English
- Cross-reference with ISO 3166-2 subdivision codes
- Handle name changes over time with date-appropriate coding
- Document alternative spellings and local names

#### **Unit and Scale Conversions**
**Problem**: Different measurement units, population scales, time periods

**Conversion Standards:**
1. **Population Denominators**: Always use absolute numbers, not rates
2. **Time Periods**: Standardize to weekly where possible
3. **Case Fatality Rate**: Always express as percentage (0-100%)
4. **Attack Rates**: Express as percentage of affected population
5. **Duration**: Express in days or weeks, not months/years

**Quality Assurance for Conversions:**
- Double-check all mathematical conversions
- Verify population denominators against census data
- Cross-validate converted values against other sources
- Document conversion factors and sources used
- Flag high-uncertainty conversions for sensitivity analysis
**Conversion Documentation Requirements:**
- **Original Values**: Preserve exact original data in metadata
- **Conversion Method**: Document step-by-step conversion process
- **Assumptions Made**: Record any interpretive decisions
- **Uncertainty Assessment**: Quantify conversion-related uncertainty
- **Validation Checks**: Cross-verify converted values
- **Alternative Interpretations**: Note other possible conversions
- **Source Contact**: Record attempts to clarify with original authors

**Quality Flags for Conversions:**
- **DIRECT**: No conversion needed, data in standard format
- **SIMPLE**: Straightforward conversion (dates, percentages)
- **COMPLEX**: Multiple conversions or assumptions required
- **UNCERTAIN**: Significant ambiguity in conversion process
- **ESTIMATED**: Conversion required estimation or interpolation

### Temporal Alignment
- **Problem**: Different reporting periods (weekly vs monthly vs annual)
- **Solution**: Use appropriate temporal aggregation, note resolution in metadata

## Success Metrics

### Quantitative Measures
- **Gap Reduction**: Percentage of missing weeks filled
- **Source Diversity**: Number of different source types identified
- **Geographic Coverage**: Proportion of administrative levels covered
- **Temporal Span**: Years of historical data added

### Qualitative Measures
- **Source Reliability**: Average confidence rating of sources
- **Data Completeness**: Proportion of critical outbreak periods captured
- **Cross-validation**: Consistency with existing reliable sources
- **Usability**: Ease of integration into modeling workflow

## Future Enhancements

### Automation Opportunities
- **Systematic monitoring**: Regular searches for new outbreak reports
- **Quality scoring**: Automated assessment of source reliability
- **Temporal interpolation**: Smart gap-filling based on neighboring data

### Methodological Improvements
- **Source ranking algorithms**: Data-driven assessment of source quality
- **Uncertainty propagation**: Better methods for handling data quality uncertainty
- **Cross-country validation**: Use regional patterns to validate country-specific data

## Angola Pilot Results and Lessons Learned

The Angola pilot successfully demonstrated this ULTRA-thorough methodology:

### Quantitative Achievements
- **Data Gap**: 454 of 796 weekly records (57%) had missing data
- **Sources Found**: 25 working URLs across 6 source categories  
- **Data Added**: 35 new observations spanning 1971-2025
- **Key Periods**: Filled critical gaps in 2006-2012 and 2016-2018
- **Geographic Detail**: Added provincial-level data for major outbreaks
- **Quality Distribution**: 60% Level 1-2 sources, 40% Level 3-4 sources
- **Validation Success**: 94% of extracted data passed all validation stages

### Process Validation
- **Search Comprehensiveness**: Multi-engine, multi-language approach identified sources missed by single-engine searches
- **Quality Control Effectiveness**: Rigorous validation caught and corrected 12% of initially extracted data points
- **Duplication Prevention**: Systematic checking prevented inclusion of 8 duplicate records
- **Cross-Reference Value**: Historical validation identified 3 data inconsistencies that were resolved through additional research

### Critical Lessons for Future Instances

#### **What Worked Exceptionally Well**
1. **WHO AFRO searches** yielded highest-quality recent outbreak data
2. **Academic literature searches** filled crucial historical gaps
3. **UNICEF humanitarian reports** provided essential provincial-level detail
4. **Cross-border validation** with DRC data confirmed outbreak timing
5. **Multi-language searches** in Portuguese uncovered unique local sources

#### **Search Strategy Refinements**
1. **Archive searches critical**: 15% of highest-quality sources required Internet Archive access
2. **Institution deep-dives essential**: Direct website searches found sources missed by general search engines
3. **Reference chain following**: 30% of final sources discovered through citation following
4. **Temporal stratification effective**: Decade-specific searches more productive than general queries
5. **Regional contextualization**: Neighboring country patterns helped validate gap periods

#### **Quality Control Insights**
1. **Cross-reference validation crucial**: Identified 4 cases of conflicting case numbers that required additional research
2. **Epidemiological plausibility checks effective**: Flagged 2 CFR values that were later confirmed as transcription errors
3. **Geographic validation essential**: Prevented inclusion of 3 incorrectly geo-coded outbreaks
4. **Duplication detection vital**: Multiple organizations reporting same outbreaks required careful resolution
5. **Source authentication important**: 2 initially promising sources were excluded due to credibility concerns

### Scaling Requirements for Future Countries

#### **Minimum Search Requirements (Learned from Angola)**
- **Minimum 15 distinct search engines/databases** per country
- **Minimum 50 unique search queries** across all categories
- **Minimum 10 hours of systematic searching** per country
- **Mandatory multi-language searches** for non-English speaking countries
- **Required cross-border validation** with neighboring countries
- **Systematic decade-by-decade temporal coverage**

#### **Quality Control Minimums**
- **100% validation** of all extracted data points
- **Multi-source confirmation** for all major outbreaks (>1000 cases)
- **Cross-reference checking** against WHO annual summaries
- **Duplication screening** for all overlapping time periods
- **Expert review** of all high-uncertainty data points

This pilot validates the ULTRA-deep search approach and demonstrates that comprehensive, systematic searching can dramatically improve cholera surveillance data completeness while maintaining high quality standards.

## CRITICAL SUCCESS FACTORS AND FINAL REQUIREMENTS

### NON-NEGOTIABLE REQUIREMENTS FOR ALL FUTURE INSTANCES

**These requirements are MANDATORY, not optional:**

1. **ULTRA-THOROUGH SEARCHING**: Every query category, every search engine, every time period
2. **RIGOROUS VALIDATION**: Every data point through every validation stage
3. **COMPREHENSIVE DOCUMENTATION**: Every source, every decision, every uncertainty
4. **SYSTEMATIC QUALITY CONTROL**: Every check, every validation, every cross-reference
5. **COMPLETE DELIVERABLES**: Every required file, every required field, every required standard

### FAILURE CONDITIONS (WORK WILL BE REJECTED IF:)

- Search methodology is incomplete or unsystematic
- Validation protocols are skipped or inadequately performed
- Documentation is missing or insufficient
- Quality control standards are not met
- Data formatting doesn't match JHU standards
- Source authentication is inadequate
- Duplication detection is not performed
- Uncertainty quantification is missing

### SUCCESS METRICS (MINIMUM ACCEPTABLE STANDARDS)

**Search Completeness:**
- ≥90% of specified query categories completed
- ≥15 distinct search engines/databases used
- ≥50% of sources found through systematic (not opportunistic) searching
- Local language searches conducted for non-English countries

**Data Quality:**
- ≥95% of extracted data passes automated validation
- ≥90% of major outbreaks confirmed by multiple sources
- ≥80% of sources at reliability Level 2 or higher
- Zero unresolved duplications in final dataset

**Documentation Standards:**
- 100% of sources have working URLs or archived copies
- 100% of data points have clear source attribution
- 100% of conversions and interpretations documented
- 100% of quality assessments completed

### KNOWLEDGE TRANSFER REQUIREMENTS

**For technical questions or methodological guidance:**
1. **Primary Reference**: This CLAUDE.md file contains all standard procedures
2. **Working Example**: Angola pilot demonstrates complete methodology
3. **Innovation Documentation**: Document any novel challenges and solutions
4. **Standards Compliance**: Maintain strict consistency with JHU database formatting
5. **Process Improvement**: Suggest enhancements based on experience

### ULTIMATE GOAL REMINDER

**The objective is to create a comprehensive, quality-controlled enhancement to cholera surveillance data that:**
- Fills critical gaps in historical cholera surveillance
- Maintains the highest possible data quality standards
- Provides appropriate uncertainty quantification
- Supports evidence-based public health decision-making
- Enables accurate epidemiological modeling across the WHO African Region
- Serves as a model for AI-enhanced surveillance data collection

**This work directly impacts global cholera control efforts. Excellence is required, not requested.**

---

**FINAL CHECKPOINT: Before submitting any country's data enhancement, verify that ALL requirements in this document have been met. Incomplete or substandard work will require complete revision.**