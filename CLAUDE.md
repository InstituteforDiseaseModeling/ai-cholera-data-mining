# CLAUDE.md - AI Cholera Surveillance Data Enhancement

**Mission**: Fill ~50% missing observations in WHO surveillance records (1970-present) through systematic identification, validation, and integration of unofficial cholera data sources.

**Strategy**: Systematic internet searches to discover unreported transmission events and validate zero-transmission periods for complete historical time series.

## Data Sources & Hierarchy

**Core Data**: Official surveillance, JHU database, AI-enhanced sources  
**Source Tiers**: Level 1 (WHO/MoH) → Level 2 (UNICEF/Academic) → Level 3 (News/NGO) → Level 4 (Local/Social)

## Core Methodology

**Workflow**: Gap assessment → JHU inventory → AI systematic search → Data integration  
**Output Format**: JHU-compatible CSV with enhanced dual-reference indexing  
**Deliverables**: search_report.txt, metadata.csv, cholera_data.csv, search_log.txt

## MANDATORY GAP-TARGETED SEARCH PROTOCOL

**CRITICAL**: Before beginning any search, agents MUST consult surveillance coverage reference files to target missing periods.

### Pre-Search Requirements (MANDATORY)

1. **Load Reference Files**: Read `./reference/agent_quick_reference.csv` for country-specific gaps
2. **Identify Priority Periods**: Focus searches on specific missing date ranges
3. **Apply Temporal Filters**: Include missing years/periods in ALL search queries
4. **Prioritize High-Gap Countries**: Begin with HIGH priority countries (<70% coverage)

### Gap-Targeted Query Strategy

**MANDATORY QUERY MODIFICATION**: All searches must include temporal constraints targeting missing periods.

**Standard Query**: `"Angola cholera outbreak WHO"`
**Gap-Targeted Query**: `"Angola cholera outbreak WHO 2019 2020 2021 2022"` (targeting specific missing years)

**Template Examples**:
- `"{Country} cholera cases {missing_year_1} {missing_year_2}"` 
- `"{Country} cholera surveillance {gap_start_year}-{gap_end_year}"`
- `"{Country} cholera outbreak {specific_missing_period}"`

### Reference File Usage Protocol

**agent_quick_reference.csv Usage**:
```
FOR EACH COUNTRY:
1. Check search_priority (HIGH/MEDIUM/LOW)
2. Read missing_recent_years for temporal targeting
3. Use priority_periods for exact date range focus
4. Apply coverage_pct for effort allocation
```

**Example for Ethiopia (59.1% coverage, HIGH priority)**:
- **Priority Gap**: 2018-12-10 to 2023-01-01
- **Missing Years**: 2000-2009 (historical)
- **Search Focus**: "Ethiopia cholera 2019 2020 2021 2022" + historical searches

### Temporal Search Allocation (MANDATORY)

**HIGH Priority Countries** (<70% coverage): 80% of searches target priority gaps, 20% historical extension
**MEDIUM Priority Countries** (70-90%): 60% gap-filling, 40% historical extension  
**LOW Priority Countries** (>90%): 40% gap-filling, 60% historical/future extension

### Gap Validation Requirements

**MANDATORY**: For each identified gap period, agents must:
1. **Confirm Zero Transmission**: Search for evidence that NO cholera occurred
2. **Identify Surveillance Gaps**: Distinguish between no disease vs. no reporting
3. **Document Gap Type**: Disease-free period vs. surveillance system failure
4. **Cross-Reference Regional**: Check neighboring countries for outbreak patterns

### Success Metrics for Gap-Targeted Searches

**Primary Goal**: Fill identified priority gaps with confirmed zero-transmission or discovered outbreak data
**Secondary Goal**: Extend historical coverage before earliest observed data
**Tertiary Goal**: Validate recent surveillance completeness

### Practical Gap-Targeting Example

**ETHIOPIA (ETH) - 59.1% coverage, HIGH priority**:
- **Priority Gap**: 2018-12-10 to 2023-01-01 (4+ year gap)
- **Missing Historical**: 2000-2014 
- **Current Data**: 2015-2018, 2023-2025

**Mandatory Search Allocation**:
1. **80% effort on Priority Gap (2019-2022)**:
   - "Ethiopia cholera 2019 surveillance WHO"
   - "Ethiopia cholera outbreak 2020 2021 UNICEF" 
   - "Ethiopia cholera epidemic 2022 MSF"
   - "Ethiopia cholera cases 2019-2022 government"

