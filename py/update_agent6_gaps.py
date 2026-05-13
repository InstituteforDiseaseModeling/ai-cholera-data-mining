#!/usr/bin/env python3
"""
Update Agent 6 to use optimized gap analysis files
"""

import re

# Read the agent 6 file
agent6_file = "./agents/agent_6_quality_auditor.md"

with open(agent6_file, 'r') as f:
    content = f.read()

# Define replacements
replacements = [
    # Replace old file references with new ones
    ("comprehensive_gaps = pd.read_csv('./reference/comprehensive_gaps_inventory.csv')",
     "gap_ranges = pd.read_csv('./reference/consolidated_gap_ranges.csv')"),
    
    ("agent1_priority = pd.read_csv('./reference/agent_1_priority_gaps.csv')",
     "gaps_summary = pd.read_csv('./reference/optimized_gaps_summary.csv')"),
    
    ("agent2_geographic = pd.read_csv('./reference/agent_2_geographic_gaps.csv')",
     "# Geographic gaps now in consolidated_gap_ranges.csv"),
    
    ("agent3_validation = pd.read_csv('./reference/agent_3_validation_gaps.csv')",
     "# Validation gaps now in consolidated_gap_ranges.csv"),
    
    ("agent4_historical = pd.read_csv('./reference/agent_4_historical_gaps.csv')",
     "# Historical gaps now in consolidated_gap_ranges.csv"),
    
    ("agent_reference = pd.read_csv('./reference/agent_quick_reference.csv')",
     "# Reference data now in optimized_gaps_summary.csv"),
    
    # Update variable references
    ("country_gaps = comprehensive_gaps[comprehensive_gaps['iso_code'] == target_iso]",
     "country_gaps = gap_ranges[gap_ranges['iso_code'] == target_iso]"),
    
    ("country_ref = agent_reference[agent_reference['iso_code'] == target_iso].iloc[0]",
     "country_ref = gaps_summary[gaps_summary['iso_code'] == target_iso].iloc[0]"),
    
    # Update priority tier references to use new priority field
    ("country_gaps['priority_tier'].value_counts()",
     "country_gaps['priority'].value_counts()"),
    
    ("country_gaps[country_gaps['priority_tier'] == 'CRITICAL']",
     "country_gaps[country_gaps['priority'] == 'HIGH']  # HIGH priority in new system"),
    
    ("country_gaps[country_gaps['priority_tier'] == 'HIGH']",
     "country_gaps[country_gaps['priority'] == 'HIGH']"),
    
    ("'tier': gap['priority_tier']",
     "'priority': gap['priority']"),
    
    ("gaps_filled if g['tier'] == 'CRITICAL'",
     "gaps_filled if g['priority'] == 'HIGH'"),
    
    ("gaps_filled if g['tier'] == 'HIGH'",
     "gaps_filled if g['priority'] == 'HIGH'"),
    
    # Update comprehensive gaps references
    ("comprehensive gap analysis",
     "consolidated gap analysis"),
    
    ("comprehensive_gaps_inventory.csv",
     "consolidated_gap_ranges.csv"),
    
    ("1,277 total gaps",
     "consolidated gap ranges"),
]

# Apply replacements
for old, new in replacements:
    content = content.replace(old, new)

# Update the loading section with better structure
new_loading_section = """**STEP 1: Load Optimized Gap Analysis Files (REQUIRED)**
```python
import pandas as pd

# Load optimized gap analysis files
gap_ranges = pd.read_csv('./reference/consolidated_gap_ranges.csv')
gaps_summary = pd.read_csv('./reference/optimized_gaps_summary.csv')

# Detect target country from existing files
import os
import glob
data_dirs = glob.glob('./data/*/')
target_iso = None
if data_dirs:
    target_iso = os.path.basename(data_dirs[0].rstrip('/'))

# Filter for target country
if target_iso:
    country_gaps = gap_ranges[gap_ranges['iso_code'] == target_iso]
    country_ref = gaps_summary[gaps_summary['iso_code'] == target_iso].iloc[0]
    
    print(f"Quality audit for {country_ref['country']} ({target_iso})")
    print(f"Total gap ranges identified: {len(country_gaps)}")
    print(f"Baseline coverage: {country_ref['coverage_pct']:.1f}%")
    print(f"Priority breakdown:")
    print(country_gaps['priority'].value_counts())
```"""

# Replace the old loading section
pattern = r'\*\*STEP 1: Load Comprehensive Gap Analysis Files.*?\n```python.*?```'
content = re.sub(pattern, new_loading_section, content, flags=re.DOTALL)

# Write updated content
with open(agent6_file, 'w') as f:
    f.write(content)

print("Agent 6 updated to use optimized gap analysis files")