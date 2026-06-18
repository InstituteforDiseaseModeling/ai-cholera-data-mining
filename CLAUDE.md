# CLAUDE.md - AI Cholera Surveillance Data Enhancement

**Mission**: Enhance integrated JHU/WHO baseline cholera surveillance data (1970-present) by systematically filling identified gaps through AI-driven discovery, validation, and integration of additional cholera data sources.

**Strategy**: Gap-targeted systematic internet searches to discover unreported transmission events and validate zero-transmission periods, building on integrated JHU historical database and WHO dashboard baseline data.

**Important Note: While this project is open source, it remains an experimental pilot study and the AI-generated data have not yet been fully validated by human experts. Data posted here may change over time as we refine methods. All data should be independently verified before use.**

**CRITICAL SCOPE RESTRICTION**: AI cholera data collection is **RESTRICTED TO THE 40 MOSAIC FRAMEWORK COUNTRIES ONLY**. Do not process any countries outside the MOSAIC framework. The analysis scope is limited to these 40 core modeling countries.

## Data Sources & Hierarchy

**Separate Source Files Architecture**: Each country now maintains separate baseline data files:
- `./data/{ISO}/cholera_data_jhu.csv` - JHU historical database (1970-2020+ surveillance data)
- `./data/{ISO}/cholera_data_who.csv` - WHO dashboard data (recent 2023-2025 surveillance)  
- `./data/{ISO}/cholera_data_ai.csv` - AI discoveries (agents work with this file only)

**AI Enhancement Tiers**: Level 1 (WHO/MoH) → Level 2 (UNICEF/Academic) → Level 3 (News/NGO) → Level 4 (Local/Social)  
**Data Architecture**: Separate JHU/WHO baseline files → AI gap-filling enhancement (cholera_data_ai.csv) → Validated enhanced dataset

## Core Methodology

**Workflow**: Integrated baseline analysis → Gap identification → AI systematic enhancement → Data validation  
**Output Format**: Enhanced cholera_data_ai.csv with AI discoveries using dual-reference indexing, separate from JHU/WHO baseline files  
**Deliverables**: search_report.txt, enhanced metadata_ai.csv, enhanced cholera_data_ai.csv, individual search_log_agent_X.txt files
**Progress Tracking**: dashboard/completion_checklist.csv (automatically updated from file system analysis)
**Gap Analysis**: `py/analyze_baseline_gaps_optimized.py` generates baseline surveillance gap files from JHU/WHO data

## Orchestrator-Based Workflow Architecture

**NEW WORKFLOW EXECUTION MODEL**: The system now uses a **workflow orchestrator** pattern for systematic country-specific data enhancement.

**ORCHESTRATOR DASHBOARD MANAGEMENT**: The workflow orchestrator (Agent 0) handles all dashboard updates automatically. Individual agents (1-7) focus solely on data collection without dashboard update responsibilities.

### Country-Specific Orchestrator Files

**Location**: `./data/{ISO_CODE}`
**Purpose**: Pre-configured, country-specific instructions for complete 7-agent workflow execution
**Generation**: Use `python py/generate_country_prompt.py {ISO_CODE}` to create the prompt file that initiates the workflow-orchestrator

### Specialized Subagent Architecture

**Location**: `.claude/agents` - Individual agent configurations and system prompts
**Access Method**: Use the `Task()` tool with specific subagent_type parameters:
- `cholera-baseline-collector` (Agent 1)
- `geographic-expansion-specialist` (Agent 2)  
- `zero-transmission-validator` (Agent 3)
- `obscure-source-explorer` (Agent 4)
- `cross-reference-integrator` (Agent 5)
- `gap-context-investigator` (Agent 6)
- `cholera-quality-auditor` (Agent 7)

### Workflow Execution Protocol

Use orchestrator files with `Task()` tool for country-specific workflow execution.

#### Step 1: Generate/Load Prompt File
```bash
# Generate country-specific prompt (if not exists)
python py/generate_country_prompt.py {ISO_CODE}

# Example: Generate for Ethiopia
python py/generate_country_prompt.py ETH
```

#### Step 2: Execute Orchestrator-Based Workflow
```python
# The prompt file contains a Task command to initiate the workflow-orchestrator
# Example content of prompt_AGO.txt:
Task(description="Angola cholera workflow", prompt="AGO", subagent_type="workflow-orchestrator")

# The workflow-orchestrator then manages all 7 agents automatically:
# - Agent 1: Baseline Collection (cholera-baseline-collector)
# - Agent 2: Geographic Expansion (geographic-expansion-specialist)
# - Agent 3: Zero-Transmission Validation (zero-transmission-validator)
# - Agent 4: Obscure Source Exploration (obscure-source-explorer)
# - Agent 5: Cross-Reference Integration (cross-reference-integrator)
# - Agent 6: Gap Context Investigation (gap-context-investigator)
# - Agent 7: Quality Audit (cholera-quality-auditor)
```

#### Step 3: Monitor Progress
The dashboard is automatically updated at workflow initialization and final completion only. Individual agents do not need to update the dashboard.

## Dashboard Management

### **AUTOMATED DASHBOARD SYSTEM** (Agents: READ-ONLY Awareness)

Dashboard updates now occur only at workflow initialization and completion.

**Automated Update System**:
```bash
# Unified dashboard update (completion checklist + timeline plots + embedded data)
bash update_dashboard.sh
```

### **AGENT RESPONSIBILITIES**:

**✅ FOCUS ON DATA COLLECTION:**
- Create/update cholera_data_ai.csv and metadata_ai.csv files (all agents)
- Complete individual agent search logs (see Agent Operations Framework)
- Generate quality audit and brief search_report.txt (Agent 7 only)
- Document all work in proper file formats

**❌ DO NOT MANUALLY UPDATE DASHBOARD:**
Only orchestrator does this at initialization and completion.


## MANDATORY GAP-TARGETED SEARCH PROTOCOL

**Note on search protocol sections**: This document contains three search protocol sections (Gap-Targeted Protocol, Ultra Deep Search Methodology, and Three-Phase Search Protocol in the Batch Processing section). These are complementary, not competing — they describe the same workflow from different angles. **Priority order**: (1) Always load gap files and target identified gaps first. (2) Apply ultra-deep multi-source coverage within each batch. (3) Follow the three-phase structure across the agent's full search run.

**CRITICAL**: Before beginning any search, agents MUST consult the baseline surveillance gap analysis files to target missing periods in baseline data.

### Pre-Search Requirements (MANDATORY)

1. **Load Baseline Gap Analysis Files**: Read baseline gap analysis files generated from JHU/WHO integrated baseline data
2. **All Agents Must Load**:
   - `./reference/baseline_surveillance_gaps_annual.csv` - Years with ≥6 months missing data
   - `./reference/baseline_surveillance_gaps_detailed.csv` - Consolidated gap periods with exact dates
   - `./reference/baseline_surveillance_gaps_coverage.csv` - Country-level coverage summary
3. **Identify Target Periods**: Focus searches on specific date ranges identified in baseline gaps
4. **Apply Exhaustive Search Strategy**: Target ALL surveillance gaps equally with comprehensive searches
   - No coverage-based allocation - all gaps receive equal search effort
   - Systematic coverage of every identified gap period
   - Comprehensive searches regardless of baseline coverage percentage
5. **Document Gap Targeting**: Record which gaps were searched and results obtained
### Enhanced Gap-Targeted Query Strategy

**MANDATORY QUERY MODIFICATION**: All searches must include temporal constraints targeting missing periods with enhanced contextual targeting using the comprehensive gap analysis data.

#### **Standard Query Enhancement:**
**Basic Query**: `"Angola cholera outbreak WHO"`
**Enhanced Gap-Targeted Query**: `"Angola national cholera outbreak WHO dry season 2019-2025 surveillance following minimal outbreak Luanda"`

#### **Context-Enhanced Query Templates:**