2. **20% effort on Historical Extension (pre-2015)**:
   - "Ethiopia cholera 2010-2014 surveillance"
   - "Ethiopia cholera 2000s decade outbreak"
   - "Ethiopia cholera historical 1990s 2000s"

**Gap Validation Searches**:
- "Ethiopia cholera-free 2019 2020 2021" (confirm no disease)
- "Ethiopia surveillance system 2019-2022" (check reporting gaps)
- "Ethiopia neighboring countries cholera 2019-2022" (regional context)

**RESULT EXPECTATION**: Either fill 2019-2022 gap with data OR confirm no cholera transmission with evidence

## ULTRA DEEP SEARCH METHODOLOGY

**CRITICAL**: Exhaustive, systematic internet searches across ALL discoverable sources.

### Search Strategy
**Multi-Engine Protocol**: 15+ search engines/databases per country  
**Query Framework**: 7 mandatory categories, 50+ unique queries minimum  
**Source Coverage**: 486 tiered domains in priority_sources.txt + expansion

### Query Categories (Mandatory)

1. **WHO/Official**: Surveillance reports, epidemiological bulletins, situation updates
2. **Academic**: Peer-reviewed literature, epidemiological studies, phylogenetic analyses
3. **Humanitarian**: UNICEF, OCHA, MSF outbreak responses, emergency assessments
4. **Regional**: Cross-border transmission, surveillance networks, neighboring countries
5. **Historical**: Colonial records, pandemic waves, archive searches by decade
6. **Technical**: Laboratory networks, diagnostic evaluation, environmental monitoring
7. **Linguistic**: Local language searches, vernacular terms, regional media

**Query Templates**: See template_search_protocol.txt for complete query lists

### Advanced Techniques

**Temporal Granularity**: Monthly/seasonal/decade-specific searches  
**Geographic Granularity**: National → Provincial → District → Municipal levels  
**Source Chain Following**: Citation networks, reference tracing, report versions  
**Institutional Deep Dives**: Ministry archives, university repositories, regional organizations

**Temporal Focus Periods**:  
- 1970s-1990s: Historical/colonial records  
- 1990s-2010: Early surveillance development  
- **2010-2020**: Primary gap-filling target  
- 2020-present: COVID impact assessment

## Data Standards

**Directory**: `data/{ISO_CODE}/`  
**Files**: search_report.txt, metadata.csv, cholera_data.csv, search_log.txt

### DUAL-REFERENCE INDEXING SYSTEM

**CRITICAL**: Mandatory enhanced indexing for data integrity

**Protocol**: Sequential integer indices (1,2,3...) + exact source names  
**Benefit**: Automated processing + human readability + error prevention  
**Format**: metadata.csv Index column ↔ cholera_data.csv source_index column

### File Specifications

**search_report.txt**: Executive summary, methodology, quality assessment, JHU relationship, recommendations

**metadata.csv** (9 columns): Index, Source, URL, Description, Date_Range, Data_Type, Status, Reliability_Level, Validation_Status

**cholera_data.csv** (12 columns): Location, TL, TR, deaths, sCh, cCh, CFR, reporting_date, source_index, source, confidence_weight, processing_notes

## COMPREHENSIVE COLUMN DEFINITIONS

### cholera_data.csv Column Specifications

**Location** (CRITICAL - Geographic Administrative Units ONLY):
- **Purpose**: Geographic administrative unit where cholera cases/deaths occurred
- **Format**: `AFR::{ISO}` (national), `AFR::{ISO}::{PROVINCE}` (provincial), `AFR::{ISO}::{PROVINCE}::{DISTRICT}` (district)
- **ACCEPTABLE**: `AFR::AGO`, `AFR::AGO::Luanda`, `AFR::AGO::Luanda::Belas`, `AFR::AGO::Multi_Provincial`
- **PROHIBITED**: Any non-geographic categories (Vaccination, Training, Demographics_*, Age_Group_*, Laboratory_*, Surveillance_*)
- **Rule**: Must represent a physical location where people contracted cholera

**TL** (Time Left - Start Date):
- **Purpose**: Outbreak/reporting period start date
- **Format**: YYYY-MM-DD (ISO 8601)
- **Required**: Always required, use best available estimate if exact date unknown

**TR** (Time Right - End Date): 
- **Purpose**: Outbreak/reporting period end date
- **Format**: YYYY-MM-DD (ISO 8601)
- **Rule**: Must be ≥ TL date

**deaths** (Integer):
- **Purpose**: Number of confirmed cholera deaths
- **Format**: Positive integer or empty
- **Validation**: Must be ≤ sCh (deaths cannot exceed suspected cases)

