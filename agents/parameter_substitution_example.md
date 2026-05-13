# Parameter Substitution Example

## How the Orchestrator Generates Country-Specific Instructions

### Input: "Process Ethiopia's cholera data"

### Step 1: Parameter Extraction
```json
{
  "COUNTRY_NAME": "Ethiopia",
  "ISO_CODE": "ETH", 
  "country": "Ethiopia",
  "major_cities": ["Addis Ababa", "Dire Dawa", "Mek'ele", "Gondar"],
  "neighboring_countries": ["Sudan", "South Sudan", "Kenya", "Somalia", "Djibouti", "Eritrea"],
  "priority_gap_years": ["2019", "2020", "2021", "2022"],
  "TOTAL_PROVINCES": 11
}
```

### Step 2: Agent 1 Task Generation

**Base Template (from agent1_baseline_collector.md):**
```
Execute the comprehensive 8-phase search protocol for {COUNTRY_NAME} ({ISO_CODE}). 
Your mission is to fill gaps by adding AI discoveries to ./data/{ISO_CODE}/cholera_data_ai.csv.
```

**Generated Task (with parameters substituted):**
```
Execute the comprehensive 8-phase search protocol for Ethiopia (ETH).
Your mission is to fill gaps by adding AI discoveries to ./data/ETH/cholera_data_ai.csv.

**Country-Specific Context:**
- Priority gap years: 2019, 2020, 2021, 2022
- Baseline coverage: 59.1% (HIGH priority for gap-filling)
- Neighboring countries for cross-validation: Sudan, South Sudan, Kenya, Somalia, Djibouti, Eritrea
- Total provinces: 11 administrative divisions to consider

**Gap-Targeted Search Focus:**
- Include temporal constraints: "Ethiopia cholera 2019 2020 2021 2022" in searches
- Priority period: 2018-12-10 to 2023-01-01 (4+ year gap)
- Focus 80% of searches on identified priority gaps
```

### Step 3: Agent 2 Task Generation

**Base Template (from agent2_geographic_expansion.md):**
```
Execute systematic geographic expansion for {COUNTRY_NAME} ({ISO_CODE}).
Search queries should include:
- "{country} {province_name} cholera outbreak cases deaths {year}"
- "{country} {major_city} cholera municipal health department {year}"
```

**Generated Task (with parameters substituted):**
```
Execute systematic geographic expansion for Ethiopia (ETH).

**Enhanced Geographic Search Queries:**
- "Ethiopia Addis_Ababa cholera outbreak cases deaths 2019"
- "Ethiopia Dire_Dawa cholera municipal health department 2020" 
- "Ethiopia Oromia cholera outbreak cases deaths 2021"
- "Ethiopia Amhara cholera district breakdown administrative 2022"

**Administrative Targets (11 provinces total):**
- Major provinces: Addis Ababa, Oromia, Amhara, Tigray, SNNPR, Somali, Afar
- Major cities: Addis Ababa, Dire Dawa, Mek'ele, Gondar, Hawassa, Bahir Dar
- Geographic coding: AFR::ETH::{PROVINCE}::{DISTRICT} format
```

### Step 4: Agent 3 Task Generation

**Base Template (from agent3_zero_transmission.md):**
```
Execute systematic zero-transmission validation for {COUNTRY_NAME} ({ISO_CODE}).
Cross-border validation with: {neighboring_countries}
```

**Generated Task (with parameters substituted):**
```
Execute systematic zero-transmission validation for Ethiopia (ETH).

**Year-Specific Search Protocol:**
- "Ethiopia cholera 2019" across all search engines
- "Ethiopia cholera outbreak 2020" news archives  
- "WHO Ethiopia cholera surveillance 2021"
- "Ethiopia cholera cases deaths 2022" academic

**Cross-border validation with:** Sudan, South Sudan, Kenya, Somalia, Djibouti, Eritrea
- "Ethiopia Sudan cholera cross-border transmission 2019-2022"
- "Horn of Africa cholera regional patterns 2019-2022"

**Priority Gap Focus:**
- Systematic validation of 2019-2022 absence period
- Confirm surveillance system functioning during gap
- Document as zero-transmission observations in cholera_data.csv
```

## Key Benefits of This Approach

✅ **Dynamic Parameter Substitution**: Country-specific values automatically filled in  
✅ **Context-Aware Instructions**: Each agent gets relevant geographic and temporal context  
✅ **Gap-Targeted Focus**: Instructions automatically target country-specific missing periods  
✅ **Scalable**: Same system works for all 40 MOSAIC countries  
✅ **Maintainable**: Parameter changes update all agent instructions automatically  

## Implementation in Orchestrator

The orchestrator subagent would:
1. Parse country name from user input
2. Load parameters from reference files
3. Generate country-specific task instructions for each agent
4. Invoke agents sequentially with customized instructions
5. Monitor progress and coordinate handoffs