**Geographic Context Queries**:
- `"{Country} {geographic_level} cholera cases {gap_start_year}-{gap_end_year}"` 
- `"{Country} {specific_province} cholera surveillance {gap_period}"`
- `"{Country} {district_name} cholera outbreak {seasonal_context}"`

**Seasonal Context Queries**:
- `"{Country} cholera {seasonal_context} {gap_years}"` (e.g., "Ethiopia cholera dry season 2019-2022")
- `"{Country} cholera rainy season outbreak {gap_period}"` 
- `"{Country} cholera flooding epidemic {specific_dates}"`

**Outbreak Scale Context Queries**:
- `"{Country} cholera following {preceding_outbreak_scale} outbreak {gap_period}"` 
- `"{Country} cholera surveillance after {outbreak_magnitude} epidemic {gap_dates}"`
- `"{Country} cholera cases between {preceding_location} {following_location} outbreaks"`


### Reference File Usage Protocol

**baseline_surveillance_gaps_annual.csv Usage**:
- Long format: country, iso_code, gap_year, months_missing
- Lists all years with ≥6 months of missing baseline data
- Use for year-specific gap targeting

**baseline_surveillance_gaps_detailed.csv Usage**:
- Consolidated periods: country, iso_code, gap_start, gap_end, days, months, years
- Provides exact date ranges for all gaps ≥7 days
- Use for precise temporal targeting

**baseline_surveillance_gaps_coverage.csv Usage**:
- Summary: country, iso_code, total_months, months_with_data, months_missing, percent_coverage, data_years, missing_years
- Provides country-level overview for search allocation
- Use to determine search effort distribution
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

**Gap Validation Searches**:
- "Ethiopia cholera-free 2019 2020 2021" (confirm no disease)
- "Ethiopia surveillance system 2019-2022" (check reporting gaps)
- "Ethiopia neighboring countries cholera 2019-2022" (regional context)

**CRITICAL RESULT EXPECTATION**: Either fill identified gaps with data OR confirm no cholera transmission with evidence


### **Gap-Specific Search Strategies**

**Seasonal Context Targeting**:
- **dry_season gaps**: Target water scarcity, drought monitoring, health system reports
- **rainy_season gaps**: Target flooding, WASH disruption, refugee/displacement reports  
- **pre_rainy gaps**: Target preparation, vaccination campaigns, early warning systems
- **post_rainy gaps**: Target recovery, surveillance strengthening, outbreak aftermath

**Geographic Level Targeting**:
- **national gaps**: Target WHO country reports, government health ministry data, academic papers
- **provincial gaps**: Target regional WHO offices, provincial health departments, NGO field reports
- **district gaps**: Target local health centers, district surveillance, community health programs
- **municipal gaps**: Target urban health systems, refugee camps, border health posts

**Outbreak Scale Context Targeting**:
- **Following major/large outbreaks**: Search for epidemic aftermath, system recovery, lessons learned
- **Following minimal/small outbreaks**: Search for early detection, rapid response, containment efforts
- **Between outbreak periods**: Focus on surveillance system validation, zero-transmission confirmation

### **Step 5: Mandatory Gap Documentation**

**For each targeted gap, agents must**:
1. **Document Search Attempts**: Record which gaps were searched with what queries
2. **Document Results**: Note if gap was filled with data or validated as zero-transmission
3. **Document Remaining Gaps**: Identify gaps that still need attention
4. **Update Gap Status**: Mark gaps as addressed/validated/remaining in search logs

**Search Log Template Enhancement**:
```
=== GAP-TARGETED SEARCH BATCH X ===
Target Gap: {country} {gap_start} to {gap_end} ({gap_days} days)
Context: Year with {months_missing} months missing baseline data
Queries Executed: [list enhanced queries with context]
Results: [data found/zero-transmission validated/gap remains]
CSV Updates: [specific rows added to cholera_data_ai.csv]
Gap Status: FILLED/VALIDATED/REMAINING
```

## INTEGRATED BASELINE DATA ANALYSIS

**FOUNDATION**: All countries start with separate baseline data for systematic gap-targeted enhancement

### Baseline Data Structure
- **JHU Historical Database**: `./data/{ISO}/cholera_data_jhu.csv` - Comprehensive 1970-2020+ cholera surveillance data (source_database: 'JHU')
- **WHO Dashboard Data**: `./data/{ISO}/cholera_data_who.csv` - Recent 2023-2025 surveillance updates (source_database: 'WHO')  
- **AI Enhancement Target**: `./data/{ISO}/cholera_data_ai.csv` - Fill gaps and add discoveries (source_database: 'AI')

**AGENT WORKFLOW**: Agents work exclusively with `cholera_data_ai.csv` to add new discoveries while baseline files remain separate for integration


### Coverage Metrics Calculation
- **Coverage Percentage**: Months with ≥50% days covered by observations / total months in surveillance period
- **Gap Detection**: Periods ≥7 days without meaningful cholera data in baseline
- **Exhaustive Search Strategy**: All gaps treated equally with comprehensive, exhaustive searches regardless of coverage percentage
- **Meaningful Observations**: Data rows with sCh>0 OR deaths>0 OR cCh>0 (excluding administrative records)

### Visual Coverage Analysis
```bash
# Generate coverage heatmap showing temporal patterns by data source
python py/generate_coverage_heatmap.py
```
**Output**: `./figures/cholera_coverage_heatmap.png` - Countries×Years heatmap colored by JHU/WHO/AI sources

## ULTRA DEEP SEARCH METHODOLOGY

**CRITICAL**: Exhaustive, systematic internet searches across ALL discoverable sources.

### Search Strategy
**Multi-Engine Protocol**: 15+ search engines/databases per country  
**Query Framework**: 7 mandatory categories, 50+ unique queries minimum  
**Source Coverage**: 486 tiered domains in reference/priority_sources.txt + expansion

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


## Data Standards

**Directory**: `data/{ISO_CODE}/`  
**Files**: See Agent Operations Framework for complete file outputs
**Baseline Files**: cholera_data_jhu.csv, cholera_data_who.csv (separate baseline data, read-only for agents)

### DUAL-REFERENCE INDEXING SYSTEM

**CRITICAL**: Mandatory enhanced indexing for data integrity

**Protocol**: Sequential integer indices (1,2,3...) + exact source names  
**Benefit**: Automated processing + human readability + error prevention  
**Format**: metadata_ai.csv Index column ↔ cholera_data_ai.csv source_index column

## FILE FORMAT SPECIFICATIONS

### Required Files and Structure

**Directory**: `data/{ISO_CODE}/`

#### Core Data Files

**cholera_data_ai.csv** (14 columns):
- Index, Location, TL, TR, deaths, sCh, cCh, CFR, reporting_date, source_index, source, confidence_weight, processing_notes, source_database
- **Dual-Reference System**: source_index (integer) ↔ metadata Index column + source (exact name match)
- **Date Format**: YYYY-MM-DD for all date fields
- **Location Format**: AFR::{ISO} location codes

**metadata_ai.csv** (15 columns):
- Index, Source, URL, Description, Date_Range, Data_Type, Status, Reliability_Level, Validation_Status, Search_Technique, Language_Original, Citation_Depth, Cross_References, Discovery_Method, source_database
- **Index Column**: Sequential integers (1, 2, 3...) - MANDATORY for dual-reference system
- **Consistent Naming**: Source names must be used exactly in cholera_data_ai.csv

#### Supporting Files

**search_report.txt**:
- Brief summary created by Agent 7 only
- Include: total sources discovered, total data observations added, key gaps filled, overall data quality assessment, remaining limitations

**search_log_agent_X.txt**:
- Individual logs for each agent (see Agent Operations Framework)
- Document search batches, queries, results, and CSV updates

**Baseline Files** (read-only):
- cholera_data_jhu.csv - JHU historical database (1970-2020+)
- cholera_data_who.csv - WHO dashboard data (2023-2025)

### MANDATORY Format Requirements