**sCh** (Suspected Cholera Cases - Integer):
- **Purpose**: Clinically diagnosed cholera cases (including probable cases)
- **Format**: Positive integer or empty
- **Primary Metric**: Main case count for surveillance
- **Rule**: Must have actual case numbers, not vaccination counts, population figures, or capacity data

**cCh** (Confirmed Cholera Cases - Integer):
- **Purpose**: Laboratory-confirmed cholera cases only
- **Format**: Positive integer or empty
- **Rule**: Must be ≤ sCh (confirmed cases subset of suspected)

**CFR** (Case Fatality Rate - Percentage):
- **Purpose**: Percentage of cases resulting in death
- **Format**: 0-100 (percentage, not decimal)
- **Calculation**: (deaths/sCh) × 100
- **Validation**: Must be 0.1-15% for most outbreaks (flag outliers)

**reporting_date** (Date):
- **Purpose**: Date when data was reported/published
- **Format**: YYYY-MM-DD
- **Rule**: Must be ≥ TR (reporting after outbreak end)

**source_index** (Integer):
- **Purpose**: Reference to metadata.csv Index column
- **Format**: Sequential integer (1, 2, 3...)
- **Critical**: Must match exactly with metadata.csv Index

**source** (Text):
- **Purpose**: Exact name of source from metadata.csv
- **Format**: Free text matching metadata Source column exactly
- **Validation**: Must exist in metadata.csv Source column

**confidence_weight** (Decimal):
- **Purpose**: Quality-based weighting for modeling
- **Format**: 0.1-1.0 decimal
- **Levels**: Level 1 (0.9-1.0), Level 2 (0.7-0.9), Level 3 (0.3-0.6), Level 4 (0.1-0.3)

**processing_notes** (Text):
- **Purpose**: Detailed notes on data extraction and interpretation
- **Format**: Free text with exact source quotes
- **Required**: Must include source quotes supporting case/death interpretations
- **Template**: "Source states: '[exact quote]' - interpreted as [sCh/cCh] cases"

## CRITICAL DATA INCLUSION RULES

### MANDATORY Requirements for cholera_data.csv Entry:
1. **Geographic Location**: Must be actual administrative unit (country/province/district)
2. **Quantitative Data**: Must have specific numbers for cases, deaths, or CFR
3. **Cholera-Specific**: Must be cholera cases/deaths, not vaccination/training/capacity data
4. **Source Attribution**: Must have matching metadata entry with working source

### PROHIBITED Entries (DO NOT ADD):
- **Vaccination Data**: `AFR::{ISO}::Vaccination`, `AFR::{ISO}::OCV_Campaign`
- **Training Data**: `AFR::{ISO}::Training`, `AFR::{ISO}::Health_Workers`
- **Demographics Without Location**: `AFR::{ISO}::Demographics_*`, `AFR::{ISO}::Age_*`
- **System Capacity**: `AFR::{ISO}::Laboratory_*`, `AFR::{ISO}::Surveillance_*`
- **Population Data**: Population denominators, coverage percentages, capacity figures

### DATA EXTRACTION VALIDATION CHECKLIST:
```
BEFORE ADDING ANY ROW:
□ Location is geographic administrative unit (not program/demographic category)
□ sCh or cCh contains actual cholera case numbers (not vaccination/population/capacity)
□ Source explicitly mentions cholera cases/deaths (not just cholera programs)
□ Numbers represent disease incidence (not prevention/demographics/training)
□ Processing notes include exact source quote supporting interpretation
```

**MANDATORY DATA INCLUSION REQUIREMENT**: Agents are **PROHIBITED** from adding any data observations (rows) to cholera_data.csv unless they can identify at least one cholera case value (sCh or cCh). Sources that only mention cholera outbreaks without providing quantitative case counts **MUST NOT** be included in the data file. Only sources with identifiable case numbers, death counts, or calculable epidemiological metrics qualify for data extraction.

**ENHANCED QUALITY CONTROL FOR sCh/cCh COLUMNS**:

**Mandatory Pre-Entry Validation**
```
BEFORE ADDING TO cholera_data.csv:
□ Number explicitly described as cholera "cases" (not vaccinated, population, density)
□ Source context indicates disease incidence (not prevention/demographics)
□ Quote exact source text supporting case interpretation
□ Validate units are case counts, not rates/coverage/capacity
```

**High-Risk Context Flags**
```
EXTRA VALIDATION REQUIRED FOR:
- Vaccination reports → likely vaccinated count, not cases
- Demographics → likely population, not cases  
- WASH assessments → likely coverage, not cases

ACCEPT: "cases", "infections", "ill", "hospitalized"
REJECT: "affected", "targeted", "covered", "population"
```

