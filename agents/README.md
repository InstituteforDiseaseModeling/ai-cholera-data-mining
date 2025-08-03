# MOSAIC Subagent Configurations

This directory contains the configuration files needed to create specialized subagents for the MOSAIC cholera surveillance data enhancement workflow using Claude Code's subagent system.

## Overview

The MOSAIC workflow transforms traditional single-context "pseudo-agent" approaches into a legitimate multi-agent architecture with true specialized AI agents, each operating in separate context windows with purpose-built system prompts.

## Agent Configuration Files

### Core Data Collection Agents
- **`agent_1_baseline_collector.md`** - Baseline Data Collector
  - Loads `agent_1_priority_gaps.csv` for targeted gap-filling (50 CRITICAL/HIGH gaps ≥30 days)
  - Systematic priority source coverage and foundational searches
  - Batch-based stopping criteria with data observation yield tracking (minimum 5 batches)

- **`agent_2_geographic_expansion.md`** - Geographic Expansion Specialist  
  - Loads `agent_2_geographic_gaps.csv` for district/municipal expansion (40 gaps)
  - Provincial/district-level data discovery and subnational mining
  - Administrative hierarchy drilling with geographic-level targeting

- **`agent_3_zero_transmission.md`** - Zero-Transmission Validator
  - Loads `agent_3_validation_gaps.csv` for absence validation (60 gaps, 7 days-1 year)
  - **MANDATORY**: Documents validated absence periods as data observations in cholera_data_ai.csv
  - Regional cross-validation with neighboring countries for cholera-free periods

- **`agent_4_obscure_sources.md`** - Obscure Source Explorer
  - Loads `agent_4_historical_gaps.csv` for historical/obscure mining (30 gaps >5 years)
  - Alternative source discovery beyond standard databases and suggested sources
  - Historical archives, gray literature, and unconventional source exploration

- **`agent_5_cross_reference.md`** - Cross-Reference Integrator
  - Uses `comprehensive_gaps_inventory.csv` for exhaustive source permutation
  - Cross-validation and conflict resolution between gap periods
  - Citation network expansion and adjacent data mining

- **`agent_6_quality_auditor.md`** - Quality Auditor
  - Integrates ALL gap analysis files for comprehensive coverage assessment
  - **Enhanced Gap Impact Analysis**: Pre/post workflow coverage comparison
  - Final dataset finalization with quantitative gap-filling metrics

## Implementation Process

### Step 1: Create Subagents in Claude Code
Use each `.md` file to create specialized subagents:
```bash
# For each agent configuration file:
# 1. Copy the system prompt from the .md file
# 2. Create new subagent using /agents command
# 3. Configure tools and permissions as specified
# 4. Test individual agent functionality
```

### Step 2: Generate Gap Analysis and Orchestrator Files
```bash
# From main project directory
# Step 2a: Generate comprehensive gap analysis (creates agent-specific gap files)
python py/analyze_integrated_coverage_gaps.py

# Step 2b: Generate country-specific orchestrator files  
python py/generate_country_orchestrator.py ETH        # Single country
python py/generate_country_orchestrator.py --all     # All 40 MOSAIC countries
```

### Step 3: Execute Workflows
Use generated orchestrator files to coordinate all 6 agents:
```bash
# Generated files: ./data/{ISO}/workflow_orchestrator_{ISO}.txt
# These contain complete country-specific instructions for the master orchestrator
```

### Step 4: Automated Setup Integration
The subagent system is integrated into the main setup process:
```bash
./setup.sh    # Automatically generates gap analysis and orchestrator files in Steps 6-7
```

## Architecture Benefits

### Technical Advantages
- **Separate Context Windows**: Each agent maintains independent context, preventing bloat
- **Specialized Expertise**: Purpose-built system prompts optimized for specific tasks
- **Parallel Processing**: Multiple agents can operate simultaneously
- **Error Isolation**: Issues in one agent don't cascade to others
- **Scalable Design**: Reusable agents across all 40 MOSAIC countries

