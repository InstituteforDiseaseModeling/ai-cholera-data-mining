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

**cholera_data.csv** (14 columns): Location, TL, TR, Primary, Phantom, deaths, sCh, cCh, CFR, reporting_date, source_index, source, confidence_weight, validation_status

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

### Systematic Search Strategy (MANDATORY)

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

**CRITICAL: This data enhancement directly impacts MOSAIC model accuracy and public health decisions. Thoroughness and accuracy are mandatory.**

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