1. **Index System Integrity**:
   - Metadata CSV MUST have Index column with sequential integers
   - Data CSV MUST have source_index column matching metadata indices
   - Data CSV source names MUST exactly match metadata Source column
   - All data rows MUST have both source_index AND source columns populated
   - No index numbers can be duplicated or missing in metadata

2. **Data Type Standards**:
   - Dates: YYYY-MM-DD format only
   - Integers: deaths, sCh, cCh must be positive integers or empty
   - Decimals: CFR (0-100), confidence_weight (0.1-1.0)
   - Text: UTF-8 encoding for all text fields

3. **Quality Assurance**:
   - All files must pass format validation before submission
   - Maintain consistent column order as specified
   - No additional columns without prior approval

**CRITICAL**: Agents work exclusively with cholera_data_ai.csv and metadata_ai.csv files. Baseline files are read-only references for gap analysis.

## COMPREHENSIVE COLUMN DEFINITIONS

### cholera_data_ai.csv Column Specifications

**Location** (CRITICAL - Geographic Administrative Units ONLY):
- **Purpose**: Geographic administrative unit where cholera cases/deaths occurred
- **Format**: `AFR::{ISO}` (national), `AFR::{ISO}::{PROVINCE}` (provincial), `AFR::{ISO}::{PROVINCE}::{DISTRICT}` (district)
- **ACCEPTABLE**: `AFR::AGO`, `AFR::AGO::Luanda`, `AFR::AGO::Luanda::Belas`, `AFR::AGO::Multi_Provincial`
- **PROHIBITED**: Any non-geographic categories (Vaccination, Training, Demographics_*, Age_Group_*, Laboratory_*, Surveillance_*)
- **Rule**: Must represent a physical location where people contracted cholera
- **Double-counting warning**: When both national (AFR::ISO) and provincial rows exist for the same date range, document in `processing_notes` which level is intended as the primary count for MOSAIC aggregation (e.g., "National total — includes provinces not individually listed" or "Provincial subset — do not sum with national row"). This prevents double-counting in likelihood calculations.

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
- **Validation**: Must be 0.1-15% for most outbreaks (flag outliers). Humanitarian/conflict settings may reach ~20% — document context. Multi-year aggregated CFR entries should receive confidence_weight ≤0.7.

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

**source_database** (Text):
- **Purpose**: Track data provenance across different source systems
- **Format**: Controlled vocabulary: 'JHU', 'WHO', 'AI'
- **Values**: 
  - 'JHU': Data from JHU cholera database baseline integration (historical coverage)
  - 'WHO': Data from WHO surveillance dashboards and emergency reports (2023-2025 coverage)
  - 'AI': Data extracted by AI agents during systematic searches. This field tracks collection method, not source originality — use 'AI' even if the underlying source was WHO or JHU, as long as the row was discovered/extracted by an agent (not pre-loaded from the baseline files). Agent confirmation of a baseline-source entry also uses 'AI'.
- **Required**: All data rows must have source_database classification
- **Baseline Integration**: Countries now begin with dual-source baseline combining JHU historical data with WHO recent surveillance

## CRITICAL DATA INCLUSION RULES

### MANDATORY Requirements for cholera_data_ai.csv Entry:
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

## DATA EXTRACTION AND DOCUMENTATION REQUIREMENTS

**MANDATORY**: Comprehensive documentation and validation for ALL data extraction decisions

### Pre-Extraction Validation Checklist

**BEFORE ADDING ANY ROW to cholera_data_ai.csv:**
□ Location is geographic administrative unit (not program/demographic category)
□ sCh or cCh contains actual cholera case numbers (not vaccination/population/capacity)
□ Source explicitly mentions cholera cases/deaths (not just cholera programs)
□ Numbers represent disease incidence (not prevention/demographics/training)
□ Processing notes include exact source quote supporting interpretation
□ Number explicitly described as cholera "cases" (not vaccinated, population, density)
□ Source context indicates disease incidence (not prevention/demographics)
□ Validate units are case counts, not rates/coverage/capacity

### Critical Field Validations

#### sCh/cCh Column Quality Control
**High-Risk Context Flags - EXTRA VALIDATION REQUIRED:**
- Vaccination reports → likely vaccinated count, not cases
- Demographics → likely population, not cases  
- WASH assessments → likely coverage, not cases

**ACCEPT**: "cases", "infections", "ill", "hospitalized", "patients", "affected individuals"
**REJECT**: "affected", "targeted", "covered", "population", "beneficiaries", "doses"

#### Mandatory Extended Thinking Requirement
**USE EXTENDED ULTRATHINK WHEN:**
□ Synthesizing data from multiple sources
□ Interpreting ambiguous numbers or context
□ Performing any cross-validation between sources
□ Resolving conflicts between different reports
□ Determining if numbers represent cases vs. other metrics

**THINK THROUGH**: Context clues, source credibility, temporal alignment, epidemiological plausibility, alternative interpretations

### Documentation Standards

#### 1. Original Format Preservation
- Screenshot or copy original data presentation
- Record exact text, numbers, dates as presented
- Note table/figure numbers, page numbers, section locations
- Save PDF copies when possible
- Document access date and URL status

#### 2. Extraction Decision Documentation
- Record every interpretive decision made
- Document ambiguous data handling
- Note assumptions about missing information
- Explain unit conversions step-by-step
- Record alternative interpretations considered

#### 3. Traceability Requirements
- Direct quotes for key data points
- Page/section references for all extracted data
- Author contact information when available
- Publication DOI/URL for all sources
- Version information for updated reports

#### 4. Processing Notes Format
**MANDATORY**: processing_notes MUST include: "Source states: '[exact quote]' - interpreted as [sCh/cCh] cases"

**Example**: "Source states: 'A total of 1,234 cholera patients were admitted to treatment centers' - interpreted as 1234 sCh cases"

### Quality Assurance During Extraction

**MANDATORY CHECKS:**
1. **Double-entry verification**: Re-extract key data points to check consistency
2. **Mathematical validation**: Verify calculated fields (CFR, attack rates)
3. **Unit consistency**: Ensure all conversions are correct
4. **Date logic**: Verify temporal relationships make sense
5. **Geographic accuracy**: Confirm location codes and names

### Uncertainty Quantification

**REQUIREMENT: Flag and quantify all uncertainties**
1. **High Certainty**: Direct, unambiguous data extraction
2. **Medium Certainty**: Minor interpretation or conversion required
3. **Low Certainty**: Significant assumptions or ambiguous source
4. **Provisional**: Major uncertainties, requires verification

### Tiered Cross-Validation Framework

**TIER 1: High-Value Cases (>1000 cases)**
- REQUIRE: 2+ independent sources for major outbreaks
- USE ULTRATHINK: Compare sources, resolve discrepancies

**TIER 2: Moderate Cases (100-1000 cases)**  
- ENCOURAGE: Seek secondary confirmation when possible
- ACCEPT: Single high-quality source (Level 1-2)
- FLAG: Note single-source status

**TIER 3: Small Cases (<100 cases)**
- ACCEPT: Single source with appropriate confidence weighting

**CROSS-VALIDATION TRIGGERS (REQUIRE 2+ SOURCES):**
□ Cases >1000 (major outbreak)
□ First outbreak in new geographic area
□ Dates conflict with regional patterns

### Data Inclusion Rules Summary

**MANDATORY Requirements for cholera_data_ai.csv Entry:**
1. **Geographic Location**: Must be actual administrative unit (country/province/district)
2. **Quantitative Data**: Must have specific numbers for cases, deaths, or CFR
3. **Cholera-Specific**: Must be cholera cases/deaths, not vaccination/training/capacity data
4. **Source Attribution**: Must have matching metadata entry with working source