### Operational Benefits  
- **Maintained Convenience**: Single-command execution per country preserved
- **Automated Parameters**: Country-specific context generated automatically
- **Quality Assurance**: Specialized validation and quality control agent
- **Performance Tracking**: Built-in stopping criteria and yield monitoring
- **Complete Documentation**: Comprehensive logging and reporting

## Workflow Execution Pattern

```
Master Orchestrator
│
├─ Loads country-specific parameters (gaps, priorities, context)
├─ Sequentially invokes specialized agents:
│  │
│  ├─ Agent 1: Baseline Data Collector
│  │  └─ Loads agent_1_priority_gaps.csv → targets 50 CRITICAL/HIGH gaps ≥30 days
│  │
│  ├─ Agent 2: Geographic Expansion Specialist  
│  │  └─ Loads agent_2_geographic_gaps.csv → adds 40 district/municipal gaps
│  │
│  ├─ Agent 3: Zero-Transmission Validator
│  │  └─ Loads agent_3_validation_gaps.csv → validates 60 absence periods (7 days-1 year)
│  │
│  ├─ Agent 4: Obscure Source Explorer
│  │  └─ Loads agent_4_historical_gaps.csv → mines 30 historical gaps (>5 years)
│  │
│  ├─ Agent 5: Cross-Reference Integrator
│  │  └─ Uses comprehensive_gaps_inventory.csv → exhaustive cross-validation
│  │
│  └─ Agent 6: Quality Auditor
│     └─ Integrates ALL gap files → quantitative gap-filling impact analysis
│
└─ Delivers complete enhanced dataset with quality metrics
```

## File Organization

### This Directory (`./subagents/`)
- Contains **only** the 6 agent configuration files (.md)
- Each file includes complete system prompt and tool specifications
- Clean, focused directory for subagent creation

### Supporting Infrastructure
- **Generation Script**: `../py/generate_country_orchestrator.py` 
- **Template File**: `../templates/template_workflow_orchestrator.txt`
- **Generated Orchestrators**: `../data/{ISO}/workflow_orchestrator_{ISO}.txt`
- **Comprehensive Gap Analysis**: `../py/analyze_integrated_coverage_gaps.py`
- **Reference Data**: 
  - `../reference/agent_quick_reference.csv` (country priorities)
  - `../reference/comprehensive_gaps_inventory.csv` (1,277 total gaps)
  - **Agent-Specific Gap Files**:
    - `../reference/agent_1_priority_gaps.csv` (50 CRITICAL/HIGH priority gaps)
    - `../reference/agent_2_geographic_gaps.csv` (40 geographic expansion gaps)
    - `../reference/agent_3_validation_gaps.csv` (60 zero-transmission validation gaps)
    - `../reference/agent_4_historical_gaps.csv` (30 historical/obscure gaps)

## Integration with MOSAIC Framework

### Data Sources Integration
- **JHU Historical Database**: Baseline coverage (1970-2020+)
- **WHO Dashboard Surveillance**: Recent data (2023-2025)  
- **AI Agent Discoveries**: Gap-filling enhancements

### Quality Standards
- **4-Tier Source Reliability**: Level 1 (WHO/Government) to Level 4 (Local media)
- **Dual-Reference Indexing**: Sequential integers ↔ exact source names
- **Confidence Weighting**: Quality-based modeling weights (0.1-1.0)
- **Zero-Transmission Documentation**: Absence periods as data observations

### Output Standards
- **Enhanced cholera_data_ai.csv**: AI discoveries with source_database: 'AI'
- **Complete metadata.csv**: Full source documentation and validation
- **Search logs**: Individual agent activity logs (search_log_agent_X.txt)
- **Quality report**: Executive summary (search_report.txt)

This subagent architecture transforms cholera surveillance data collection into a systematic, scalable, and quality-controlled process that maintains operational simplicity while delivering comprehensive coverage across all 40 MOSAIC framework countries.