#!/usr/bin/env python3
"""
Update all existing country workflow files with unified dashboard update commands

This script updates all existing agentic_workflow_{ISO}.txt files to use the new
unified dashboard update system (bash update_dashboard.sh) instead of the old
separate commands.
"""

import os
import re
from pathlib import Path

def update_workflow_file(file_path: Path):
    """Update a single workflow file with unified dashboard commands"""
    
    if not file_path.exists():
        return False
        
    try:
        # Read the current content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Update 1: Pre-workflow initialization
        old_init_pattern = r'1\. \*\*Initialize Dashboard Tracking\*\*: Create initialization marker and update dashboard immediately'
        new_init_text = '''1. **Initialize Dashboard Tracking**: Create initialization marker and update dashboard immediately
```bash
echo "=== AGENT 1 INITIALIZATION ===" > ./data/{ISO_CODE}/search_log_agent_1.txt
echo "Country: {COUNTRY_NAME} ({ISO_CODE})" >> ./data/{ISO_CODE}/search_log_agent_1.txt
echo "Start Time: $(date '+%Y-%m-%d %H:%M:%S')" >> ./data/{ISO_CODE}/search_log_agent_1.txt
bash update_dashboard.sh
```'''
        
        content = re.sub(old_init_pattern, new_init_text, content)
        
        # Update 2: Agent 1 completion
        old_agent1_pattern = r'\*\*AGENT 1 COMPLETION: FOCUS ON DATA QUALITY\*\*\n\*\*Dashboard Updates Automatically\*\* - focus on completing data collection files:'
        new_agent1_text = '''**AGENT 1 COMPLETION: FOCUS ON DATA QUALITY**
**MANDATORY DASHBOARD UPDATE** - Update all dashboard data after completing Agent 1:
```bash
bash update_dashboard.sh
```
This updates: completion checklist (PENDING status), timeline plots with initial data, source counts, and observation metrics.

**Data Quality Requirements**:'''
        
        content = re.sub(old_agent1_pattern, new_agent1_text, content)
        
        # Update 3: Agent 2 completion
        old_agent2_pattern = r'\*\*AGENT 2 COMPLETION: FOCUS ON DATA QUALITY\*\*\n\*\*Dashboard Updates Automatically\*\* - focus on completing expanded dataset:'
        new_agent2_text = '''**AGENT 2 COMPLETION: FOCUS ON DATA QUALITY**
**RECOMMENDED DASHBOARD UPDATE** - Update dashboard data after completing Agent 2:
```bash
bash update_dashboard.sh
```
This updates: timeline plots with geographic expansion data, enhanced source counts, and improved coverage visualization.

**Data Quality Requirements**:'''
        
        content = re.sub(old_agent2_pattern, new_agent2_text, content)
        
        # Update 4: Agent 3 completion
        old_agent3_pattern = r'\*\*AGENT 3 COMPLETION: FOCUS ON DATA QUALITY\*\*\n\*\*Dashboard Updates Automatically\*\* - focus on completing absence documentation:'
        new_agent3_text = '''**AGENT 3 COMPLETION: FOCUS ON DATA QUALITY**
**RECOMMENDED DASHBOARD UPDATE** - Update dashboard data after completing Agent 3:
```bash
bash update_dashboard.sh
```
This updates: timeline plots with validated zero-transmission periods, comprehensive coverage gaps filled, enhanced temporal completeness.

**Data Quality Requirements**:'''
        
        content = re.sub(old_agent3_pattern, new_agent3_text, content)
        
        # Update 5: Agent 4 completion
        old_agent4_pattern = r'\*\*AGENT 4 COMPLETION: FOCUS ON DATA QUALITY\*\*\n\*\*Dashboard Updates Automatically\*\* - focus on completing obscure source integration:'
        new_agent4_text = '''**AGENT 4 COMPLETION: FOCUS ON DATA QUALITY**
**RECOMMENDED DASHBOARD UPDATE** - Update dashboard data after completing Agent 4:
```bash
bash update_dashboard.sh
```
This updates: timeline plots with obscure source discoveries, diversified source portfolio, enhanced data coverage from unconventional sources.

**Data Quality Requirements**:'''
        
        content = re.sub(old_agent4_pattern, new_agent4_text, content)
        
        # Update 6: Agent 5 completion
        old_agent5_pattern = r'\*\*AGENT 5 COMPLETION: FOCUS ON DATA QUALITY\*\*\n\*\*Dashboard Updates Automatically\*\* - focus on completing permutation discoveries:'
        new_agent5_text = '''**AGENT 5 COMPLETION: FOCUS ON DATA QUALITY**
**RECOMMENDED DASHBOARD UPDATE** - Update dashboard data after completing Agent 5:
```bash
bash update_dashboard.sh
```
This updates: timeline plots with final permutation discoveries, complete source network mapping, pre-audit data visualization.

**Data Quality Requirements**:'''
        
        content = re.sub(old_agent5_pattern, new_agent5_text, content)
        
        # Update 7: Agent 6 focus areas - add final dashboard update
        old_agent6_pattern = r'(### \*\*Agent 6 Focus Areas:\*\*\n- \*\*File Completion\*\*: Ensure all required files are present and properly formatted\n- \*\*Data Validation\*\*: Complete quality audit of all sources and observations  \n- \*\*Documentation\*\*: Final search_log\.txt and search_report\.txt consolidation\n- \*\*System Integration\*\*: Verify dataset ready for MOSAIC modeling integration)'
        
        new_agent6_text = r'''\1

**MANDATORY FINAL DASHBOARD UPDATE** - Update all dashboard data after completing Agent 6:
```bash
bash update_dashboard.sh
```
This final update: marks country COMPLETED, generates final timeline plots, updates completion statistics, embeds final data in dashboard.'''
        
        content = re.sub(old_agent6_pattern, new_agent6_text, content)
        
        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def main():
    """Update all country workflow files"""
    print("=" * 80)
    print("UPDATING ALL COUNTRY WORKFLOW FILES WITH UNIFIED DASHBOARD COMMANDS")
    print("=" * 80)
    
    base_path = Path(__file__).parent.parent
    data_dir = base_path / "data"
    
    # Find all workflow files
    workflow_files = list(data_dir.glob("*/agentic_workflow_*.txt"))
    
    print(f"Found {len(workflow_files)} country workflow files to update...")
    
    updated_count = 0
    
    for workflow_file in sorted(workflow_files):
        iso_code = workflow_file.name.replace('agentic_workflow_', '').replace('.txt', '')
        print(f"  Updating {iso_code}...")
        
        if update_workflow_file(workflow_file):
            updated_count += 1
            print(f"    ✅ Updated: {workflow_file.name}")
        else:
            print(f"    ⭕ No changes needed: {workflow_file.name}")
    
    print("\n" + "=" * 80)
    print(f"✅ WORKFLOW UPDATE COMPLETE!")
    print(f"📁 Files processed: {len(workflow_files)}")
    print(f"🔄 Files updated: {updated_count}")
    print(f"⭕ No changes needed: {len(workflow_files) - updated_count}")
    print("\n🎯 All country workflows now use unified dashboard update system:")
    print("   - bash update_dashboard.sh")
    print("   - Consistent across all agents")
    print("   - Complete dashboard synchronization")
    print("=" * 80)

if __name__ == "__main__":
    main()