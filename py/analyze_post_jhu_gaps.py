#!/usr/bin/env python3
"""
Post-JHU Integration Gap Analysis

This script analyzes data coverage gaps AFTER JHU baseline integration,
updating the agent_quick_reference.csv to reflect remaining priorities
for AI agent searches.

The goal is to focus AI agents on periods NOT covered by JHU data.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from pathlib import Path
import json

# Configuration
OUTPUT_DATA_PATH = "./data"
REFERENCE_PATH = "./reference"
SURVEILLANCE_DATA_PATH = "../MOSAIC-data/processed/cholera/weekly/cholera_surveillance_weekly_combined.csv"

def load_country_mapping():
    """Load country name to ISO code mapping."""
    try:
        with open(f"{REFERENCE_PATH}/country_mapping.json", 'r') as f:
            data = json.load(f)
        
        # Extract countries from the nested structure
        countries = data.get('countries', {})
        return {v['name']: k for k, v in countries.items() if v.get('mosaic_framework', False)}
    except FileNotFoundError:
        print(f"Warning: country_mapping.json not found")
        return {}

def load_surveillance_reference():
    """Load WHO surveillance data for comparison."""
    try:
        if os.path.exists(SURVEILLANCE_DATA_PATH):
            df = pd.read_csv(SURVEILLANCE_DATA_PATH)
            return df
        else:
            print(f"Warning: WHO surveillance data not found at {SURVEILLANCE_DATA_PATH}")
            return pd.DataFrame()
    except Exception as e:
        print(f"Warning: Could not load surveillance data: {e}")
        return pd.DataFrame()

def analyze_country_coverage(country_iso, country_name):
    """
    Analyze coverage for a single country after JHU integration.
    
    Returns dict with coverage metrics and gap periods.
    """
    
    country_data_path = f"{OUTPUT_DATA_PATH}/{country_iso}"
    
    # Check if country has JHU data
    if not os.path.exists(f"{country_data_path}/cholera_data.csv"):
        return {
            'iso_code': country_iso,
            'country': country_name,
            'coverage_pct': 0.0,
            'data_span': 'No data',
            'search_priority': 'HIGH',
            'missing_recent_years': '2000-2024',
            'priority_periods': 'Complete data collection needed',
            'total_observations': 0,
            'earliest_date': None,
            'latest_date': None,
            'has_jhu_baseline': False
        }
    
    # Load JHU baseline data
    try:
        data_df = pd.read_csv(f"{country_data_path}/cholera_data.csv")
        
        # Parse dates
        data_df['TL'] = pd.to_datetime(data_df['TL'])
        data_df['TR'] = pd.to_datetime(data_df['TR'])
        
        # Calculate coverage metrics
        earliest_date = data_df['TL'].min()
        latest_date = data_df['TR'].max()
        total_observations = len(data_df)
        
        # Calculate coverage percentage (very rough estimate based on expected weekly data)
        date_range_days = (latest_date - earliest_date).days
        expected_weeks = date_range_days / 7
        coverage_pct = min((total_observations / expected_weeks) * 100, 100) if expected_weeks > 0 else 0
        
        # Identify major gaps
        data_df = data_df.sort_values('TL')
        gaps = []
        
        for i in range(1, len(data_df)):
            prev_end = data_df.iloc[i-1]['TR']
            curr_start = data_df.iloc[i]['TL']
            gap_days = (curr_start - prev_end).days
            
            # Consider gaps > 365 days as significant
            if gap_days > 365:
                gaps.append((prev_end, curr_start))
        
        # Determine priority based on coverage and recency
        current_year = datetime.now().year
        has_recent_data = latest_date.year >= (current_year - 2)
        
        if coverage_pct < 50:
            priority = 'HIGH'
        elif coverage_pct < 80:
            priority = 'MEDIUM'
        else:
            priority = 'LOW'
        
        # Identify missing recent years (last 5 years)
        recent_years = list(range(current_year - 5, current_year + 1))
        data_years = set(data_df['TL'].dt.year.unique())
        missing_recent = [str(year) for year in recent_years if year not in data_years]
        
        # Format priority periods
        if gaps:
            # Focus on the most recent major gap
            latest_gap = max(gaps, key=lambda x: x[1])
            priority_periods = f"{latest_gap[0].strftime('%Y-%m-%d')} to {latest_gap[1].strftime('%Y-%m-%d')}"
        elif not has_recent_data:
            priority_periods = f"{latest_date.strftime('%Y-%m-%d')} to {current_year}-12-31"
        else:
            priority_periods = f"Pre-{earliest_date.year} and post-{latest_date.year} extension"
        
        return {
            'iso_code': country_iso,
            'country': country_name,
            'coverage_pct': round(coverage_pct, 1),
            'data_span': f"{earliest_date.year}-{latest_date.year}",
            'search_priority': priority,
            'missing_recent_years': ', '.join(missing_recent) if missing_recent else 'None',
            'priority_periods': priority_periods,
            'total_observations': total_observations,
            'earliest_date': earliest_date,
            'latest_date': latest_date,
            'has_jhu_baseline': True
        }
        
    except Exception as e:
        print(f"Error analyzing {country_iso}: {e}")
        return None

def main():
    """Generate post-JHU integration gap analysis."""
    
    print("================================================================================")
    print("POST-JHU INTEGRATION GAP ANALYSIS")
    print("================================================================================")
    print("Analyzing data coverage after JHU baseline integration...")
    print("Goal: Focus AI agents on gaps NOT covered by JHU data")
    print("")
    
    # Load country mapping
    country_mapping = load_country_mapping()
    if not country_mapping:
        print("❌ Could not load country mapping")
        return
    
    # Load surveillance reference (optional)
    surveillance_df = load_surveillance_reference()
    
    # Analyze each country
    results = []
    high_priority = []
    medium_priority = []
    low_priority = []
    
    print("Analyzing coverage for 40 MOSAIC framework countries...")
    
    for country_name, country_iso in country_mapping.items():
        print(f"  Analyzing {country_iso} ({country_name})...")
        
        result = analyze_country_coverage(country_iso, country_name)
        if result:
            results.append(result)
            
            # Categorize by priority
            if result['search_priority'] == 'HIGH':
                high_priority.append(result)
            elif result['search_priority'] == 'MEDIUM':
                medium_priority.append(result)
            else:
                low_priority.append(result)
    
    # Sort results by priority and coverage
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values(['search_priority', 'coverage_pct'])
    
    # Save updated agent quick reference
    output_file = f"{REFERENCE_PATH}/agent_quick_reference.csv"
    results_df.to_csv(output_file, index=False)
    
    print("")
    print("================================================================================")
    print("POST-JHU GAP ANALYSIS COMPLETE")
    print("================================================================================")
    print(f"📊 Total countries analyzed: {len(results)}")
    print(f"🔴 HIGH priority (AI focus): {len(high_priority)} countries")
    print(f"🟡 MEDIUM priority: {len(medium_priority)} countries") 
    print(f"🟢 LOW priority: {len(low_priority)} countries")
    print("")
    
    # Detailed priority breakdown
    if high_priority:
        print("🔴 HIGH PRIORITY countries (major gaps, AI agents should focus here):")
        for result in sorted(high_priority, key=lambda x: x['coverage_pct']):
            print(f"   • {result['country']} ({result['iso_code']}): {result['coverage_pct']:.1f}% coverage, {result['total_observations']} observations")
        print("")
    
    if medium_priority:
        print("🟡 MEDIUM PRIORITY countries (partial coverage, moderate AI effort):")
        for result in sorted(medium_priority, key=lambda x: x['coverage_pct']):
            print(f"   • {result['country']} ({result['iso_code']}): {result['coverage_pct']:.1f}% coverage, {result['total_observations']} observations")
        print("")
    
    if low_priority:
        print("🟢 LOW PRIORITY countries (good JHU coverage, minimal AI needed):")
        for result in sorted(low_priority, key=lambda x: x['coverage_pct']):
            print(f"   • {result['country']} ({result['iso_code']}): {result['coverage_pct']:.1f}% coverage, {result['total_observations']} observations")
        print("")
    
    print(f"✅ Updated agent reference saved: {output_file}")
    print("")
    print("🎯 RECOMMENDATIONS FOR AI AGENTS:")
    print("• Focus searches on HIGH priority countries first")
    print("• Target specific priority_periods identified for each country")
    print("• Use JHU baseline data as reference for validation")
    print("• Countries with 'No data' need complete systematic searches")
    print("")
    print("📈 IMPACT OF JHU INTEGRATION:")
    total_obs = sum(r['total_observations'] for r in results)
    countries_with_data = len([r for r in results if r['has_jhu_baseline']])
    print(f"• {total_obs:,} total observations now available across {countries_with_data} countries")
    print(f"• Substantial baseline data reduces AI search workload")
    print(f"• AI agents can now focus on targeted gap-filling vs. broad discovery")
    print("================================================================================")

if __name__ == "__main__":
    main()