**Mandatory Documentation**
```
processing_notes MUST include: "Source states: '[exact quote]' - interpreted as [sCh/cCh] cases"
```

**MANDATORY EXTENDED THINKING REQUIREMENT**
```
USE EXTENDED ULTRATHINK WHEN:
□ Synthesizing data from multiple sources
□ Interpreting ambiguous numbers or context
□ Performing any cross-validation between sources
□ Resolving conflicts between different reports
□ Determining if numbers represent cases vs. other metrics

THINK THROUGH: Context clues, source credibility, temporal alignment, 
epidemiological plausibility, alternative interpretations
```

**Tiered Cross-Validation Framework**
```
TIER 1: High-Value Cases (>1000 cases)
- REQUIRE: 2+ independent sources for major outbreaks
- USE ULTRATHINK: Compare sources, resolve discrepancies

TIER 2: Moderate Cases (100-1000 cases)  
- ENCOURAGE: Seek secondary confirmation when possible
- ACCEPT: Single high-quality source (Level 1-2)
- FLAG: Note single-source status

TIER 3: Small Cases (<100 cases)
- ACCEPT: Single source with appropriate confidence weighting

CROSS-VALIDATION TRIGGERS (REQUIRE 2+ SOURCES):
□ Cases >1000 (major outbreak)
□ First outbreak in new geographic area
□ Dates conflict with regional patterns
```

**Requirements**: Dual-reference system (source_index ↔ Index), exact name matching, YYYY-MM-DD dates, AFR::{ISO} location codes

## DATA QUALITY FRAMEWORK

**CRITICAL**: Mandatory 4-stage validation for ALL sources

### Source Reliability Levels

**Level 1 (0.9-1.0)**: WHO, MoH, peer-reviewed journals, government statistics  
**Level 2 (0.7-0.9)**: UNICEF, OCHA, established NGOs, regional organizations  
**Level 3 (0.3-0.6)**: Reputable news, local government, preliminary academic reports  
**Level 4 (0.1-0.3)**: Local media, social media, unofficial reports (extreme caution)

### Validation Protocol (4 Stages)

**Stage 1 - Authentication**: URL verification, author credentials, domain validation  
**Stage 2 - Data Quality**: CFR 0.1-15%, attack rates 0.01-10%, duration 2 weeks-2 years  
**Stage 3 - Cross-Reference**: Multi-source confirmation (>1000 cases), historical consistency  
**Stage 4 - Duplication**: Exact/partial detection, resolution protocol, documentation

### Quality Control

**Quantitative Rules**: Statistical outlier detection, trend analysis, demographic consistency  
**Qualitative Criteria**: Methodological soundness, reporting quality, institutional credibility  
**Documentation**: URL, validation status, quality score, confidence weight, limitations, cross-references  
**Conflict Resolution**: Source hierarchy, uncertainty ranges, sensitivity analysis flags

**Quality Flags**: HIGH/MEDIUM/LOW/PROVISIONAL based on validation results

## MOSAIC Integration

**Data Flow**: Gap-filled surveillance → Enhanced time series → Weighted modeling  
**Integration**: Confidence weights in likelihood functions, uncertainty propagation, sensitivity analysis

## MANDATORY BEST PRACTICES FOR AI INSTANCES

**REQUIREMENTS: These practices are mandatory. Non-compliance compromises MOSAIC modeling effectiveness.**

### Gap-Targeted Search Initialization (MANDATORY)

**STEP 1: Load Reference Data (BEFORE ANY SEARCHES)**
```python
# REQUIRED: Read reference files before starting
import pandas as pd
agent_ref = pd.read_csv('./reference/agent_quick_reference.csv')
target_country = agent_ref[agent_ref['iso_code'] == 'ETH'].iloc[0]  # Example: Ethiopia
priority_periods = target_country['priority_periods']  # "2018-12-10 to 2023-01-01"
missing_years = target_country['missing_recent_years']  # "2000, 2001, 2002..."
search_priority = target_country['search_priority']  # "HIGH"
```

**STEP 2: Parse Target Periods**
```python
# Extract specific years and periods for targeted searching
if 'to' in priority_periods:
    gap_start, gap_end = priority_periods.split(' to ')
    gap_years = list(range(int(gap_start[:4]), int(gap_end[:4]) + 1))
else:
    gap_years = []

missing_years_list = [int(y.strip()) for y in missing_years.split(',') if y.strip() != 'None']
```

