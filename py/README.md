# MOSAIC AI Cholera Data Collection - Python Scripts

This directory contains the essential Python scripts for the MOSAIC AI Cholera Data Collection project. The scripts have been consolidated and streamlined to eliminate deprecated functionality and reduce duplication.

## 📋 **CORE SCRIPTS (Essential)**

### **1. configure_countries.py** 🔧
**Purpose**: Creates directories and customized workflow files for all 40 MOSAIC framework countries
- **Usage**: `python py/configure_countries.py`
- **Output**: Country-specific directories and workflow files in `./data/{ISO}/`
- **When to run**: Initial project setup, or when adding new countries
- **Dependencies**: Requires `reference/country_mapping.json`

### **2. update_dashboard_data.py** 📊
**Purpose**: **UNIFIED DASHBOARD UPDATER** - Single command to update all dashboard components
- **Usage**: `python py/update_dashboard_data.py` or `bash update_dashboard.sh`
- **What it does**:
  - Updates completion checklist based on file analysis
  - Generates 3-source timeline coverage plots (AI, WHO, JHU)
  - Creates timeline week counts CSV
  - Updates dashboard HTML with embedded data
- **When to run**: After agent completions, for dashboard refresh
- **Replaces**: Multiple previous scripts (timeline plots, week counts, checklist updates)

### **3. initialize_country.py** 🚀
**Purpose**: Automated country initialization for Agent 1 workflow start
- **Usage**: `python py/initialize_country.py {ISO_CODE}`
- **What it does**:
  - Creates initial Agent 1 log file
  - Prepares country for workflow execution
  - Provides initialization confirmation
- **When to run**: When starting work on a new country

## 📚 **REFERENCE DATA GENERATORS**

### **5. get_iso_codes.py** 🌍
**Purpose**: Extracts and formats ISO country codes from MOSAIC data
- **Usage**: `python py/get_iso_codes.py`
- **Output**: Country mapping files in `reference/`
- **When to run**: When updating country lists or reference data
- **Features**: Generates mapping files, ISO lists, usage instructions

### **6. get_surveillance_gaps.py** 📊
**Purpose**: Creates agent-friendly surveillance coverage reference with gap analysis
- **Usage**: `python py/get_surveillance_gaps.py`
- **Output**: `reference/agent_quick_reference.csv` with gap targeting data
- **When to run**: When updating surveillance coverage analysis
- **Features**: Gap identification, priority period analysis, agent-friendly formats

## 🔬 **SPECIALIZED DATA ANALYSIS**

### **7. generate_monthly_surveillance_matrix_v2.py** 📅
**Purpose**: Creates comprehensive monthly surveillance matrix using full MOSAIC data
- **Usage**: `python py/generate_monthly_surveillance_matrix_v2.py`
- **Output**: Monthly matrix format for surveillance analysis
- **When to run**: For monthly analysis and reporting needs
- **Use case**: Monthly surveillance reports, trend analysis

## 🛠️ **MAINTENANCE UTILITIES**

### **9. update_workflow_dashboard_commands.py** 🔄
**Purpose**: Updates existing country workflow files with unified dashboard commands
- **Usage**: `python py/update_workflow_dashboard_commands.py`
- **What it does**: Systematically updates all 40 country workflow files
- **When to run**: When updating workflow templates or dashboard commands
- **Use case**: Maintenance, workflow standardization

## 🎯 **USAGE PATTERNS**

### **Daily Agent Workflow**
```bash
# Agent 1 initialization
python py/initialize_country.py {ISO_CODE}

# After each agent completion
bash update_dashboard.sh
```

### **Project Setup**
```bash
# Initial setup (run once)
python py/configure_countries.py
python py/get_iso_codes.py
python py/get_surveillance_gaps.py
```

### **Data Analysis**
```bash
# Specialized exports (as needed)
# python py/generate_weekly_surveillance_longform.py  # REMOVED - no longer needed
python py/generate_monthly_surveillance_matrix_v2.py
```

### **Maintenance**
```bash
# Update workflows (when needed)
python py/update_workflow_dashboard_commands.py
```

## 📈 **SCRIPT CONSOLIDATION HISTORY**

### **Removed (Deprecated)**
- `generate_timeline_plots.py` → Replaced by 3-source version
- `generate_monthly_surveillance_matrix.py` → Replaced by v2
- `generate_timeline_plots_3sources.py` → REMOVED (deprecated, replaced by dual_timeline plots)
- `generate_timeline_week_counts.py` → Integrated into unified dashboard updater
- `generate_timeline_data.py` → Replaced by PNG plot system

### **Key Improvements**
- **Unified Dashboard System**: Single command replaces multiple scripts
- **Eliminated Duplication**: Removed superseded versions
- **Better Organization**: Clear separation of core vs specialized scripts
- **Simplified Workflow**: Agents only need to know `bash update_dashboard.sh`

## 🔧 **DEPENDENCIES**

### **Required Python Packages**
- `pandas` - Data processing
- `matplotlib` - Plot generation
- `pathlib` - File path management
- `json` - Configuration file handling
- `csv` - Data file processing
- `PIL` (Pillow) - Image processing for plot cropping

### **Required Data Files**
- `reference/country_mapping.json` - Country information
- `../MOSAIC-data/processed/cholera/weekly/` - Surveillance data
- `./data/{ISO}/cholera_data.csv` - AI-enhanced data

## 📝 **NOTES**

- All scripts are designed to be run from the project root directory
- The unified dashboard system (`update_dashboard_data.py`) is the main entry point for dashboard updates
- Specialized scripts are maintained for specific analysis needs but are not part of the daily workflow
- Country-specific files are automatically generated and should not be manually edited
- The script collection has been optimized for maintainability and ease of use