**PROHIBITED Entries (DO NOT ADD):**
- **Vaccination Data**: `AFR::{ISO}::Vaccination`, `AFR::{ISO}::OCV_Campaign`
- **Training Data**: `AFR::{ISO}::Training`, `AFR::{ISO}::Health_Workers`
- **Demographics Without Location**: `AFR::{ISO}::Demographics_*`, `AFR::{ISO}::Age_*`
- **System Capacity**: `AFR::{ISO}::Laboratory_*`, `AFR::{ISO}::Surveillance_*`
- **Population Data**: Population denominators, coverage percentages, capacity figures

### Integration with Validation Framework

All extracted data must pass through the complete 4-stage validation protocol outlined in the Data Quality and Validation Framework before final inclusion in cholera_data_ai.csv.

**MANDATORY DATA INCLUSION REQUIREMENT**: Agents are **PROHIBITED** from adding any data observations (rows) to cholera_data_ai.csv unless they can identify at least one cholera case value (sCh or cCh) **OR** can document a confirmed zero-transmission period. Sources that only mention cholera outbreaks without providing quantitative case counts **MUST NOT** be included in the data file. Only sources with identifiable case numbers, death counts, calculable epidemiological metrics, or validated absence periods qualify for data extraction.

## MANDATORY ZERO-TRANSMISSION DOCUMENTATION PROTOCOL

**CRITICAL REQUIREMENT**: All validated cholera-free periods MUST be documented as data observations in cholera_data_ai.csv. This is not optional - absence periods are as epidemiologically important as outbreak periods for MOSAIC modeling.

### Zero-Transmission Data Entry Format

```
Location: AFR::{ISO} (national level for absence periods)
TL: YYYY-01-01 (start of absence period)  
TR: YYYY-12-31 (end of absence period)
deaths: 0
sCh: 0
cCh: (empty)
CFR: 0.0
reporting_date: End date + 1 day
source_index: [metadata reference]
source: [WHO surveillance confirmation or academic validation]
confidence_weight: 0.8-1.0 (based on surveillance system quality)
processing_notes: "Source confirms zero cholera transmission during [period] - validated absence via [surveillance system/WHO reporting]. Surveillance system status during absence: [operational/disrupted/unknown]. Evidence type: [Documented_Absence from WHO report / Inferred_Absence from gap analysis / Surveillance_Gap with no positive evidence]."
source_database: AI
```

### Mandatory Zero-Transmission Entry Triggers

1. **Gap Periods Validated**: Any period >1 year between documented outbreaks where surveillance confirms no cases
2. **WHO "Zero Reporting"**: Official surveillance data showing no cholera cases for specific years
3. **Academic Documentation**: Peer-reviewed studies confirming absence periods (e.g., "decade-long absence 1997-2006")
4. **Surveillance System Validation**: Evidence of functioning disease surveillance during cholera-free periods
5. **Regional Context**: Confirmed absence during periods when neighboring countries had outbreaks

### Examples of Required Zero-Transmission Entries

- WHO surveillance reports: "no cholera cases reported in [Country] during [Year]" → MANDATORY cholera_data_ai.csv entry
- Academic studies: "decade-long absence 1997-2006" → MANDATORY cholera_data_ai.csv entries for each year or period
- Government reports: "cholera-free period following end of civil war" → MANDATORY cholera_data_ai.csv entry
- Regional analysis: "Country X remained cholera-free while neighbors experienced outbreaks" → MANDATORY cholera_data_ai.csv entry

### Source Requirements for Zero-Transmission Entries

- WHO surveillance reports explicitly stating "no cases reported"
- Academic literature documenting absence periods with epidemiological evidence
- Government health ministry annual reports confirming zero cholera cases
- Regional surveillance networks documenting cholera-free status
- Cross-border analysis confirming absence despite regional transmission

### Quality Standards for Absence Documentation

- **Level 1 (1.0 weight)**: WHO official surveillance confirming zero cases
- **Level 1 (0.9 weight)**: Academic studies with epidemiological evidence of absence
- **Level 2 (0.8 weight)**: Government reports confirming cholera-free periods
- **Level 3 (0.7 weight)**: Inferred absence from regional surveillance patterns

### Mandatory Validation Requirements

1. **Surveillance System Functioning**: Evidence that disease surveillance was operational during absence period
2. **Regional Consistency**: Cross-check with neighboring countries' outbreak patterns
3. **Historical Continuity**: Validate absence periods fit within known outbreak cycles
4. **Duration Plausibility**: Confirm absence duration is epidemiologically reasonable (typically 1-10 years)
5. **Documentation Quality**: Ensure source explicitly confirms absence rather than just lack of reporting

### Quality Impact of Zero-Transmission Documentation

Zero-transmission documentation is essential for:
1. **Complete time series**: MOSAIC models require knowledge of both presence AND absence of disease
2. **Accurate transmission modeling**: Understanding when/why cholera is absent informs transmission parameters
3. **Public health planning**: Documented cholera-free periods guide resource allocation and preparedness
4. **Regional analysis**: Cross-border transmission patterns depend on accurate absence documentation
5. **Intervention effectiveness**: Measuring success requires documenting sustained absence periods

### Agent Responsibilities for Zero-Transmission

- **Agent 1**: Document any zero-transmission periods discovered during baseline searches
- **Agent 2**: Document provincial-level absence periods where surveillance confirms zero cases
- **Agent 3**: PRIMARY RESPONSIBILITY - systematically validate and document ALL cholera-free periods
- **All Agents**: If absence periods are identified, MANDATORY documentation in cholera_data_ai.csv

### Validation Standards

Zero-transmission entries require the same validation rigor as outbreak data - appropriate confidence weighting, source documentation, and cross-reference validation. All zero-transmission entries must pass through the complete 4-stage validation protocol outlined in the Data Quality and Validation Framework.


**Requirements**: Dual-reference system (source_index ↔ Index), exact name matching, YYYY-MM-DD dates, AFR::{ISO} location codes

## DATA QUALITY AND VALIDATION FRAMEWORK

**CRITICAL**: Mandatory 4-stage validation for ALL sources and data points

### Source Reliability Levels

**Level 1 (0.9-1.0)**: WHO, MoH, peer-reviewed journals, government statistics  
**Level 2 (0.7-0.9)**: UNICEF, OCHA, established NGOs, regional organizations  
**Level 3 (0.3-0.6)**: Reputable news, local government, preliminary academic reports  
**Level 4 (0.1-0.3)**: Local media, social media, unofficial reports (extreme caution)

### Comprehensive Validation Protocol (4 Stages)

#### Stage 1: Authentication and Source Verification
- **URL Validation**: Test all links, use archived versions if current links fail
- **Author Credentials**: Verify institutional affiliations and expertise
- **Domain Validation**: Confirm official government/organization websites
- **Publication Verification**: Confirm journal indexing, peer review status
- **Archive Search**: Use Internet Archive for broken or moved content

#### Stage 2: Data Quality and Epidemiological Validation
**Epidemiological Range Validation**:
- CFR between 0.1% and 15% for most outbreaks (flag outliers for manual review). Note: humanitarian/conflict settings may legitimately exceed 5% (up to ~20%) due to treatment access collapse — do not auto-reject these; document context in processing_notes. CFRs derived from multi-year aggregated data (>2 years) should use confidence_weight ≤0.7 regardless of source quality.
- Case numbers > 0 and < population of affected area
- Outbreak duration between 1 week and 104 weeks (2 years)
- Attack rates between 0.01% and 10% of population
- Deaths ≤ suspected cases (mathematical consistency)

**Temporal Logic Validation**:
- Start date < End date
- Reporting date ≥ End date
- No dates in the future beyond data collection
- Seasonal patterns consistent with regional cholera epidemiology
- Multi-year trends follow epidemiologically plausible patterns

**Geographic Validation**:
- Location codes match ISO/WHO standards
- Administrative hierarchy consistency (Country→Province→District)
- Coordinates within correct administrative boundaries
- Population denominators match latest census data
- Cross-border patterns epidemiologically plausible

