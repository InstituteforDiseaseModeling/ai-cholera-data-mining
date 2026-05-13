#!/usr/bin/env python3
"""
Fix agent prompts to properly use optimized gap analysis files
"""

import os
from pathlib import Path

# Agent files directory
AGENTS_DIR = "./agents"

# New gap loading section
NEW_GAP_LOADING_SECTION = """**STEP 2: Load Optimized Gap Analysis Files (MANDATORY)**
**CRITICAL**: Before beginning any searches, MUST load optimized gap analysis files:

**Primary Gap Targeting File**: `./reference/consolidated_gap_ranges.csv`
- Contains date ranges of missing data periods for each country
- Format: country, iso_code, gap_start, gap_end, gap_months, priority, coverage_pct
- Process gaps by priority (HIGH > MEDIUM > LOW) and chronologically within each priority

**Secondary Reference**: `./reference/optimized_gaps_summary.csv` for country-level context
- Country-specific coverage percentage, priority level, and gap count
- Memory-optimized format without full month lists

**STEP 3: Optimized Gap-Targeted Search Strategy**
ALL search queries must target specific gap date ranges:

**Optimized Query Generation**:
```python
# Load consolidated gap ranges file
gap_ranges = pd.read_csv('./reference/consolidated_gap_ranges.csv')

# Filter for target country
country_gaps = gap_ranges[gap_ranges['iso_code'] == target_iso]

# Process by priority
high_priority_gaps = country_gaps[country_gaps['priority'] == 'HIGH']

# Generate queries for each gap range
for _, gap in high_priority_gaps.iterrows():
    gap_start = gap['gap_start']
    gap_end = gap['gap_end']
    gap_months = gap['gap_months']
    
    # Extract years from gap range
    start_year = int(gap_start[:4])
    end_year = int(gap_end[:4])
    
    # Generate year-specific queries
    for year in range(start_year, end_year + 1):
        query1 = f"{gap['country']} cholera {year} outbreak cases deaths WHO"
        query2 = f"{gap['country']} cholera {year} surveillance government ministry"
        # Execute queries...
```"""

def fix_agent_file(file_path):
    """Fix a single agent file to properly use optimized gap files."""
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Find the section to replace
    start_idx = None
    end_idx = None
    
    for i, line in enumerate(lines):
        if "**STEP 2: Load" in line and "Gap Analysis Files" in line:
            start_idx = i
        elif start_idx is not None and ("**STEP 3:" in line or "**STEP 4:" in line or "## Your Core" in line):
            # Find where Step 3 content ends
            for j in range(i+1, len(lines)):
                if "**Search Allocation" in lines[j] or "**Mandatory Gap" in lines[j] or "## Your Core" in lines[j]:
                    end_idx = j
                    break
            if end_idx is None:
                end_idx = i + 20  # Default to 20 lines after Step 3 start
            break
    
    if start_idx is not None and end_idx is not None:
        # Replace the section
        new_lines = lines[:start_idx]
        new_lines.append(NEW_GAP_LOADING_SECTION + "\n\n")
        
        # Find where to continue from (after the old Step 3 content)
        continue_from = end_idx
        new_lines.extend(lines[continue_from:])
        
        # Write back
        with open(file_path, 'w') as f:
            f.writelines(new_lines)
        return True
    
    return False

def main():
    """Fix all agent files."""
    
    agents_dir = Path(AGENTS_DIR)
    if not agents_dir.exists():
        print(f"Agents directory not found: {AGENTS_DIR}")
        return
    
    updated_count = 0
    
    # Process specific agent files that need fixing
    agent_files = [
        "agent_1_baseline_collector.md",
        "agent_2_geographic_expansion.md", 
        "agent_3_zero_transmission.md",
        "agent_4_obscure_sources.md",
        "agent_5_cross_reference.md"
    ]
    
    for agent_file_name in agent_files:
        agent_file = agents_dir / agent_file_name
        if agent_file.exists():
            print(f"Fixing {agent_file_name}...")
            if fix_agent_file(agent_file):
                print(f"  ✓ Fixed {agent_file_name}")
                updated_count += 1
            else:
                print(f"  - Could not fix {agent_file_name}")
    
    print(f"\nFixed {updated_count} agent files")
    
    # Clean up old files that are no longer needed
    print("\n=== CLEANUP: Removing old gap analysis files ===")
    old_files = [
        "./reference/agent_1_simple_gaps.csv",
        "./reference/agent_2_simple_gaps.csv",
        "./reference/agent_3_simple_gaps.csv",
        "./reference/agent_4_simple_gaps.csv",
        "./reference/agent_5_simple_gaps.csv",
        "./reference/simple_gaps_summary.csv",
        "./reference/simple_national_gaps.csv"
    ]
    
    for old_file in old_files:
        if os.path.exists(old_file):
            os.remove(old_file)
            print(f"  ✓ Removed {old_file}")

if __name__ == "__main__":
    main()