# Quick Start Guide

## Overview
This guide provides essential steps to begin cholera surveillance data enhancement for any MOSAIC framework country.

## Prerequisites

### Verify Country Eligibility
Check that your target country is among the 40 MOSAIC framework countries:
```bash
cat reference/mosaic_country_codes.csv
```

### Required Files
Ensure these reference files exist:
- `./reference/agent_quick_reference.csv` - Country priorities
- `./reference/agent_*_gaps.csv` - Agent-specific gap targets
- `./reference/priority_sources.txt` - Authorized domains

## Step-by-Step Workflow

### 1. Generate Country Orchestrator
```bash
python py/generate_country_orchestrator.py {ISO_CODE}
# Example: python py/generate_country_orchestrator.py ETH
```

### 2. Execute 6-Agent Workflow

Use the workflow-orchestrator agent:
```python
Task(description="Execute cholera workflow", 
     prompt="AGO",  # or any ISO code
     subagent_type="workflow-orchestrator")
```

Or execute agents individually:
```python
# Agent 1: Baseline Collection
Task(description="Baseline collection", 
     prompt=agent_1_instructions, 
     subagent_type="cholera-baseline-collector")

# Continue for agents 2-6...
```

### 3. Monitor Progress
```bash
# Update dashboard after each agent
bash update_dashboard.sh

# View dashboard
open dashboard/dashboard.html
```

## Key Commands

### Data Analysis
```bash
# Analyze coverage gaps
python py/analyze_integrated_coverage_gaps.py

# Generate coverage heatmap
python py/generate_coverage_heatmap.py

# Check compliance
python py/verify_compliance.py
```

### Dashboard Management
```bash
# Single command updates everything
bash update_dashboard.sh
```

## File Outputs

Each country will have:
```
data/{ISO}/
├── cholera_data_jhu.csv      # Baseline (read-only)
├── cholera_data_who.csv      # Baseline (read-only)
├── cholera_data_ai.csv       # AI discoveries
├── metadata_ai.csv           # Source documentation
├── search_log_agent_1.txt    # Agent 1 log
├── search_log_agent_2.txt    # Agent 2 log
├── search_log_agent_3.txt    # Agent 3 log
├── search_log_agent_4.txt    # Agent 4 log
├── search_log_agent_5.txt    # Agent 5 log
├── search_log_agent_6.txt    # Agent 6 log
└── search_report.txt         # Final summary
```

## Critical Rules

1. **Parallel Execution**: Always batch 20 queries in parallel
2. **Gap Targeting**: Use reference files to target missing periods
3. **Zero-Transmission**: Document all validated absence periods
4. **Quality Control**: All data must pass 4-stage validation
5. **Dashboard Updates**: Run after each agent completion

## Success Criteria

- Fill priority gaps (score ≥85)
- ≥80% sources at Level 1-2 reliability
- 100% data passes quality control
- Complete documentation trail

## Troubleshooting

### Common Issues
- **No gaps found**: Check reference file generation
- **Low yield**: Verify priority source coverage
- **Validation failures**: Review quality control stages

### Getting Help
- Technical specs: `docs/technical/`
- Methodology: `docs/methodology/`
- Examples: `templates/`

## Next Steps

1. Review gap analysis for your country
2. Check priority level and coverage
3. Begin with Agent 1 baseline collection
4. Monitor yield and adjust strategy