#### Stage 3: Cross-Reference and Expert Validation
**Multi-Source Confirmation Requirements**:
- Outbreaks >1000 cases: Require ≥2 independent sources
- CFR >5%: Require clinical confirmation sources
- New geographic areas: Cross-check with neighboring regions
- Historical data: Verify against WHO annual summaries

**Mathematical and Pattern Consistency**:
- CFR calculations accurate to ±0.1%
- Cumulative totals match sub-period sums
- Attack rates consistent with population denominators
- Case progression follows epidemic curve logic
- Seasonal trends match known cholera epidemiology
- Geographic spread follows transmission pathways
- Outbreak magnitude consistent with preparedness capacity
- Recovery rates align with treatment availability

**Expert Review Requirements**:
- Epidemiological plausibility assessment
- Historical context validation
- Source credibility evaluation
- Methodology transparency and soundness
- Data collection standards documented

#### Stage 4: Final Integration and Duplication Checks
**Duplication Prevention**:
- No identical records from different sources
- Overlapping periods resolved using best available data
- Updated reports supersede preliminary versions
- Aggregated data doesn't double-count sub-national data

**Integration Validation**:
- New data compatible with existing JHU database
- All required fields populated or explicitly marked missing
- Geographic coding complete and standardized
- Source attribution clear and traceable
- No systematic biases introduced
- Coverage gaps appropriately filled
- Confidence weights appropriately assigned

### Quality Control Documentation Requirements

**MANDATORY for each data point:**
1. **Validation Status**: Pass/Fail for each validation stage
2. **Flag Reasons**: Specific issues identified during validation
3. **Resolution Actions**: How validation issues were addressed
4. **Final Quality Score**: Numerical rating (1-10) based on validation
5. **Reviewer Notes**: Human expert assessment comments
6. **Uncertainty Quantification**: Confidence intervals where applicable

### Rejection and Review Criteria

**Automatically reject data if:**
- CFR > 100% without exceptional circumstances documentation
- Case numbers exceed 100% of population (implausible attack rates)
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

### Quality Assurance Metrics

**Track and report:**
1. **Validation Pass Rates**: Percentage passing each validation stage
2. **Source Distribution**: Breakdown by reliability level
3. **Geographic Coverage**: Administrative levels represented
4. **Temporal Coverage**: Years and periods covered
5. **Data Density**: Records per year/region
6. **Quality Scores**: Distribution of final quality ratings
7. **Rejection Rates**: Reasons for data exclusion
8. **Uncertainty Levels**: Distribution of confidence weights

### Quality Improvement Feedback Loop

**MANDATORY: Continuously improve process**
1. **Pattern Recognition**: Identify common validation failures
2. **Search Optimization**: Adjust queries based on success rates
3. **Source Prioritization**: Focus on highest-yield source types
4. **Validation Refinement**: Update validation rules based on experience
5. **Documentation Enhancement**: Improve guidance based on lessons learned

**Quality Flags**: HIGH/MEDIUM/LOW/PROVISIONAL based on validation results

## MOSAIC Integration

**Data Flow**: Gap-filled surveillance → Enhanced time series → Weighted modeling  
**Integration**: Confidence weights in likelihood functions, uncertainty propagation, sensitivity analysis

## MANDATORY BEST PRACTICES FOR AI INSTANCES

**REQUIREMENTS: These practices are mandatory. Non-compliance compromises MOSAIC modeling effectiveness.**

### Always State Explicit File Locations When Referencing Files

**MANDATORY**: Whenever you mention, read, write, or reference a file — in chat responses, search logs, processing notes, reports, or commit messages — state its **explicit path**, not just the bare filename. This prevents ambiguity (e.g., `cholera_data_ai.csv` exists in 40 country directories) and lets the reader locate the file immediately.

**Rules**:
- Use the full repo-relative path (or absolute path) rather than a bare filename:
  - ✅ `./data/MOZ/cholera_data_ai.csv`, `./reference/baseline_surveillance_gaps_detailed.csv`, `py/update_dashboard_data.py`
  - ❌ `cholera_data_ai.csv`, `the gaps file`, `the dashboard script`
- When using a path template, define the placeholder and give a concrete example: `./data/{ISO}/metadata_ai.csv` (e.g., `./data/MOZ/metadata_ai.csv`).
- When reporting that data was added or changed, name the exact file path and the specific rows/indices affected (e.g., "added rows 38–44 to `./data/MOZ/cholera_data_ai.csv`").
- When a referenced file lives outside the current working directory (another repo, a temp/cache location), say so explicitly with the full path.


## MANDATORY SEARCH STRATEGY AND BATCH PROCESSING

**CRITICAL**: This section defines the authoritative search methodology. Searches must be organized into logical batches of 20-25 queries covering diverse sources and time periods. Stopping criteria are evaluated after each batch.

**Execution model**: Queries within a batch execute sequentially (one WebSearch at a time); stopping criteria are evaluated between batches, not within them. The term "parallel" in earlier sections means organizing queries into coordinated batches, not simultaneous execution.

### Batch Processing Requirements

#### Batch Organization Mandate

**AVOID**: Unstructured, ad-hoc individual queries without batch organization
```python
# POOR PRACTICE - Unstructured queries
WebSearch("Angola cholera WHO 2024")
# stop, evaluate, decide next step
WebSearch("Angola cholera UNICEF 2024")
```

**REQUIRED**: Organized batch execution
```python
# REQUIRED - Parallel Batch Processing: batches of 20-25 queries
[
  WebSearch("Angola cholera WHO 2024"),
  WebSearch("Angola cholera UNICEF 2024"),
  WebSearch("Angola cholera MSF 2024"),
  WebSearch("Angola cholera ReliefWeb 2024"),
  WebSearch("Angola cholera government 2024"),
  WebSearch("Angola cholera academic 2024"),
  WebSearch("Angola cholera surveillance 2024"),
  WebSearch("Angola cholera cases 2002"),
  WebSearch("Angola cholera deaths 2006"),
  WebSearch("Angola oral cholera vaccine 2018")
  # ... up to 20-25 queries per batch
]
```

**CRITICAL REQUIREMENTS**:
- Execute 20-25 queries per batch in parallel
- Complete ALL stated queries without shortcuts
- Maintain minimum performance standards (>50% of required rate)
- Document batch completion times and query rates

### Three-Phase Search Protocol

#### PHASE 1: Broad Discovery (REQUIRED)
Comprehensive initial coverage using parallel execution:

1. **Systematic Query Categories**: Execute ALL mandatory categories in parallel batches
   - WHO/Official surveillance sources
   - Academic/peer-reviewed literature
   - Humanitarian/NGO reports
   - Regional/cross-border sources
   - Historical/archival records
   - Technical/laboratory reports
   - Linguistic/local language sources

2. **Multi-Engine Coverage**: Parallel searches across:
   - Google, Google Scholar, PubMed
   - WHO databases, ReliefWeb
   - Government sites, institutional repositories
   - Regional databases, news archives

3. **Temporal Comprehensiveness**: Parallel decade-specific searches
   - Batch searches by decade (1970s, 1980s, 1990s, 2000s, 2010s, 2020s)
   - Execute all decades simultaneously

4. **Geographic Completeness**: Parallel administrative levels
   - National, provincial, district searches in same batch
   - Cross-border regional searches

5. **Language Diversity**: Simultaneous multi-language batches
   - English, French, Portuguese, Arabic, local languages
   - Execute language variants in parallel

#### PHASE 2: Targeted Gap Filling (REQUIRED)
Focused searches based on Phase 1 discoveries:

1. **Gap Identification**: Analyze Phase 1 results for:
   - Missing years, regions, outbreak periods
   - Incomplete geographic coverage
   - Partial temporal coverage

2. **Focused Batch Searches**: Create targeted query batches for:
   - Specific gap periods identified
   - Under-represented geographic areas
   - Missing source types

3. **Cross-Reference Validation**: Parallel WebFetch for:
   - Multi-source verification of major outbreaks
   - Regional pattern confirmation
   - Temporal consistency checks

