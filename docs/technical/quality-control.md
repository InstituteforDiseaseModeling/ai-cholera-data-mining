# Quality Control Protocols

## Source Reliability Framework

### Reliability Levels
| Level | Weight | Sources | Criteria |
|-------|--------|---------|----------|
| 1 | 0.9-1.0 | WHO, MoH, peer-reviewed journals | Official surveillance, government statistics |
| 2 | 0.7-0.9 | UNICEF, OCHA, established NGOs | Regional organizations, UN agencies |
| 3 | 0.3-0.6 | Reputable news, local government | Preliminary reports, regional media |
| 4 | 0.1-0.3 | Local media, social media | Unofficial reports (use with extreme caution) |

## 4-Stage Validation Protocol

### Stage 1: Authentication
- URL verification and archival
- Author/institution credentials
- Domain validation
- Publication date verification

### Stage 2: Data Quality Checks

**Epidemiological Ranges**:
- CFR: 0.1-15% (flag outliers)
- Attack rates: 0.01-10% of population
- Outbreak duration: 1-104 weeks
- Deaths ≤ suspected cases

**Temporal Logic**:
- Start date < End date
- Reporting date ≥ End date
- No future dates
- Seasonal pattern consistency

**Geographic Validation**:
- ISO/WHO location codes
- Administrative hierarchy
- Population denominator accuracy
- Cross-border plausibility

### Stage 3: Cross-Reference Validation

**Multi-Source Requirements**:
- Outbreaks >1000 cases: ≥2 sources
- CFR >5%: Clinical confirmation
- New areas: Regional verification
- Historical: WHO annual summaries

**Mathematical Consistency**:
- CFR calculation accuracy (±0.1%)
- Period sum validation
- Attack rate calculations
- Epidemic curve logic

### Stage 4: Integration Checks

**Duplication Prevention**:
- Identical record detection
- Overlapping period resolution
- Version supersession
- Sub-national aggregation

**Completeness Assessment**:
- Required field validation
- Geographic coding standardization
- Source attribution verification
- Quality score assignment

## Quality Control Metrics

### Rejection Criteria
Automatically reject if:
- CFR >20% without exceptional documentation
- Attack rates >20% of population
- Logically inconsistent dates
- Unverifiable sources
- Invalid geographic codes
- Unresolvable mathematical errors

### Manual Review Triggers
Flag for review if:
- CFR outside 0.5-10% range
- Attack rates outside 0.1-5% range
- Outbreak duration <2 weeks or >1 year
- Single source for major outbreaks
- Significant source discrepancies
- Unusual seasonal patterns

## Zero-Transmission Validation

### Documentation Requirements
When confirming cholera-free periods:
- Location: AFR::{ISO} (national level)
- TL/TR: Full absence period
- deaths: 0, sCh: 0, CFR: 0.0
- confidence_weight: 0.8-1.0
- processing_notes: Explicit absence confirmation

### Validation Standards
1. Evidence of functioning surveillance
2. Regional outbreak pattern consistency
3. Historical continuity validation
4. Duration plausibility (1-10 years typical)
5. Explicit absence vs. no reporting

## Quality Assurance Tracking

Monitor and report:
- Validation pass rates by stage
- Source reliability distribution
- Geographic coverage completeness
- Temporal gap-filling success
- Data density metrics
- Quality score distributions
- Rejection reasons
- Uncertainty quantification