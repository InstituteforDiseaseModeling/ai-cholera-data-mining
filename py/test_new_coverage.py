#!/usr/bin/env python3
"""Test the new coverage calculation with 1970-present fixed range"""

import pandas as pd
from pathlib import Path
from datetime import datetime

def calculate_coverage_fixed_range(iso_code, data_files):
    """Calculate coverage using fixed 1970-present range"""
    base_path = Path('/Users/johngiles/Library/CloudStorage/OneDrive-Bill&MelindaGatesFoundation/Projects/MOSAIC/ai-cholera-data-mining')
    country_dir = base_path / 'data' / iso_code
    
    # Fixed date range: 1970 to present
    min_year = 1970
    current_year = datetime.now().year
    total_months = (current_year - min_year + 1) * 12
    
    covered_months = set()
    
    for data_file in data_files:
        file_path = country_dir / data_file
        if file_path.exists():
            try:
                df = pd.read_csv(file_path)
                if not df.empty and 'TL' in df.columns:
                    for date_str in df['TL'].dropna():
                        try:
                            date = pd.to_datetime(date_str)
                            covered_months.add((date.year, date.month))
                        except:
                            continue
            except Exception as e:
                print(f"Error reading {data_file}: {e}")
                continue
    
    if not covered_months:
        return "0.0", 0, total_months
    
    # Count only months within the standard range
    covered_in_range = len([m for m in covered_months if 1970 <= m[0] <= current_year])
    total_covered = len(covered_months)
    
    # Calculate percentage
    if total_months > 0:
        percentage = round((covered_in_range / total_months) * 100, 1)
        # If we have data outside the standard range, indicate >100%
        if total_covered > covered_in_range:
            return ">100", covered_in_range, total_months
        else:
            return str(percentage), covered_in_range, total_months
    else:
        return "0.0", 0, total_months

# Test countries
for iso in ['AGO', 'BDI', 'ETH']:
    print(f"\n{'='*60}")
    print(f"Testing {iso} with fixed 1970-present range:")
    print(f"{'-'*60}")
    
    # Baseline (JHU + WHO)
    baseline_pct, baseline_covered, baseline_total = calculate_coverage_fixed_range(
        iso, ['cholera_data_jhu.csv', 'cholera_data_who.csv']
    )
    print(f"Baseline (JHU + WHO): {baseline_pct}% ({baseline_covered}/{baseline_total} months)")
    
    # After AI (JHU + WHO + AI)
    after_pct, after_covered, after_total = calculate_coverage_fixed_range(
        iso, ['cholera_data_jhu.csv', 'cholera_data_who.csv', 'cholera_data_ai.csv']
    )
    print(f"After AI (JHU + WHO + AI): {after_pct}% ({after_covered}/{after_total} months)")
    
    print(f"\nCorrect note format:")
    print(f"Workflow completed with all 7 agents; (baseline coverage {baseline_pct}% -> after {after_pct}% coverage)")