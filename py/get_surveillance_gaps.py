#!/usr/bin/env python3
"""
Create agent-friendly surveillance coverage reference files.

This script creates multiple formats optimized for AI agents working on 
cholera surveillance data gap identification and collection.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

def create_agent_friendly_reference(input_file):
    """
    Create agent-friendly reference files for surveillance data coverage.
    
    Args:
        input_file (str): Path to input CSV file
    """
    
    print(f"Loading data from: {input_file}")
    
    try:
        # Load the data
        df = pd.read_csv(input_file)
        print(f"Loaded {len(df)} rows of data")
        
        # Convert date columns to datetime
        df['date_start'] = pd.to_datetime(df['date_start'])
        df['date_stop'] = pd.to_datetime(df['date_stop'])
        
        # Identify observed data (non-NA cases, deaths, or source)
        observed_mask = (
            (df['cases'].notna()) | 
            (df['deaths'].notna()) | 
            (df['source'].notna())
        )
        
        observed_data = df[observed_mask].copy()
        print(f"Found {len(observed_data)} rows with observed data")
        
        if len(observed_data) == 0:
            print("No observed data found!")
            return
        
        # Get overall time range
        overall_start = observed_data['date_start'].min()
        overall_end = observed_data['date_stop'].max()
        
        results = []
        gap_results = []
        
        for country_code in sorted(observed_data['iso_code'].unique()):
            country_data = observed_data[observed_data['iso_code'] == country_code].copy()
            country_name = country_data['country'].iloc[0]
            
            # Sort by date
            country_data = country_data.sort_values('date_start')
            
            # Get country's data range
            country_start = country_data['date_start'].min()
            country_end = country_data['date_stop'].max()
            
            # Find continuous periods (allowing for small gaps)
            periods = []
            current_start = None
            current_end = None
            
            for _, row in country_data.iterrows():
                row_start = row['date_start']
                row_end = row['date_stop']
                
                if current_start is None:
                    current_start = row_start
                    current_end = row_end
                else:
                    gap_days = (row_start - current_end).days
                    
                    if gap_days <= 56:  # Continue current period
                        current_end = max(current_end, row_end)
                    else:  # Start new period
                        periods.append((current_start, current_end))
                        current_start = row_start
                        current_end = row_end
            
            # Add the final period
            if current_start is not None:
                periods.append((current_start, current_end))
            
            # Calculate total coverage
            total_days_covered = sum((end - start).days + 1 for start, end in periods)
            total_possible_days = (country_end - country_start).days + 1
            coverage_percentage = (total_days_covered / total_possible_days) * 100
            
            # Format for agent consumption
            intervals_list = [f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}" 
                            for start, end in periods]
            
            # Identify major gaps (>3 months)
            gaps = []
            if len(periods) > 1:
                for i in range(len(periods) - 1):
                    gap_start = periods[i][1] + timedelta(days=1)
                    gap_end = periods[i+1][0] - timedelta(days=1)
                    gap_days = (gap_end - gap_start).days + 1
                    
                    if gap_days > 90:  # Gaps > 3 months
                        gaps.append(f"{gap_start.strftime('%Y-%m-%d')} to {gap_end.strftime('%Y-%m-%d')}")
                        
                        # Add to gap results
                        gap_results.append({
                            'country': country_name,
                            'iso_code': country_code,
                            'gap_start': gap_start.strftime('%Y-%m-%d'),
                            'gap_end': gap_end.strftime('%Y-%m-%d'),
                            'gap_days': gap_days,
                            'gap_years': round(gap_days / 365.25, 1)
                        })
            
            results.append({
                'country': country_name,
                'iso_code': country_code,
                'first_data': country_start.strftime('%Y-%m-%d'),
                'last_data': country_end.strftime('%Y-%m-%d'),
                'total_span_years': round((country_end - country_start).days / 365.25, 1),
                'coverage_percentage': round(coverage_percentage, 1),
                'data_periods': len(periods),
                'major_gaps': len([g for g in gaps]),
                'covered_intervals': "; ".join(intervals_list),
                'major_gap_periods': "; ".join(gaps) if gaps else "None",
                'priority_search_periods': "; ".join(gaps) if gaps else f"Pre-{country_start.strftime('%Y')} and Post-{country_end.strftime('%Y')} data"
            })
            
            print(f"{country_code} ({country_name}): {coverage_percentage:.1f}% coverage, {len(periods)} periods, {len(gaps)} major gaps")
        
        # Create summary DataFrame
        summary_df = pd.DataFrame(results)
        summary_df = summary_df.sort_values('coverage_percentage')
        
        # Create gaps DataFrame
        gaps_df = pd.DataFrame(gap_results)
        
        # Create reference directory if it doesn't exist
        os.makedirs('./reference', exist_ok=True)
        
        # Save files
        summary_df.to_csv('./reference/observed_time_periods.csv', index=False)
        print(f"\nAgent reference saved to: ./reference/observed_time_periods.csv")
        
        if len(gaps_df) > 0:
            gaps_df = gaps_df.sort_values(['gap_days'], ascending=False)
            gaps_df.to_csv('./reference/priority_data_gaps.csv', index=False)
            print(f"Priority gaps saved to: ./reference/priority_data_gaps.csv")
        
        # Create country-specific quick lookup
        quick_lookup = []
        for _, row in summary_df.iterrows():
            # Parse covered intervals to get years covered
            intervals = row['covered_intervals'].split('; ')
            years_covered = set()
            
            for interval in intervals:
                start_str, end_str = interval.split(' to ')
                start_year = int(start_str[:4])
                end_year = int(end_str[:4])
                years_covered.update(range(start_year, end_year + 1))
            
            # Determine likely missing years (focusing on recent decades)
            all_years = set(range(2000, 2026))  # Focus on 2000-2025
            missing_recent = sorted(all_years - years_covered)
            
            quick_lookup.append({
                'iso_code': row['iso_code'],
                'country': row['country'], 
                'coverage_pct': row['coverage_percentage'],
                'data_span': f"{row['first_data'][:4]}-{row['last_data'][:4]}",
                'search_priority': "HIGH" if row['coverage_percentage'] < 70 else "MEDIUM" if row['coverage_percentage'] < 90 else "LOW",
                'missing_recent_years': ", ".join(map(str, missing_recent[:10])) if missing_recent else "None",  # Show first 10
                'priority_periods': row['priority_search_periods']
            })
        
        quick_df = pd.DataFrame(quick_lookup)
        quick_df = quick_df.sort_values(['search_priority', 'coverage_pct'])
        quick_df.to_csv('./reference/agent_quick_reference.csv', index=False)
        print(f"Quick lookup saved to: ./reference/agent_quick_reference.csv")
        
        # Print summary for agents
        print(f"\n=== AGENT SUMMARY ===")
        print(f"Countries analyzed: {len(summary_df)}")
        print(f"High priority countries (<70% coverage): {len(quick_df[quick_df['search_priority'] == 'HIGH'])}")
        print(f"Medium priority countries (70-90% coverage): {len(quick_df[quick_df['search_priority'] == 'MEDIUM'])}")
        print(f"Major data gaps identified: {len(gaps_df) if len(gaps_df) > 0 else 0}")
        
        print(f"\nTOP 5 PRIORITY COUNTRIES FOR DATA COLLECTION:")
        for _, row in quick_df.head().iterrows():
            print(f"  {row['iso_code']} ({row['country']}): {row['coverage_pct']}% coverage - Focus: {row['missing_recent_years'][:50]}...")
            
    except Exception as e:
        print(f"Error processing data: {e}")
        return False
    
    return True

def main():
    """Main function to run the analysis."""
    
    # File paths
    input_file = "../MOSAIC-data/processed/cholera/weekly/cholera_surveillance_weekly_combined.csv"
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)
    
    # Run analysis
    success = create_agent_friendly_reference(input_file)
    
    if success:
        print(f"\nAgent reference files created successfully!")
        print(f"\nFiles created in ./reference/:")
        print(f"  - observed_time_periods.csv: Comprehensive coverage summary")
        print(f"  - agent_quick_reference.csv: Quick lookup with search priorities") 
        print(f"  - priority_data_gaps.csv: Major gaps requiring attention")
    else:
        print(f"\nAnalysis failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()