**STEP 3: Generate Gap-Targeted Queries**
```python
# MANDATORY: Include temporal constraints in ALL queries
base_queries = [
    f"{country} cholera outbreak",
    f"{country} cholera surveillance", 
    f"{country} cholera epidemic"
]

# Add temporal targeting
targeted_queries = []
for query in base_queries:
    for year in gap_years:
        targeted_queries.append(f"{query} {year}")
    for year in missing_years_list[:5]:  # Focus on first 5 missing years
        targeted_queries.append(f"{query} {year}")
```

### Systematic Search Strategy (MANDATORY)

#### **MANDATORY PARALLEL SEARCH METHODOLOGY**

**CRITICAL**: This section overrides all other search guidance. Failure to implement parallel execution will result in incomplete data collection and methodology non-compliance.

##### **A. Fundamental Parallel Processing Mandate**

**PROHIBITED BEHAVIOR**: Sequential query execution
```python
# NEVER DO THIS - Sequential Processing
WebSearch("Angola cholera WHO 2024")     # Wait
WebSearch("Angola cholera UNICEF 2024")  # Wait  
WebSearch("Angola cholera MSF 2024")     # Wait
```

**MANDATORY BEHAVIOR**: Parallel batch execution
```python
# REQUIRED - Parallel Batch Processing: batches of 25 queries
[
  WebSearch("Angola cholera WHO 2024"),
  WebSearch("Angola cholera UNICEF 2024"),
  WebSearch("Angola cholera MSF 2024"),
  WebSearch("Angola cholera ReliefWeb 2024"),
  WebSearch("Angola cholera government 2024"),
  WebSearch("Angola cholera academic 2024"),
  WebSearch("Angola cholera surveillance 2024"),
  WebSearch("Angola cholera cases 2002")
  WebSearch("Angola cholera deaths 2006")
  WebSearch("Angola oral cholera vaccine 2018")
]
```

**MANDATORY BEHAVIOR**: Complete ALL stated queries without shortcuts

#### **Multi-Phase Search Protocol (Using Parallel Execution)**
**PHASE 1: Broad Discovery (REQUIRED)**
1. **Start with systematic queries**: Execute ALL query categories using parallel batch processing from section above
2. **Multiple search engines**: Use parallel WebSearch calls across Google, Google Scholar, PubMed, WHO databases, ReliefWeb, government sites
3. **Language diversity**: Execute multi-language query batches simultaneously (English, French, Portuguese, Arabic, local languages)
4. **Temporal comprehensiveness**: Batch decade-specific searches in parallel (1970s, 1980s, etc.)
5. **Geographic completeness**: Parallel execution across administrative levels (national, provincial, district)

**PHASE 2: Targeted Gap Filling (REQUIRED)**
1. **Identify specific gaps**: Missing years, regions, outbreak periods from Phase 1 results
2. **Focused searches**: Execute gap-specific queries in parallel batches using accelerated methodology
3. **Cross-reference validation**: Use parallel WebFetch to verify gaps across multiple sources simultaneously
4. **Regional contextualization**: Batch cross-border searches for neighboring countries (execute in parallel)
5. **Alternative terminology**: Create synonym/local term query batches for parallel execution

**PHASE 3: Deep Validation (REQUIRED)**
1. **Source chain following**: Execute reference/citation searches in parallel batches
2. **Institution deep dives**: Use parallel WebSearch across multiple organization websites simultaneously
3. **Archive exploration**: Batch Internet Archive searches using parallel processing
4. **Expert consultation**: Contact authors/institutions when possible (maintain parallel processing for other searches)
5. **Peer verification**: Execute cross-checking across multiple sources using parallel WebFetch

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
- [ ] **PARALLEL EXECUTION: All searches conducted using parallel batch methodology**
- [ ] **PERFORMANCE STANDARDS: Agent 1 minimum 8 batches/200 queries with stopping criteria, Agent 4 exactly 200 queries**
- [ ] **SYSTEMATIC COVERAGE: Priority sources parsed and systematically searched**
- [ ] **BATCH LOGGING: Query rates and performance metrics documented**

**CRITICAL: This data enhancement directly impacts MOSAIC model accuracy and public health decisions. Thoroughness, accuracy, and efficient parallel execution are mandatory.**

### Quality Control Protocol

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