4. **Alternative Terminology**: Parallel searches using:
   - Synonyms and local disease terms
   - Historical terminology variations
   - Regional naming conventions

#### PHASE 3: Deep Validation (REQUIRED)
Comprehensive validation and source expansion:

1. **Source Chain Following**: Parallel batch searches for:
   - Citation networks from discovered sources
   - Reference lists from key publications
   - Related publications by same authors

2. **Institutional Deep Dives**: Simultaneous searches of:
   - Organization websites and repositories
   - Ministry of Health archives
   - University databases
   - NGO publication libraries

3. **Archive Exploration**: Parallel searches in:
   - Internet Archive/Wayback Machine
   - Digital library collections
   - Historical newspaper archives
   - Government document repositories

4. **Quality Verification**: Parallel validation of:
   - Source authenticity
   - Data consistency
   - Cross-source agreement
   - Temporal alignment

### Search Completeness Verification

**MANDATORY CHECKLIST before concluding search:**
- [ ] All 7 query categories completed with parallel execution
- [ ] All major search engines/databases checked (15+ minimum)
- [ ] Local language searches conducted where applicable
- [ ] All decades searched systematically (1970s-2020s)
- [ ] All administrative levels searched (national, provincial, district)
- [ ] Reference chains followed from found sources
- [ ] Institution websites searched systematically
- [ ] Archive searches conducted for broken links
- [ ] Cross-border and regional sources checked
- [ ] Preliminary vs final report versions verified

### Performance Standards

- **Minimum Batch Size**: 20 queries (maximum 25)
- **Query Execution Rate**: >50% of maximum for >90% of time
- **Batch Completion**: Document time and yield for each batch
- **Total Coverage**: 200+ queries per agent (except Agent 7)
- **Stopping Criteria**: Per Agent Operations Framework

### Integration with Agent Framework

Each agent applies this three-phase protocol with agent-specific focus:
- **Agent 1**: Emphasize Phase 1 broad discovery
- **Agent 2**: Focus on geographic variants in all phases
- **Agent 3**: Prioritize absence validation searches
- **Agent 4**: Emphasize Phase 3 deep archival searches
- **Agent 5**: Focus on Phase 2 cross-reference validation
- **Agent 6**: Emphasize context and system functionality searches



### FINAL DELIVERABLE STANDARDS (MANDATORY)

#### **Completeness Requirements**
**ALL deliverables must include:**
- Search report (`search_report.txt`, created by Agent 7 only): concise executive summary (1-2 pages) covering total sources, observations added, gaps filled, data quality assessment, and remaining limitations. Detailed metrics (validation pass rates, source distribution, geographic/temporal coverage) documented as a structured appendix within the same file.
- Metadata_ai.csv with enhanced indexing system (Index column + all required fields)
- cholera_data_ai.csv in standardized JHU format with dual-reference system (source_index + source columns)
- Quality assessment documentation
- Validation report with all checks performed
- Uncertainty quantification for all data points
- Recommendations for future data collection


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
- [ ] **PERFORMANCE STANDARDS: Agents 1-6 continue until 3 consecutive batches <5% yield OR 10 total batches maximum**
- [ ] **SYSTEMATIC COVERAGE: Priority sources parsed and systematically searched**
- [ ] **BATCH LOGGING: Query rates and performance metrics documented**

**CRITICAL: This data enhancement directly impacts MOSAIC model accuracy and public health decisions. All searches must follow the Mandatory Search Strategy and Parallel Processing protocol.**



## Common Pitfalls and Solutions

### Search Challenges
- **Problem**: Limited results for specific countries/time periods
- **Solution**: Broaden search to regional reports, neighboring countries

## DATA STANDARDIZATION AND CONFLICT RESOLUTION

### Comprehensive Standardization Protocol

#### Date Standardization
**Problem**: Multiple date formats across sources

**MANDATORY Conversion Rules**:
- **Standard Format**: YYYY-MM-DD for all dates
- **Ambiguous Dates**: Document assumption (e.g., 01/02/2020 → specify if DD/MM or MM/DD)
- **Date Ranges**: Use TL (start) and TR (end) fields
- **Incomplete Dates**: 
  - Year only: "2006-01-01" to "2006-12-31"
  - Month-Year: Use first and last day of month
- **Seasonal Data**: Map to appropriate months based on country climate patterns

#### Geographic Standardization
**Problem**: Inconsistent naming and administrative levels

**MANDATORY Standards**:
- **Country**: AFR::{ISO_CODE} (e.g., AFR::AGO)
- **Province**: AFR::{ISO}::{PROVINCE} (e.g., AFR::AGO::Luanda)
- **District**: AFR::{ISO}::{PROVINCE}::{DISTRICT}
- **Municipal**: AFR::{ISO}::{PROVINCE}::{DISTRICT}::{MUNICIPALITY}

**Naming Rules**:
- Use official English administrative names
- Cross-reference with ISO 3166-2 codes
- Document alternative spellings/local names
- Handle temporal name changes appropriately

#### Case Count Standardization
**Problem**: Different definitions and reporting standards

**Conversion Protocol**:
1. **Suspected Cases (sCh)**: Primary metric, includes clinical diagnoses
2. **Confirmed Cases (cCh)**: Laboratory-confirmed only
3. **"Total Cases"**: Assign to sCh unless specifically laboratory-confirmed
4. **Rate Conversions**: Convert to absolute numbers using documented population
5. **Cumulative vs Period**: Clearly distinguish and document

#### Unit Conversions
**Standard Requirements**:
- **CFR**: Express as percentage (0-100%), not decimal
- **Attack Rates**: Percentage of affected population
- **Duration**: Convert to days for calculations
- **Population**: Use absolute numbers, not rates

### Conflict Resolution Framework

#### Conflicting Information Protocol
When sources report different values:

1. **Document All Values**: Record exact values from each source with timestamps
2. **Apply Source Hierarchy**:
   - Level 1: WHO, Government official statistics
   - Level 2: UN agencies, established NGOs
   - Level 3: Academic sources, news media
   - Level 4: Local/unofficial sources

3. **Resolution Rules**:
   - **WHO vs Local**: Prefer WHO for standardized definitions
   - **Final vs Preliminary**: Always use updated/final reports
   - **Different Periods**: Ensure temporal alignment before comparing
   - **Different Scales**: Use most specific geographic level

4. **Documentation Requirements**:
   - Record all conflicts in processing_notes
   - Provide uncertainty ranges when applicable
   - Reduce confidence_weight for conflicting data
   - Flag for sensitivity analysis

#### Missing Data Protocol
**Resolution Steps**:
1. **Required Fields**: Location, dates, and at least one metric (cases/deaths/CFR)
2. **Acceptable Gaps**: Can calculate CFR if cases and deaths available
3. **Imputation**: Only for obvious errors (e.g., typos)
4. **Documentation**: Use standard codes (NA, missing, not reported)

#### Source Authentication Issues
**Verification Protocol**:
1. **URL Validation**: Test links, use archived versions for broken URLs
2. **Author Verification**: Confirm credentials and affiliations
3. **Publication Status**: Verify peer review, official status
4. **Alternative Access**: Document all access attempts

### Documentation Requirements

#### Conversion Documentation
For every standardization:
- **Original Values**: Preserve in metadata or processing_notes
- **Conversion Method**: Document step-by-step process
- **Assumptions**: Record all interpretive decisions
- **Uncertainty**: Quantify conversion-related uncertainty
- **Validation**: Cross-verify converted values

#### Quality Flags
- **DIRECT**: No conversion needed
- **SIMPLE**: Straightforward conversion
- **COMPLEX**: Multiple conversions required
- **UNCERTAIN**: Significant ambiguity
- **ESTIMATED**: Required estimation/interpolation

