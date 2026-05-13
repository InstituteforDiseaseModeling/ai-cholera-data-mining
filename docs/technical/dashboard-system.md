# Dashboard Management System

## Overview

The dashboard system provides automated progress tracking and visualization for cholera surveillance data enhancement. It operates entirely through file system analysis, requiring no manual intervention from agents.

## Automated Update System

### Single Command Update
```bash
bash update_dashboard.sh
```

This command automatically:
- Updates completion checklist based on file analysis
- Generates timeline visualizations
- Embeds current data into dashboard HTML
- Synchronizes all dashboard components

## How the System Works

### Status Detection Logic

**COMPLETED**:
- All 6 agent search logs present
- cholera_data_ai.csv and metadata_ai.csv exist
- Either search_report.txt exists OR substantial data collected

**PENDING**:
- At least one agent search log exists
- Some data files present
- Work in progress

**NOT_STARTED**:
- No agent activity detected
- No significant files present

### Automatic Metrics Calculation

| Metric | Source |
|--------|--------|
| Sources | Count from metadata_ai.csv rows |
| Observations | Count from cholera_data_ai.csv rows |
| Date Range | Min(TL) to Max(TR) from data |
| Execution Time | Estimated from query counts in logs |
| Progress | Real-time file system state |

## Agent Responsibilities

### What Agents SHOULD Do:
- Create/update cholera_data_ai.csv and metadata_ai.csv
- Complete search_log_agent_X.txt files
- Generate search_report.txt (Agent 6 only)
- Run `bash update_dashboard.sh` after completion

### What Agents should NOT Do:
- Edit dashboard CSV files manually
- Update status fields
- Calculate progress metrics
- Modify completion timestamps

## Dashboard Components

### 1. Completion Checklist
- `dashboard/completion_checklist.csv`
- Auto-generated from file system analysis
- Tracks all 40 MOSAIC countries

### 2. Timeline Visualizations
- Coverage plots showing JHU, WHO, and AI data
- Automatically generated for each country
- Synchronized date ranges across all plots

### 3. Embedded Data
- Week count data extracted and embedded in HTML
- Automatic CSV data integration
- Real-time updates on dashboard refresh

## Agent Initialization Protocol

Agent 1 should initialize country status immediately:
```bash
echo "=== AGENT 1 INITIALIZATION ===" > ./data/{ISO}/search_log_agent_1.txt
echo "Country: {COUNTRY} ({ISO})" >> ./data/{ISO}/search_log_agent_1.txt
echo "Start Time: $(date '+%Y-%m-%d %H:%M:%S')" >> ./data/{ISO}/search_log_agent_1.txt
bash update_dashboard.sh
```

## Update Points

Run dashboard update after:
- Agent 1 completion
- Each subsequent agent completion
- Agent 6 final quality audit
- Any significant data additions

## Benefits

- **Zero Manual Errors**: Fully automated tracking
- **Real-Time Accuracy**: Always reflects current state
- **Agent Focus**: No distraction from core mission
- **Consistent Metrics**: Standardized calculations