#### **Updated Search Requirements (Using Parallel Methodology)**
- **PARALLEL EXECUTION MANDATORY**: All queries must use batch processing (20 parallel queries per batch)
- **Minimum Performance Standards**: Agent 1 minimum 5 batches/100 queries with data observation yield stopping criteria, Agent 4 conditional batching based on data discovery
- **Systematic Coverage Required**: Agent 1 uses focused 45 highest-priority sources (200 queries from priority_sources.txt)
- **Multi-language Parallel Batches**: Execute simultaneous searches in English, Portuguese, French, Arabic, and local languages
- **Cross-border Parallel Validation**: Batch searches across neighboring countries simultaneously
- **Accelerated Temporal Coverage**: Parallel decade-specific searches (1970s-2020s executed simultaneously)

#### **Quality Control Minimums (Enhanced)**
- **100% validation** of all extracted data points using parallel validation techniques
- **Multi-source confirmation** for all major outbreaks (>1000 cases) via parallel WebFetch
- **Cross-reference checking** against WHO annual summaries using batch processing
- **Duplication screening** for all overlapping time periods with automated detection
- **Expert review** of all high-uncertainty data points while maintaining search momentum
- **Performance Monitoring**: Real-time tracking of query rates and batch completion times

This methodology validates that **systematic parallel execution** can complete comprehensive searches (1,000-1,320 queries) in 10-15 minutes while maintaining the highest quality standards for MOSAIC epidemiological modeling.

## COMPREHENSIVE ACCESS PERMISSIONS

### UNRESTRICTED ACCESS TO SUGGESTED SOURCES

**EXPLICIT AUTHORIZATION**: All AI instances working on cholera surveillance data collection have **UNRESTRICTED AND IMMEDIATE ACCESS** to all domains, websites, databases, and platforms listed in `./priority_sources.txt`.

**PRE-APPROVED DOMAIN ACCESS**: The priority_sources.txt file contains **486 pre-authorized domains** organized into 4 priority tiers:

- **TIER 1 (105 sources)**: WHO Official, Government Health Ministries, Major Academic Medical Centers
- **TIER 2 (138 sources)**: UN Agencies, Major Universities, Established NGOs, Major Journals  
- **TIER 3 (141 sources)**: Regional Organizations, News Media, Surveillance Networks, WASH Organizations
- **TIER 4 (102 sources)**: Archives, Specialized Databases, Secondary Sources

**ACCESS PROTOCOL**: 
1. **No Permission Required**: Proceed immediately with WebFetch(), WebSearch(), and data extraction from any domain in priority_sources.txt
2. **Systematic Coverage Mandatory**: Execute the required queries per tier (30/15/8/4 queries respectively) 
3. **Documentation Required**: Log all access attempts and results in search logs
4. **Quality Standards**: Apply appropriate reliability ratings based on tier classifications

**EXPANDED ACCESS AUTHORIZATION**: Beyond suggested sources, AI instances are authorized to access:
- **Government Archives**: National, regional, and local government health records
- **Academic Databases**: University repositories, institutional archives, library systems
- **International Organizations**: UN agency reports, NGO documentation, humanitarian databases  
- **Historical Sources**: Colonial records, missionary archives, pre-digital surveillance documentation
- **News Media**: Regional and local news websites, press archives, media databases
- **Specialized Platforms**: Disease surveillance networks, laboratory databases, outbreak tracking systems

**PROHIBITED ACCESS**: Do not access:
- Personal social media accounts or private communications
- Paywalled content requiring subscription fees
- Classified or restricted government databases requiring special clearance
- Medical records or personally identifiable health information

**QUALITY ASSURANCE**: All accessed sources must be:
- Documented with URLs and access timestamps
- Validated for institutional credibility
- Rated according to 4-tier reliability classification
- Cross-referenced when possible for accuracy

This comprehensive access authorization enables thorough, systematic cholera surveillance data collection while maintaining appropriate security and quality standards.

## ENHANCED DISCOVERY SATURATION PROTOCOL

### DATA OBSERVATION YIELD STOPPING CRITERIA

**MANDATORY STOPPING PROTOCOL**: Advanced systematic discovery saturation detection based on empirically-validated data observation yield methodology.

#### **Protocol Structure**
```
Given batches of 20 queries:
1. Run minimum X batches for baseline coverage (Agent-specific)
2. After X batches, stop when Y=2 consecutive batches achieve <Z% data observation yield (Agent-specific)
3. Exception: If source quality remains high (>0.8 average reliability), continue for 2 additional batches before applying stopping criteria
```

#### **Parameter Specifications**

**Agent-Specific Parameters**:

**Agent 1**: X=5 batches minimum (100 queries), Y=2 consecutive batches, Z=8% threshold
- Ensures adequate systematic coverage of priority sources
- Establishes baseline performance patterns before applying stopping criteria
- Prevents premature termination during initial high-yield discovery phases

