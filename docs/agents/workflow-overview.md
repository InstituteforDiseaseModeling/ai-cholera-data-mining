# Agent Workflow Implementation Guide

## 6-Agent System Overview

The cholera surveillance enhancement system uses six specialized agents, each with distinct responsibilities:

### Agent Types and Responsibilities

1. **cholera-baseline-collector** (Agent 1)
   - Systematic priority source coverage
   - Focus on WHO, government, academic sources
   - Stop when 3 consecutive batches <5% yield OR 10 total batches (200 queries max)

2. **geographic-expansion-specialist** (Agent 2)
   - Sub-national data discovery
   - Provincial, district, municipal level expansion
   - Stop when 3 consecutive batches <5% yield OR 10 total batches (200 queries max)

3. **zero-transmission-validator** (Agent 3)
   - Absence period documentation
   - Validate cholera-free periods ≥7 days
   - Document ALL validated periods as data observations

4. **obscure-source-explorer** (Agent 4)
   - Historical and gray literature mining
   - Internet Archive, institutional repositories
   - Focus on gaps >5 years old or ≥3 years duration

5. **cross-reference-integrator** (Agent 5)
   - Source triangulation and conflict resolution
   - Citation network following
   - Comprehensive cross-validation

6. **cholera-quality-auditor** (Agent 6)
   - Final validation and quality assessment
   - Gap-filling impact analysis
   - Create brief search_report.txt

## Workflow Execution Protocol

### Step 1: Generate Orchestrator File
```bash
python py/generate_country_orchestrator.py {ISO_CODE}
```

### Step 2: Execute via Task Tool
Each agent uses specialized subagent_type parameters:
```python
Task(description="Agent 1 Baseline Collection", 
     prompt=orchestrator_instructions, 
     subagent_type="cholera-baseline-collector")
```

### Step 3: Monitor Progress
```bash
bash update_dashboard.sh
```

## Search Implementation Requirements

### Parallel Batch Execution (Mandatory)
- Execute 20 queries per batch in parallel
- Never execute queries sequentially
- Track batch performance metrics

### Stopping Criteria
| Agent | Stop When | Max Batches | Max Queries |
|-------|-----------|-------------|-------------|
| 1-6 | 3 consecutive <5% yield | 10 | 200 |
| 7 | Quality complete | N/A | N/A |

### Data Observation Yield Calculation
```
Batch Yield = (Queries resulting in CSV additions / 20) × 100%
```
Only count queries that produce actual cholera_data_ai.csv entries with quantitative data.

## File Output Requirements

Each agent must create:
- `search_log_agent_X.txt` - Detailed search documentation
- Updates to `cholera_data_ai.csv` - New data observations
- Updates to `metadata_ai.csv` - Source documentation

Agent 6 additionally creates:
- `search_report.txt` - Brief summary of key outcomes

## Quality Standards

### Source Reliability Levels
- Level 1 (0.9-1.0): WHO, MoH, peer-reviewed
- Level 2 (0.7-0.9): UNICEF, established NGOs
- Level 3 (0.3-0.6): Reputable news, local government
- Level 4 (0.1-0.3): Local media, unofficial reports

### Validation Requirements
- All data must pass epidemiological range checks
- Major outbreaks (>1000 cases) require multiple sources
- Zero-transmission periods require explicit documentation

## Dashboard Integration

Agents should NOT manually update the dashboard. The system automatically:
- Detects file changes
- Calculates completion status
- Updates metrics based on actual data
- Generates timeline visualizations

Simply run `bash update_dashboard.sh` after completing work.