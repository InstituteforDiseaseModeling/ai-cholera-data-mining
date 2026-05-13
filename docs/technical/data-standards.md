# Data Standards & Specifications

## File Architecture

### Separate Source Files
Each country maintains separate baseline data files:
- `./data/{ISO}/cholera_data_jhu.csv` - JHU historical database (1970-2020+ surveillance data)
- `./data/{ISO}/cholera_data_who.csv` - WHO dashboard data (recent 2023-2025 surveillance)
- `./data/{ISO}/cholera_data_ai.csv` - AI discoveries (agents work with this file only)

### Dual-Reference Indexing System
- Sequential integer indices (1,2,3...) + exact source names
- metadata_ai.csv Index column ↔ cholera_data_ai.csv source_index column
- Enables automated processing + human readability + error prevention

## cholera_data_ai.csv Column Specifications

### Location (Geographic Administrative Units ONLY)
- **Format**: `AFR::{ISO}` (national), `AFR::{ISO}::{PROVINCE}` (provincial), `AFR::{ISO}::{PROVINCE}::{DISTRICT}` (district)
- **Examples**: `AFR::AGO`, `AFR::AGO::Luanda`, `AFR::AGO::Luanda::Belas`
- **Prohibited**: Non-geographic categories (Vaccination, Training, Demographics_*, Age_Group_*, Laboratory_*, Surveillance_*)
- **Rule**: Must represent a physical location where people contracted cholera

### TL (Time Left - Start Date)
- **Format**: YYYY-MM-DD (ISO 8601)
- **Required**: Always required, use best available estimate if exact date unknown

### TR (Time Right - End Date)
- **Format**: YYYY-MM-DD (ISO 8601)
- **Rule**: Must be ≥ TL date

### deaths (Integer)
- **Format**: Positive integer or empty
- **Validation**: Must be ≤ sCh (deaths cannot exceed suspected cases)

### sCh (Suspected Cholera Cases)
- **Format**: Positive integer or empty
- **Primary Metric**: Main case count for surveillance
- **Rule**: Must have actual case numbers, not vaccination counts, population figures, or capacity data

### cCh (Confirmed Cholera Cases)
- **Format**: Positive integer or empty
- **Rule**: Must be ≤ sCh (confirmed cases subset of suspected)

### CFR (Case Fatality Rate)
- **Format**: 0-100 (percentage, not decimal)
- **Calculation**: (deaths/sCh) × 100
- **Validation**: Must be 0.1-15% for most outbreaks (flag outliers)

### reporting_date
- **Format**: YYYY-MM-DD
- **Rule**: Must be ≥ TR (reporting after outbreak end)

### source_index
- **Format**: Sequential integer (1, 2, 3...)
- **Critical**: Must match exactly with metadata.csv Index

### source
- **Format**: Free text matching metadata Source column exactly
- **Validation**: Must exist in metadata.csv Source column

### confidence_weight
- **Format**: 0.1-1.0 decimal
- **Levels**: 
  - Level 1 (0.9-1.0): WHO, MoH, peer-reviewed
  - Level 2 (0.7-0.9): UNICEF, established NGOs
  - Level 3 (0.3-0.6): Reputable news, local government
  - Level 4 (0.1-0.3): Local media, unofficial reports

### processing_notes
- **Format**: Free text with exact source quotes
- **Template**: "Source states: '[exact quote]' - interpreted as [sCh/cCh] cases"

### source_database
- **Values**: 'JHU', 'WHO', 'AI'
- **Purpose**: Track data provenance across different source systems

## metadata_ai.csv Specifications

15 required columns:
1. **Index**: Sequential integer (1, 2, 3...)
2. **Source**: Exact source name
3. **URL**: Working URL or archive link
4. **Description**: Brief source description
5. **Date_Range**: Coverage period
6. **Data_Type**: Type of data available
7. **Status**: Active/Archived/Broken
8. **Reliability_Level**: 1-4 rating
9. **Validation_Status**: Validated/Provisional
10. **Search_Technique**: Discovery method
11. **Language_Original**: Source language
12. **Citation_Depth**: Primary/Secondary/Tertiary
13. **Cross_References**: Related sources
14. **Discovery_Method**: How source was found
15. **source_database**: Always 'AI' for agent discoveries

## Data Inclusion Rules

### Required for cholera_data_ai.csv Entry:
1. Geographic location (actual administrative unit)
2. Quantitative data (specific numbers for cases, deaths, or CFR)
3. Cholera-specific (cholera cases/deaths, not vaccination/training/capacity)
4. Source attribution (matching metadata entry with working source)

### Prohibited Entries:
- Vaccination data without case counts
- Training or capacity building metrics
- Demographics without location specificity
- System capacity without disease incidence
- Population denominators without cases

### Zero-Transmission Documentation
When validated cholera-free periods are identified:
- Location: AFR::{ISO} (national level)
- TL/TR: Start/end of absence period
- deaths: 0, sCh: 0, CFR: 0.0
- confidence_weight: 0.8-1.0 based on surveillance quality
- processing_notes: "Source confirms zero cholera transmission during [period]"