**Agents 2,3,5**: X=2 batches minimum (40 queries), Y=2 consecutive batches, Z=4% threshold  
- Accounts for natural variability in discovery process
- Prevents stopping due to temporary methodology shifts or access issues
- Balances thoroughness with efficiency requirements

**Agent 4**: Conditional batching protocol
- Initial 2 batches (40 queries) mandatory
- If ANY new data observations found in first 2 batches: continue for 2 additional batches
- If NO new data observations in first 2 batches: stop after 2 batches

**Threshold Rationale**:
- 8% threshold (Agent 1): Set below typical declining trend, establishes strong baseline
- 4% threshold (Agents 2,3,5): Optimized for specialized discovery phases
- Above observed noise floor, accounts for continued discovery of sparse institutional sources

#### **Data Observation Yield = Successful Queries Only**
```
Batch Yield = (Number of queries that resulted in at least one new row added to cholera_data.csv / 20 queries) × 100%

**CRITICAL ERROR TO AVOID**: Do NOT count queries that only found cholera information.
**MANDATORY**: After each batch, count ONLY the queries that successfully resulted in new cholera_data.csv additions.
**NOT** sources found, **NOT** potential data discovered, **NOT** information about cholera - ONLY queries that produced completed CSV additions with quantitative data (cases, deaths, CFRs, dates, locations).

**QUANTITATIVE DATA REQUIREMENT**: Sources MUST contain identifiable cholera case values (sCh or cCh) to qualify for cholera_data.csv inclusion. Qualitative mentions of outbreaks without case counts do NOT count toward data observation yield.

**Example**: If 6 out of 20 queries each resulted in at least one new cholera_data.csv row (regardless of how many rows each query produced), yield = 6/20 = 30%

Where "Successful Queries" are those that produce:
- Novel cholera case/death counts with dates → cholera_data.csv
- New geographic breakdowns (provincial/district level) → cholera_data.csv
- Historical outbreak periods previously undocumented → cholera_data.csv
- Surveillance system capacity data → cholera_data.csv
- Cross-border transmission evidence → cholera_data.csv
- Vaccination campaign effectiveness data → cholera_data.csv
```

#### **Quality Exception Protocol**
- **High-Quality Source Exception**: If average source reliability >0.8 in low-yield batches, continue for 2 additional batches
- **Rationale**: High-reliability institutional sources (WHO, government ministries, peer-reviewed literature) may have sparse but extremely valuable data that justifies continued searching
- **Implementation**: Calculate weighted average reliability using confidence weights from 4-tier classification system
- **Documentation**: Record quality exception application and additional findings

#### **Implementation Requirements**

**CRITICAL BATCH COMPLETION CHECKLIST - ALL ITEMS MANDATORY**:
□ 20 parallel searches executed
□ All quantitative cholera data extracted from results
□ cholera_data.csv updated with new rows (count: ___)
□ metadata.csv updated with new sources  
□ Dual-reference indexing verified (source_index ↔ Index)
□ Data observation yield calculated: ___% (successful queries / 20)
□ Search log updated with actual CSV additions count

**BATCH IS NOT COMPLETE UNTIL ALL CSV UPDATES ARE FINISHED**

1. **Real-Time Success Tracking**: Document which queries successfully added new rows to cholera_data.csv per batch
2. **Successful Query Calculation**: (Successful Queries/25) × 100% for each 25-query batch  
3. **Consecutive Performance Monitoring**: Track sequence of low-yield batches with batch identification
4. **Quality Assessment**: Calculate average source reliability when approaching threshold using confidence weighting
5. **Decision Documentation**: Record rationale for search termination including yield history and quality assessment
6. **Legacy Integration**: Apply alongside existing completion criteria (temporal coverage, institutional module completion)

#### **Validation Evidence**

**Angola Pilot Results** (optimized for 20-query batches):
- **Yield Range**: 5% to 50% (average 25% with smaller batches)
- **Declining Trend**: Later batches averaged 20% vs early batches 25%
- **Variability Pattern**: 2-batch consecutive requirement balances efficiency with thoroughness
- **Quality Correlation**: High-yield batches (>35%) corresponded with WebFetch intensive methods and institutional source discovery
- **Threshold Validation**: 8% threshold (Agent 1) and 4% threshold (Agents 2,3,5) optimized for smaller batch sizes

