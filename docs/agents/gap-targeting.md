# Gap-Targeted Search Methodology

## Overview

Before beginning any search, agents must consult integrated coverage analysis files to target missing periods in baseline data. This methodology ensures systematic, efficient discovery of cholera surveillance gaps.

## Pre-Search Requirements

1. **Load Reference Files**: Read `./reference/agent_quick_reference.csv` for country-specific gaps
2. **Load Agent-Specific Gap Files**: Each agent must load their specialized gap targeting file:
   - **Agent 1**: `./reference/agent_1_priority_gaps.csv` (50 CRITICAL/HIGH priority national/provincial gaps ≥30 days)
   - **Agent 2**: `./reference/agent_2_geographic_gaps.csv` (40 district/municipal level gaps for geographic expansion)
   - **Agent 3**: `./reference/agent_3_validation_gaps.csv` (60 gaps 7 days-1 year for zero-transmission validation)
   - **Agent 4**: `./reference/agent_4_historical_gaps.csv` (30 historical/obscure gaps >5 years old or ≥3 years duration)
   - **Agent 5**: Use comprehensive inventory `./reference/comprehensive_gaps_inventory.csv` for cross-reference integration
   - **Agent 6**: Quality audit using all gap files for validation completeness
3. **Identify Priority Periods**: Focus searches on specific missing date ranges (≥7 days gaps)
4. **Apply Enhanced Context**: Use seasonal_context, outbreak_scale, and geographic_level data
5. **Prioritize High-Gap Countries**: Begin with HIGH priority countries (<70% coverage)

## Query Enhancement Templates

### Standard Query Enhancement
- **Basic**: `"Angola cholera outbreak WHO"`
- **Enhanced**: `"Angola national cholera outbreak WHO dry season 2019-2025 surveillance following minimal outbreak Luanda"`

### Context-Enhanced Templates

**Geographic Context**:
- `"{Country} {geographic_level} cholera cases {gap_start_year}-{gap_end_year}"`
- `"{Country} {specific_province} cholera surveillance {gap_period}"`
- `"{Country} {district_name} cholera outbreak {seasonal_context}"`

**Seasonal Context**:
- `"{Country} cholera {seasonal_context} {gap_years}"` (e.g., "Ethiopia cholera dry season 2019-2022")
- `"{Country} cholera rainy season outbreak {gap_period}"`
- `"{Country} cholera flooding epidemic {specific_dates}"`

**Outbreak Scale Context**:
- `"{Country} cholera following {preceding_outbreak_scale} outbreak {gap_period}"`
- `"{Country} cholera surveillance after {outbreak_magnitude} epidemic {gap_dates}"`
- `"{Country} cholera cases between {preceding_location} {following_location} outbreaks"`

## Priority-Based Query Generation

**CRITICAL Priority Gaps (Score 85-100)**:
```
"{Country} {geographic_level} cholera {seasonal_context} {gap_start_year}-{gap_end_year} {preceding_outbreak_scale} outbreak surveillance WHO UNICEF government"
```

**HIGH Priority Gaps (Score 70-84)**:
```
"{Country} cholera {gap_period} {seasonal_context} surveillance {geographic_level}"
```

**MEDIUM Priority Gaps (Score 50-69)**:
```
"{Country} cholera cases {gap_years} {seasonal_context}"
```

## Temporal Search Allocation

| Priority Level | Coverage | Gap-Filling | Historical Extension |
|----------------|----------|-------------|---------------------|
| HIGH | <70% | 80% | 20% |
| MEDIUM | 70-90% | 60% | 40% |
| LOW | >90% | 40% | 60% |

## Gap Validation Protocol

For each identified gap period:
1. **Confirm Zero Transmission**: Search for evidence that NO cholera occurred
2. **Identify Surveillance Gaps**: Distinguish between no disease vs. no reporting
3. **Document Gap Type**: Disease-free period vs. surveillance system failure
4. **Cross-Reference Regional**: Check neighboring countries for outbreak patterns

## Implementation Example

**Ethiopia (ETH) - 59.1% coverage, HIGH priority**:
- Priority Gap: 2018-12-10 to 2023-01-01 (4+ year gap)
- Missing Historical: 2000-2014
- Current Data: 2015-2018, 2023-2025

**Search Allocation**:
1. **80% on Priority Gap (2019-2022)**:
   - "Ethiopia cholera 2019 surveillance WHO"
   - "Ethiopia cholera outbreak 2020 2021 UNICEF"
   - "Ethiopia cholera epidemic 2022 MSF"

2. **20% on Historical Extension (pre-2015)**:
   - "Ethiopia cholera 2010-2014 surveillance"
   - "Ethiopia cholera 2000s decade outbreak"

**Gap Validation Searches**:
- "Ethiopia cholera-free 2019 2020 2021"
- "Ethiopia surveillance system 2019-2022"
- "Ethiopia neighboring countries cholera 2019-2022"