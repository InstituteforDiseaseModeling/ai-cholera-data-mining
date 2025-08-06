#!/usr/bin/env python3
"""
MOSAIC AI Cholera Data Collection - Country Initialization Script
Creates initial Agent 1 log file and immediately updates dashboard tracking.

USAGE: python py/initialize_country.py <ISO_CODE>
Example: python py/initialize_country.py ETH

This script:
1. Creates search_log_agent_1.txt with initialization timestamp
2. Note: Dashboard update is now handled by workflow orchestrator
3. Provides confirmation of initialization
"""

import sys
import os
from datetime import datetime
from pathlib import Path
import subprocess

def initialize_country(iso_code: str):
    """Initialize a country for Agent 1 processing"""
    
    # Validate ISO code
    iso_code = iso_code.upper().strip()
    if len(iso_code) != 3:
        print(f"❌ ERROR: ISO code must be 3 characters (got: {iso_code})")
        return False
    
    # Get base path and country directory
    base_path = Path(__file__).parent.parent
    country_dir = base_path / "data" / iso_code
    
    # Check if country directory exists
    if not country_dir.exists():
        print(f"❌ ERROR: Country directory not found: {country_dir}")
        print("Run setup.sh first to create country directories")
        return False
    
    # Load country name from reference
    try:
        import json
        mapping_file = base_path / "reference" / "country_mapping.json"
        with open(mapping_file, 'r') as f:
            country_mapping = json.load(f)
        country_name = country_mapping.get('countries', {}).get(iso_code, {}).get('name', 'UNKNOWN')
    except:
        country_name = 'UNKNOWN'
    
    # Create initial log file
    log_file = country_dir / "search_log_agent_1.txt"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    log_content = f"""=== AGENT 1 INITIALIZATION ===
Country: {country_name} ({iso_code})
Start Time: {timestamp}
Agent 1 Status: INITIALIZED

Workflow orchestrator will update dashboard to show PENDING status.
Beginning systematic search protocol...

"""
    
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(log_content)
        print(f"✅ Created: {log_file}")
    except Exception as e:
        print(f"❌ ERROR creating log file: {e}")
        return False
    
    # Note: Dashboard update now handled by workflow orchestrator
    print("📊 Note: Dashboard will be updated by workflow orchestrator")
    print(f"🎯 Country {iso_code} is ready for workflow execution")
    
    # Success message
    print(f"""
🚀 INITIALIZATION COMPLETE FOR {iso_code}
================================================================================
✅ Agent 1 log file created: {log_file}
✅ Dashboard will be updated when workflow orchestrator runs  
✅ Ready to begin systematic search protocol

Next Steps:
1. Follow the 6-agent workflow in: ./data/{iso_code}/agentic_workflow_{iso_code}.txt
2. Begin Agent 1 systematic search methodology
3. Dashboard will auto-track progress through completion

Agent 1 is ready to proceed with search protocol!
================================================================================
""")
    
    return True

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python py/initialize_country.py <ISO_CODE>")
        print("Example: python py/initialize_country.py ETH")
        sys.exit(1)
    
    iso_code = sys.argv[1]
    success = initialize_country(iso_code)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()