All standardizations must maintain full traceability from original source to final data entry.

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
- **Minimum Performance Standards**: Agent 1-6 continue until 3 consecutive batches <5% data observation yield OR 10 total batches maximum
- **Systematic Coverage Required**: Agent 1 uses focused 45 highest-priority sources (200 queries from reference/priority_sources.txt)
- **Multi-language Parallel Batches**: Execute simultaneous searches in English, Portuguese, French, Arabic, and local languages
- **Cross-border Parallel Validation**: Batch searches across neighboring countries simultaneously
- **Accelerated Temporal Coverage**: Parallel decade-specific searches (1970s-2020s executed simultaneously)

**CRITICAL**: Agents must NOT stop early if stopping criteria are not met! Searches to fill surveillance gaps must be thorough. Be persistent, follow links, be exhaustive.

#### **Quality Control Minimums (Enhanced)**
- **100% validation** of all extracted data points using parallel validation techniques
- **Multi-source confirmation** for all major outbreaks (>1000 cases) via parallel WebFetch
- **Cross-reference checking** against WHO annual summaries using batch processing
- **Duplication screening** for all overlapping time periods with automated detection
- **Expert review** of all high-uncertainty data points while maintaining search momentum
- **Performance Monitoring**: Real-time tracking of query rates and batch completion times

This methodology enables systematic, batch-organized search coverage (up to 1,000-1,320 queries across Agents 1-6) while maintaining the highest quality standards for MOSAIC epidemiological modeling. Queries execute sequentially within each logical batch; stopping criteria are evaluated after each batch completes.

## MOSAIC FRAMEWORK COUNTRY PRIORITIZATION

**MANDATORY SCOPE RESTRICTION**: AI instances must work ONLY on the 40 MOSAIC framework countries for cholera data collection:

**Load MOSAIC Countries**: Read `./reference/country_mapping.json` and work ONLY on countries with `"mosaic_framework": true`:
- AGO, BDI, BEN, BFA, BWA, CAF, CIV, CMR, COD, COG, ERI, ETH, GAB, GHA, GIN, GMB, GNB, GNQ, KEN, LBR, MLI, MOZ, MRT, MWI, NAM, NER, NGA, RWA, SEN, SLE, SOM, SSD, SWZ, TCD, TGO, TZA, UGA, ZAF, ZMB, ZWE

**PROHIBITED**: 
- **NO analysis of non-MOSAIC countries**: COM, CPV, DJI, DZA, EGY, LBY, LSO, MAR, MDG, MUS, SDN, STP, SYC, TUN
- **NO work outside the 40 MOSAIC framework countries**
- **Scope validation required**: Always verify countries are MOSAIC-eligible before processing

## COMPREHENSIVE ACCESS PERMISSIONS

### UNRESTRICTED ACCESS TO SUGGESTED SOURCES

**EXPLICIT AUTHORIZATION**: All AI instances working on cholera surveillance data collection have **UNRESTRICTED AND IMMEDIATE ACCESS** to all domains, websites, databases, and platforms listed in `./reference/priority_sources.txt`.

**PRE-APPROVED DOMAIN ACCESS**: The reference/priority_sources.txt file contains **486 pre-authorized domains** organized into 4 priority tiers:

- **TIER 1 (105 sources)**: WHO Official, Government Health Ministries, Major Academic Medical Centers
- **TIER 2 (138 sources)**: UN Agencies, Major Universities, Established NGOs, Major Journals  
- **TIER 3 (141 sources)**: Regional Organizations, News Media, Surveillance Networks, WASH Organizations
- **TIER 4 (102 sources)**: Archives, Specialized Databases, Secondary Sources

**ACCESS PROTOCOL**: 
1. **No Permission Required**: Proceed immediately with WebFetch(), WebSearch(), and data extraction from any domain in reference/priority_sources.txt
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
1. All agents (1-6) continue searching until ONE of these conditions is met:
   a) 3 consecutive batches achieve <5% data observation yield, OR
   b) 10 total batches have been executed (200 queries maximum)
2. No exceptions - these are hard stopping criteria for consistency
```

#### **Parameter Specifications**

**Unified Parameters for Agents 1-6**:

**All Agents (1-6)**: 
- Stop when 3 consecutive batches achieve <5% data observation yield
- OR stop after 10 total batches (200 queries maximum)
- No minimum batch requirements - agents may stop earlier if 3 consecutive low-yield batches occur
- No exceptions or quality overrides - consistent application across all agents

**Threshold Rationale**:
- 5% threshold: Balances thoroughness with efficiency across all agent types
- 3 consecutive batches: Ensures genuine saturation rather than temporary fluctuations
- 10 batch maximum: Prevents excessive searching while allowing thorough coverage
- Unified criteria: Simplifies implementation and ensures consistency

#### **Data Observation Yield = Successful Queries Only**
```
Batch Yield = (Number of queries that resulted in at least one new row added to cholera_data_ai.csv / 20 queries) × 100%

**CRITICAL ERROR TO AVOID**: Do NOT count queries that only found cholera information.
**MANDATORY**: After each batch, count ONLY the queries that successfully resulted in new cholera_data_ai.csv additions.
**NOT** sources found, **NOT** potential data discovered, **NOT** information about cholera - ONLY queries that produced completed CSV additions with quantitative data (cases, deaths, CFRs, dates, locations).

**QUANTITATIVE DATA REQUIREMENT**: Sources MUST contain identifiable cholera case values (sCh or cCh) to qualify for cholera_data_ai.csv inclusion. Qualitative mentions of outbreaks without case counts do NOT count toward data observation yield.

**Example**: If 6 out of 20 queries each resulted in at least one new cholera_data_ai.csv row (regardless of how many rows each query produced), yield = 6/20 = 30%