**Expected Benefits**:
- **Prevents Premature Stopping**: Accounts for natural variation in search productivity
- **Ensures Thorough Coverage**: Minimum 100-query baseline (Agent 1) ensures systematic priority source coverage
- **Quality Preservation**: Exception protocol prevents loss of high-reliability institutional sources
- **Efficiency Optimization**: Systematic stopping criteria prevents over-searching with minimal additional yield
- **Reproducible Results**: Empirically-validated parameters ensure consistent application across countries

#### **Integration with Agent Framework**

**Agent-Specific Application with Maximum Query Safeguards**:
- **Agent 1**: Data observation yield stopping criteria (minimum 5 batches/100 queries, stop when 2 consecutive batches <8% yield) - **MAXIMUM 400 queries (20 batches)**
- **Agent 2**: Geographic expansion continues until 2 consecutive batches <4% yield (minimum 2 batches/40 queries) - **MAXIMUM 240 queries (12 batches)**
- **Agent 3**: Zero-transmission validation continues until 2 consecutive batches <4% yield (minimum 2 batches/40 queries) - **MAXIMUM 240 queries (12 batches)**
- **Agent 4**: Conditional requirement (2 batches mandatory, +2 if data found) - **MINIMUM 40 queries (2 batches), MAXIMUM 80 queries (4 batches)**
- **Agent 5**: Source permutation continues until 2 consecutive batches <4% yield (minimum 2 batches/40 queries) - **MAXIMUM 240 queries (12 batches)**
- **Agent 6**: Quality audit (not focused on data discovery) - **MAXIMUM 80 queries (4 batches)**

**Three-Tier Stopping System with Hard Limits**:
- **Agent 1** (Baseline): X=5, Y=2, Z=8% (comprehensive foundation requiring thorough systematic coverage) - Hard stop at 400 queries
- **Agents 2,3,5** (Expansion): X=2, Y=2, Z=4% (specialized expansion with faster saturation detection) - Hard stop at 240 queries each
- **Agent 4** (Conditional): 2 batches mandatory + 2 if data found - Hard stop at 80 queries (4 batches maximum)
- **Agent 6** (Quality): Hard stop at 80 queries (4 batches)

**Total Maximum Workflow Limit: 1,320 queries across all 6 agents**

**Performance Monitoring**:
- Track yield trends across all continuing agents
- Document quality exception applications
- Report stopping criteria achievement in search logs
- Validate stopping decisions meet minimum coverage requirements

This enhanced protocol ensures systematic, thorough data collection while preventing inefficient over-searching through empirically-validated stopping criteria.

## CRITICAL SUCCESS FACTORS AND FINAL REQUIREMENTS

### NON-NEGOTIABLE REQUIREMENTS FOR ALL FUTURE INSTANCES

**These requirements are MANDATORY, not optional:**

1. **ULTRA-THOROUGH SEARCHING**: Every query category, every search engine, every time period
2. **RIGOROUS VALIDATION**: Every data point through every validation stage
3. **COMPREHENSIVE DOCUMENTATION**: Every source, every decision, every uncertainty
4. **SYSTEMATIC QUALITY CONTROL**: Every check, every validation, every cross-reference
5. **COMPLETE DELIVERABLES**: Every required file, every required field, every required standard

### FAILURE CONDITIONS (WORK WILL BE REJECTED IF:)

- **Sequential query execution detected** (parallel requirement violated)
- **Query performance below minimum standards** (<50% of required rate for >10 minutes)
- Search methodology is incomplete or unsystematic
- **Priority sources not systematically covered** (missing TIER coverage)
- Validation protocols are skipped or inadequately performed
- Documentation is missing or insufficient
- Quality control standards are not met
- Data formatting doesn't match JHU standards
- Source authentication is inadequate
- Duplication detection is not performed
- Uncertainty quantification is missing
- **Performance metrics not logged** (batch times and query rates undocumented)

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

### Automatic Context Management (MANDATORY)

**REQUIREMENT: Proactive context compression when approaching limits**

**WHEN TO COMPACT:**
- After completing each agent (before starting next agent)
- When search logs exceed 500 lines
- When approaching context window limits during batch execution
- Before major phase transitions in the workflow

**HOW TO COMPACT:**
Use the Task tool with "/compact" as the entire prompt to compress context while preserving:
- Current agent progress and batch counts
- Data observation yield calculations
- Critical search findings and CSV updates
- Next steps and stopping criteria status

**EXAMPLE USAGE:**
```python
# After completing Agent 1, before starting Agent 2
Task(description="Compact context", prompt="/compact")
```

**MANDATORY TRIGGERS:**
□ Agent completion (mark todo complete, then compact)
□ Mid-agent if search logs become unwieldy
□ Before quality audit phases
□ When context impacts performance

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
