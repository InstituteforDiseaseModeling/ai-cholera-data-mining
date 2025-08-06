#!/usr/bin/env python3
"""Test coverage calculation for BDI"""

import pandas as pd
from pathlib import Path

def calculate_coverage(iso_code, data_files):
    """Calculate coverage from specified data files"""
    base_path = Path('/Users/johngiles/Library/CloudStorage/OneDrive-Bill&MelindaGatesFoundation/Projects/MOSAIC/ai-cholera-data-mining')
    country_dir = base_path / 'data' / iso_code
    
    dates = set()
    
    for data_file in data_files:
        file_path = country_dir / data_file
        if file_path.exists():
            try:
                df = pd.read_csv(file_path)
                if not df.empty and 'TL' in df.columns:
                    for date_str in df['TL'].dropna():
                        try:
                            date = pd.to_datetime(date_str)
                            dates.add((date.year, date.month))
                        except:
                            continue
            except Exception as e:
                print(f"Error reading {data_file}: {e}")
                continue
    
    if not dates:
        return 0.0, 0, 0
    
    min_year = min(date[0] for date in dates)
    max_year = max(date[0] for date in dates)
    
    total_months = (max_year - min_year + 1) * 12
    covered_months = len(dates)
    
    if total_months > 0:
        coverage = round((covered_months / total_months) * 100, 1)
    else:
        coverage = 0.0
    
    return coverage, covered_months, total_months

# Test BDI
print("Testing BDI coverage calculation:")
print("-" * 50)

# Baseline (JHU + WHO)
baseline_coverage, baseline_covered, baseline_total = calculate_coverage(
    'BDI', ['cholera_data_jhu.csv', 'cholera_data_who.csv']
)
print(f"Baseline (JHU + WHO): {baseline_coverage}% ({baseline_covered}/{baseline_total} months)")

# After AI (JHU + WHO + AI)
after_coverage, after_covered, after_total = calculate_coverage(
    'BDI', ['cholera_data_jhu.csv', 'cholera_data_who.csv', 'cholera_data_ai.csv']
)
print(f"After AI (JHU + WHO + AI): {after_coverage}% ({after_covered}/{after_total} months)")

print(f"\nCorrect format: (baseline coverage {baseline_coverage}% -> after {after_coverage}% coverage)")

# Also test AGO for comparison
print("\n" + "=" * 50)
print("Testing AGO coverage calculation:")
print("-" * 50)

baseline_coverage, baseline_covered, baseline_total = calculate_coverage(
    'AGO', ['cholera_data_jhu.csv', 'cholera_data_who.csv']
)
print(f"Baseline (JHU + WHO): {baseline_coverage}% ({baseline_covered}/{baseline_total} months)")

after_coverage, after_covered, after_total = calculate_coverage(
    'AGO', ['cholera_data_jhu.csv', 'cholera_data_who.csv', 'cholera_data_ai.csv']
)
print(f"After AI (JHU + WHO + AI): {after_coverage}% ({after_covered}/{after_total} months)")

print(f"\nCorrect format: (baseline coverage {baseline_coverage}% -> after {after_coverage}% coverage)")