#!/usr/bin/env python3
"""
Script to analyze cholera surveillance data and determine observed time periods by country.

This script loads the cholera surveillance CSV data and identifies date intervals 
where we have observed surveillance data (non-NA values) for each country.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

def load_and_analyze_surveillance_data(input_file, output_file):
    """
    Load cholera surveillance data and analyze observed time periods by country.
    
    Args:
        input_file (str): Path to input CSV file
        output_file (str): Path to output CSV file
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
        # Data is considered "observed" if any of cases, deaths, or source are not NA
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
            
        # Group by country and find continuous periods
        results = []
        
        for country_code in sorted(observed_data['iso_code'].unique()):
            country_data = observed_data[observed_data['iso_code'] == country_code].copy()
            country_name = country_data['country'].iloc[0]
            
            # Sort by date
            country_data = country_data.sort_values('date_start')
            
            # Find continuous periods (allowing for small gaps)
            periods = []
            current_start = None
            current_end = None
            
            for _, row in country_data.iterrows():
                row_start = row['date_start']
                row_end = row['date_stop']
                
                if current_start is None:
                    # Start first period
                    current_start = row_start
                    current_end = row_end
                else:
                    # Check if this row continues the current period
                    # Allow for gaps up to 8 weeks (56 days) - typical surveillance reporting gaps
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
            
            # Format intervals as a single string for this country
            interval_strings = []
            for start_date, end_date in periods:
                interval_strings.append(f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
            intervals = "; ".join(interval_strings)
            
            results.append({
                'country': country_name,
                'iso_code': country_code,
                'intervals': intervals
            })
            
            print(f"{country_code} ({country_name}): {intervals}")
        
        # Convert to DataFrame and save
        results_df = pd.DataFrame(results)
        
        if len(results_df) > 0:
            # Sort by country
            results_df = results_df.sort_values('country')
            
            # Save results
            results_df.to_csv(output_file, index=False)
            print(f"\nResults saved to: {output_file}")
            
            # Print summary statistics
            print(f"\nSummary:")
            print(f"- Countries with observed data: {len(results_df)}")
            
            print(f"\nCountries with observed surveillance data:")
            for _, row in results_df.iterrows():
                print(f"  {row['iso_code']} ({row['country']}): {row['intervals']}")
        
        else:
            print("No observation periods found!")
            
    except Exception as e:
        print(f"Error processing data: {e}")
        return False
    
    return True

def main():
    """Main function to run the analysis."""
    
    # File paths
    input_file = "../MOSAIC-data/processed/cholera/weekly/cholera_surveillance_weekly_combined.csv"
    output_file = "./observed_time_periods.csv"
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)
    
    # Run analysis
    success = load_and_analyze_surveillance_data(input_file, output_file)
    
    if success:
        print(f"\nAnalysis completed successfully!")
    else:
        print(f"\nAnalysis failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()