Where "Successful Queries" are those that produce:
- Novel cholera case/death counts with dates → cholera_data_ai.csv
- New geographic breakdowns (provincial/district level) → cholera_data_ai.csv
- Historical outbreak periods previously undocumented → cholera_data_ai.csv
- Surveillance system capacity data → cholera_data_ai.csv
- Cross-border transmission evidence → cholera_data_ai.csv
- Vaccination campaign effectiveness data → cholera_data_ai.csv
```

#### **Quality Exception Protocol**
- **NO EXCEPTIONS**: The stopping criteria are applied uniformly without quality-based exceptions
- **Rationale**: Consistent stopping criteria ensure reproducibility and prevent subjective decision-making
- **Implementation**: Track data observation yield for each batch and stop when criteria are met
- **Documentation**: Record exact batch counts and yields that triggered stopping

#### **Implementation Requirements**

**CRITICAL BATCH COMPLETION CHECKLIST - ALL ITEMS MANDATORY**:
□ 20 parallel searches executed
□ All quantitative cholera data extracted from results
□ cholera_data_ai.csv updated with new rows (count: ___)
□ metadata_ai.csv updated with new sources  
□ Dual-reference indexing verified (source_index ↔ Index)
□ Data observation yield calculated: ___% (successful queries / 20)
□ Search log updated with actual CSV additions count



#### **Integration with Agent Framework**

See Agent Operations Framework section for detailed agent requirements and responsibilities.

**Total Maximum Workflow Limit**: 1,200 queries for Agents 1-6 (6 agents × 200 queries max), unlimited validation queries for Agent 7

## AGENT OPERATIONS FRAMEWORK

### Common Requirements for All Agents

#### Search Log Creation (MANDATORY)
All agents MUST create and maintain individual search logs:
- **File Format**: `search_log_agent_X.txt` where X is the agent number (1-7)
- **Location**: `./data/{ISO_CODE}/search_log_agent_X.txt`
- **Initialization**: Create log file immediately upon agent start
- **Content**: Document all search batches, queries executed, results found, and CSV updates

**Agent 1 Special Initialization**:
```bash
echo "=== AGENT 1 INITIALIZATION ===" > ./data/{ISO_CODE}/search_log_agent_1.txt
echo "Country: {COUNTRY_NAME} ({ISO_CODE})" >> ./data/{ISO_CODE}/search_log_agent_1.txt  
echo "Start Time: $(date '+%Y-%m-%d %H:%M:%S')" >> ./data/{ISO_CODE}/search_log_agent_1.txt
echo "Agent 1 Status: INITIALIZED" >> ./data/{ISO_CODE}/search_log_agent_1.txt
echo "" >> ./data/{ISO_CODE}/search_log_agent_1.txt
```
Note: Agent 1 initialization triggers workflow orchestrator dashboard update to mark country as "PENDING"

#### Gap Analysis File Loading (Agents 1-6)
All data collection agents (1-6) MUST load the baseline gap analysis file:
- **File**: `./reference/baseline_surveillance_gaps_detailed.csv`
- **Purpose**: Target specific temporal gaps identified in baseline data
- **Usage**: Focus searches on gap periods based on agent-specific strategies

#### Stopping Criteria (Agents 1-6)
All data collection agents use identical stopping criteria:
- **Continue searching until ONE of these conditions is met:**
  - 3 consecutive batches achieve <5% data observation yield, OR
  - 10 total batches have been executed (200 queries maximum)
- **No exceptions**: Apply criteria uniformly across all data collection agents

### Agent-Specific Responsibilities

#### Agent 1 - Baseline Collector
- **Primary Focus**: Substantial baseline establishment using longest duration gaps first
- **Coverage Strategy**: EXHAUSTIVE - Target ALL gaps equally with comprehensive searches

#### Agent 2 - Geographic Expansion Specialist  
- **Primary Focus**: Geographic expansion at provincial and district levels
- **Coverage Strategy**: Expand coverage within gap periods using location-specific queries

#### Agent 3 - Zero-Transmission Validator
- **Primary Focus**: Validate gaps suitable for zero-transmission (7 days-2 years duration)
- **Special Requirement**: MANDATORY documentation of ALL validated absence periods as data observations in cholera_data_ai.csv

#### Agent 4 - Obscure Source Explorer
- **Primary Focus**: Historical gaps (>5 years old or ≥3 years duration)
- **Coverage Strategy**: Target gaps ending before 2018 or with duration ≥1095 days

#### Agent 5 - Cross-Reference Integrator
- **Primary Focus**: Exhaustive source permutation across all gaps
- **Coverage Strategy**: Cross-validation and conflict resolution

#### Agent 6 - Gap Context Investigator
- **Primary Focus**: Investigate remaining temporal gaps ≥6 months
- **Coverage Strategy**: Distinguish between non-reporting periods and true zero-transmission

#### Agent 7 - Quality Auditor
- **Primary Focus**: Quality audit and dataset finalization
- **Deliverables**: Create brief search_report.txt with quantitative gap-filling impact analysis
- **Note**: No stopping criteria - unlimited validation queries allowed

### Agent File Outputs
All agents produce standardized outputs in `./data/{ISO_CODE}/`:
- `search_log_agent_X.txt` - Individual agent search logs (All agents)
- `cholera_data_ai.csv` - Enhanced surveillance data (Agents 1-6)
- `metadata_ai.csv` - Source documentation (Agents 1-6)
- `search_report.txt` - Summary report (Agent 7 only)
- `workflow_orchestrator_{ISO_CODE}.txt` - Orchestrator configuration file

## UNIFIED DASHBOARD UPDATE SYSTEM

**SINGLE UPDATE COMMAND**: All agents should use the unified dashboard update system to refresh all dashboard data simultaneously.

### **RECOMMENDED UPDATE COMMANDS**

**Option 1: Shell Script (Simplest)**
```bash
bash update_dashboard.sh
```

**Option 2: Python Script (Direct)**
```bash
python py/update_dashboard_data.py
```

**What Gets Updated**:
- ✅ **Completion Checklist**: Real-time status based on file analysis
- ✅ **3-Source Timeline Plots**: Coverage visualization with synchronized date ranges
- ✅ **Week Counts Data**: Actual data extracted from sources and embedded in dashboard
- ✅ **Dashboard HTML**: All embedded CSV data refreshed automatically

### **AGENT INITIALIZATION PROTOCOL**

**CRITICAL**: The workflow orchestrator automatically runs the dashboard update command after Agent 1 creates its first search log to mark the country as "PENDING":

**Step 1: Create Initial Log File**
See Agent Operations Framework section for Agent 1 initialization protocol.

**Step 2: Begin Search Protocol**
Proceed with systematic search methodology. The workflow orchestrator handles the dashboard update automatically.

### **DASHBOARD UPDATE SCHEDULE (MEMORY-OPTIMIZED)**

**Dashboard updates occur at only TWO points to reduce memory usage**:
1. **Workflow Initialization**: Automatically after Agent 1 creates its first log file (marks country as "PENDING")
2. **Workflow Completion**: Automatically after Agent 7 completes quality audit (marks country as "COMPLETED")

**CRITICAL CHANGE**: Individual agents (1-7) do NOT update the dashboard during execution. This reduces memory usage by approximately 75% (from ~2.4GB to ~0.6GB for dashboard operations).

**Benefits of Unified System**:
- **Single Command**: No need to run multiple scripts
- **Complete Synchronization**: All dashboard elements updated together
- **Real-Time Accuracy**: Reflects actual file system state
- **Timeline Integration**: Plots and data perfectly synchronized
- **No Manual Errors**: Automated CSV embedding prevents version mismatches

**Benefits of Initialization Protocol**:
- **Immediate Visibility**: Dashboard shows "PENDING" status within seconds
- **Progress Tracking**: Stakeholders know work has begun
- **Time Tracking**: Precise start timestamps for performance metrics  
- **Quality Assurance**: Ensures proper file structure from the beginning
- **Error Prevention**: Creates necessary directory structure early

**Performance Monitoring**:
- Track yield trends across all continuing agents
- Document stopping criteria achievement (batch number and yield that triggered stop)
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

### Automatic Context Management (MANDATORY)

**REQUIREMENT: Proactive state serialization when approaching context limits**

**WHEN TO SAVE STATE:**
- After completing each agent (before starting next agent)
- After each search batch when context is growing large
- Before major phase transitions in the workflow

**HOW TO SAVE STATE:**
Write a `workflow_state.json` to `./data/{ISO_CODE}/` capturing:
- Current agent number and batch count
- Data observation yield per batch (list)
- Total rows added and sources discovered so far
- Stopping criteria status (met/not met, reason)
- Next action for the subsequent agent

**EXAMPLE:**
```json
{
  "agent": 1,
  "iso_code": "ETH",
  "batches_completed": 7,
  "batch_yields": [0.25, 0.15, 0.08, 0.04, 0.03, 0.02, 0.01],
  "stopping_criteria_met": true,
  "reason_stopped": "3 consecutive batches below 5% yield",
  "rows_added": 34,
  "sources_discovered": 22
}
```

**MANDATORY TRIGGERS:**
□ Agent completion — write state before handing off to next agent
□ Mid-agent every 5 batches if context is large
□ Before quality audit phase

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

**MANDATORY AGENT 7 BASELINE GAP ASSESSMENT**: Every country completion must include comprehensive quantitative gap-filling impact analysis using the baseline gap analysis system:

1. **Load Baseline Gap Files**: Use all three baseline gap files to assess coverage improvement
2. **Calculate Gap-Filling Success Rate**: Document how many gap periods were successfully filled or validated
3. **Coverage Enhancement**: Calculate improvement in percent_coverage from baseline analysis
4. **Temporal Distribution**: Document which years and periods were successfully addressed
5. **Geographic Coverage**: Document improvements by administrative level
6. **Remaining Gaps**: Identify unfilled gap periods requiring future attention
7. **Cross-Agent Performance**: Evaluate which agent types were most effective
8. **Enhanced Surveillance Timeline**: Generate before/after timeline showing gap-filling impact

---

**FINAL CHECKPOINT: Before submitting any country's data enhancement, verify that ALL requirements in this document have been met. Incomplete or substandard work will require complete revision.**
