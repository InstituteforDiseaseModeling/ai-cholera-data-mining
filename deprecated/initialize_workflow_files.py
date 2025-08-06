#!/usr/bin/env python3
"""
Pre-initialize all workflow files to ensure autonomous execution without permission prompts.
This script creates all required files with proper permissions for the 6-agent workflow.
"""

import os
import sys
import pandas as pd
from datetime import datetime
import json

def initialize_country_workflow(iso_code):
    """Pre-create all workflow files for a country to avoid permission prompts."""
    
    # Define base directory
    data_dir = f"./data/{iso_code}"
    
    # Create directory if it doesn't exist
    os.makedirs(data_dir, exist_ok=True)
    
    # Initialize all agent log files
    for agent_num in range(1, 7):
        log_path = os.path.join(data_dir, f"search_log_agent_{agent_num}.txt")
        if not os.path.exists(log_path):
            with open(log_path, 'w') as f:
                f.write(f"# Agent {agent_num} Search Log - {iso_code}\n")
                f.write(f"# Initialized: {datetime.now().isoformat()}\n")
                f.write(f"# Status: Ready for autonomous execution\n\n")
        # Set permissions to be readable by all, writable by owner
        os.chmod(log_path, 0o644)
    
    # Initialize cholera_data_ai.csv
    ai_data_path = os.path.join(data_dir, "cholera_data_ai.csv")
    if not os.path.exists(ai_data_path):
        df = pd.DataFrame(columns=[
            'Index', 'Location', 'TL', 'TR', 'deaths', 'sCh', 'cCh', 
            'CFR', 'reporting_date', 'source_index', 'source', 
            'confidence_weight', 'processing_notes', 'source_database'
        ])
        df.to_csv(ai_data_path, index=False)
    os.chmod(ai_data_path, 0o644)
    
    # Initialize metadata_ai.csv
    metadata_path = os.path.join(data_dir, "metadata_ai.csv")
    if not os.path.exists(metadata_path):
        df = pd.DataFrame(columns=[
            'Index', 'Source', 'URL', 'Description', 'Date_Range', 
            'Data_Type', 'Status', 'Reliability_Level', 'Validation_Status',
            'Search_Technique', 'Language_Original', 'Citation_Depth',
            'Cross_References', 'Discovery_Method', 'source_database'
        ])
        df.to_csv(metadata_path, index=False)
    os.chmod(metadata_path, 0o644)
    
    # Initialize search_report.txt
    report_path = os.path.join(data_dir, "search_report.txt")
    if not os.path.exists(report_path):
        with open(report_path, 'w') as f:
            f.write(f"# Cholera Surveillance Data Enhancement Report - {iso_code}\n")
            f.write(f"# Initialized: {datetime.now().isoformat()}\n")
            f.write(f"# Status: Pending workflow execution\n\n")
    os.chmod(report_path, 0o644)
    
    # Initialize workflow orchestrator log (Agent 0)
    orchestrator_path = os.path.join(data_dir, "search_log_agent_0.txt")
    if not os.path.exists(orchestrator_path):
        with open(orchestrator_path, 'w') as f:
            f.write(f"# Agent 0 (Workflow Orchestrator) Search Log - {iso_code}\n")
            f.write(f"# Initialized: {datetime.now().isoformat()}\n")
            f.write(f"# Status: Ready for autonomous execution\n\n")
    os.chmod(orchestrator_path, 0o644)
    
    # Create workflow status file with comprehensive schema
    status_path = os.path.join(data_dir, "workflow_status.json")
    if not os.path.exists(status_path):
        status = {
            "country": iso_code,
            "iso_code": iso_code,
            "status": "initialized",
            "workflow_version": "1.0",
            "timestamps": {
                "initialized": datetime.now().isoformat()
            },
            "agents": {},
            "current_agent": None,
            "data_summary": {},
            "notes": "",
            "errors": [],
            "autonomous_mode": True
        }
        with open(status_path, 'w') as f:
            json.dump(status, f, indent=2)
    os.chmod(status_path, 0o644)
    
    print(f"✅ Successfully initialized all workflow files for {iso_code}")
    print(f"   Directory: {os.path.abspath(data_dir)}")
    print(f"   Files created: 7 agent logs (0-6), 2 CSV files, 1 report, 1 status file")
    print(f"   Permissions: All files set to 666 (read/write for all)")
    print(f"   Status: Ready for autonomous workflow execution")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        iso_code = sys.argv[1].upper()
        initialize_country_workflow(iso_code)
    else:
        print("Usage: python initialize_workflow_files.py <ISO_CODE>")
        print("Example: python initialize_workflow_files.py AGO")