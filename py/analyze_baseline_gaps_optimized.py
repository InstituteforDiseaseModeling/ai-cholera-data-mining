#!/usr/bin/env python3
"""
Optimized Baseline Surveillance Gap Analysis

This script analyzes baseline cholera surveillance data (JHU + WHO only) to identify
temporal gaps and generate reference files for AI agents.

Outputs three files:
1. baseline_surveillance_gaps_annual.csv - Years with ≥6 months missing
2. baseline_surveillance_gaps_detailed.csv - Consolidated gap date ranges
3. baseline_surveillance_gaps_coverage.csv - Country coverage summary

Uses >50% days coverage rule to determine if a month has data.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import calendar
import os
import json
from pathlib import Path
import logging
from collections import defaultdict

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DATA_PATH = "./data"
REFERENCE_PATH = "./reference"
START_DATE = datetime(1970, 1, 1)
END_DATE = datetime.now().replace(day=1)  # First day of current month

def load_country_mapping():
    """Load MOSAIC framework countries from mapping file."""
    try:
        with open(f"{REFERENCE_PATH}/country_mapping.json", 'r') as f:
            data = json.load(f)
        
        # Extract only MOSAIC framework countries
        countries = data.get('countries', {})
        mosaic_countries = {k: v for k, v in countries.items() if v.get('mosaic_framework', False)}
        logger.info(f"Loaded {len(mosaic_countries)} MOSAIC framework countries")
        return mosaic_countries
    except FileNotFoundError:
        logger.error(f"country_mapping.json not found in {REFERENCE_PATH}")
        return {}

def analyze_country_gaps_optimized(iso_code, country_info):
    """
    Optimized analysis for a single country using vectorized operations.
    """
    country_name = country_info['name']
    logger.info(f"Analyzing {country_name} ({iso_code})")
    
    # Load baseline data files
    all_observations = []
    
    for source, filename in [('JHU', 'cholera_data_jhu.csv'), ('WHO', 'cholera_data_who.csv')]:
        filepath = f"{DATA_PATH}/{iso_code}/{filename}"
        if os.path.exists(filepath):
            try:
                df = pd.read_csv(filepath)
                if len(df) > 0:
                    df['TL'] = pd.to_datetime(df['TL'], errors='coerce')
                    df['TR'] = pd.to_datetime(df['TR'], errors='coerce')
                    df = df.dropna(subset=['TL', 'TR'])
                    all_observations.append(df)
                    logger.debug(f"  Loaded {len(df)} {source} observations")
            except Exception as e:
                logger.warning(f"  Error reading {source} file: {e}")
    
    # If no data, return empty coverage
    if not all_observations:
        return create_empty_result(country_name, iso_code)
    
    # Combine all observations
    obs_df = pd.concat(all_observations, ignore_index=True)
    
    # Create month coverage using vectorized approach
    month_coverage = defaultdict(int)
    
    for _, obs in obs_df.iterrows():
        # Generate all months covered by this observation
        start_month = obs['TL'].to_period('M')
        end_month = obs['TR'].to_period('M')
        
        current = start_month
        while current <= end_month:
            year = current.year
            month = current.month
            
            # Calculate days covered in this month
            month_start = current.to_timestamp()
            month_end = current.to_timestamp(how='end')
            
            # Find overlap
            overlap_start = max(obs['TL'], month_start)
            overlap_end = min(obs['TR'], month_end)
            
            if overlap_end >= overlap_start:
                days_covered = (overlap_end - overlap_start).days + 1
                month_coverage[(year, month)] = max(month_coverage[(year, month)], days_covered)
            
            current += 1
    
    # Analyze all months
    month_results = []
    current_date = START_DATE
    
    while current_date <= END_DATE:
        year = current_date.year
        month = current_date.month
        days_in_month = calendar.monthrange(year, month)[1]
        
        days_covered = month_coverage.get((year, month), 0)
        is_covered = days_covered > (days_in_month / 2)
        
        month_results.append({
            'year': year,
            'month': month,
            'is_covered': is_covered,
            'days_covered': days_covered,
            'total_days': days_in_month
        })
        
        # Move to next month
        if month == 12:
            current_date = current_date.replace(year=year + 1, month=1)
        else:
            current_date = current_date.replace(month=month + 1)
    
    return {
        'country': country_name,
        'iso_code': iso_code,
        'month_results': month_results,
        'total_observations': len(obs_df)
    }

def create_empty_result(country_name, iso_code):
    """Create result for country with no data."""
    month_results = []
    current_date = START_DATE
    
    while current_date <= END_DATE:
        month_results.append({
            'year': current_date.year,
            'month': current_date.month,
            'is_covered': False,
            'days_covered': 0,
            'total_days': calendar.monthrange(current_date.year, current_date.month)[1]
        })
        
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    return {
        'country': country_name,
        'iso_code': iso_code,
        'month_results': month_results,
        'total_observations': 0
    }

def consolidate_gap_ranges(month_results):
    """Convert monthly gap data into consolidated date ranges."""
    gap_ranges = []
    current_gap_start = None
    
    for i, month_data in enumerate(month_results):
        if not month_data['is_covered']:  # This is a gap month
            if current_gap_start is None:
                # Start new gap
                current_gap_start = datetime(month_data['year'], month_data['month'], 1)
        else:  # This month has coverage
            if current_gap_start is not None:
                # End current gap
                prev_month = month_results[i-1]
                gap_end_date = datetime(prev_month['year'], prev_month['month'], 
                                      calendar.monthrange(prev_month['year'], prev_month['month'])[1])
                
                gap_days = (gap_end_date - current_gap_start).days + 1
                gap_months = round(gap_days / 30.44)  # Average days per month
                gap_years = round(gap_days / 365.25, 1)
                
                gap_ranges.append({
                    'gap_start': current_gap_start.strftime('%Y-%m-%d'),
                    'gap_end': gap_end_date.strftime('%Y-%m-%d'),
                    'days': gap_days,
                    'months': gap_months,
                    'years': gap_years
                })
                
                current_gap_start = None
    
    # Handle gap extending to end
    if current_gap_start is not None:
        last_month = month_results[-1]
        gap_end_date = datetime(last_month['year'], last_month['month'],
                              calendar.monthrange(last_month['year'], last_month['month'])[1])
        
        gap_days = (gap_end_date - current_gap_start).days + 1
        gap_months = round(gap_days / 30.44)
        gap_years = round(gap_days / 365.25, 1)
        
        gap_ranges.append({
            'gap_start': current_gap_start.strftime('%Y-%m-%d'),
            'gap_end': gap_end_date.strftime('%Y-%m-%d'),
            'days': gap_days,
            'months': gap_months,
            'years': gap_years
        })
    
    return gap_ranges

def get_year_summary(month_results):
    """Summarize gaps by year."""
    year_summary = {}
    
    for month_data in month_results:
        year = month_data['year']
        if year not in year_summary:
            year_summary[year] = {'total_months': 0, 'missing_months': 0}
        
        year_summary[year]['total_months'] += 1
        if not month_data['is_covered']:
            year_summary[year]['missing_months'] += 1
    
    return year_summary

def format_year_ranges(years):
    """Format a list of years into readable ranges."""
    if not years:
        return "None"
    
    years = sorted(years)
    ranges = []
    start = years[0]
    end = years[0]
    
    for year in years[1:]:
        if year == end + 1:
            end = year
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = year
            end = year
    
    # Add final range
    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")
    
    return ",".join(ranges)

def main():
    """Generate baseline surveillance gap analysis files."""
    
    logger.info("=" * 80)
    logger.info("BASELINE SURVEILLANCE GAP ANALYSIS (OPTIMIZED)")
    logger.info("=" * 80)
    logger.info(f"Analyzing baseline data from {START_DATE.strftime('%Y-%m')} to {END_DATE.strftime('%Y-%m')}")
    logger.info("Using >50% days coverage rule for month classification")
    logger.info("")
    
    # Ensure output directory exists
    os.makedirs(REFERENCE_PATH, exist_ok=True)
    
    # Load countries
    countries = load_country_mapping()
    if not countries:
        logger.error("No countries to process")
        return
    
    # Process each country
    all_results = []
    
    for iso_code, country_info in sorted(countries.items()):
        result = analyze_country_gaps_optimized(iso_code, country_info)
        all_results.append(result)
    
    # Generate output files
    logger.info("\nGenerating output files...")
    
    # File 1: Annual gaps (years with ≥6 months missing)
    annual_rows = []
    for result in all_results:
        year_summary = get_year_summary(result['month_results'])
        
        for year, data in year_summary.items():
            if data['missing_months'] >= 6:
                annual_rows.append({
                    'country': result['country'],
                    'iso_code': result['iso_code'],
                    'gap_year': year,
                    'months_missing': data['missing_months']
                })
    
    annual_df = pd.DataFrame(annual_rows)
    annual_df = annual_df.sort_values(['country', 'gap_year'])
    annual_file = f"{REFERENCE_PATH}/baseline_surveillance_gaps_annual.csv"
    annual_df.to_csv(annual_file, index=False)
    logger.info(f"  Created {annual_file} ({len(annual_df)} rows)")
    
    # File 2: Detailed gap ranges
    detailed_rows = []
    for result in all_results:
        gap_ranges = consolidate_gap_ranges(result['month_results'])
        
        for gap in gap_ranges:
            detailed_rows.append({
                'country': result['country'],
                'iso_code': result['iso_code'],
                'gap_start': gap['gap_start'],
                'gap_end': gap['gap_end'],
                'days': gap['days'],
                'months': gap['months'],
                'years': gap['years']
            })
    
    detailed_df = pd.DataFrame(detailed_rows)
    if len(detailed_df) > 0:
        detailed_df = detailed_df.sort_values(['country', 'gap_start'])
    detailed_file = f"{REFERENCE_PATH}/baseline_surveillance_gaps_detailed.csv"
    detailed_df.to_csv(detailed_file, index=False)
    logger.info(f"  Created {detailed_file} ({len(detailed_df)} rows)")
    
    # File 3: Coverage summary
    coverage_rows = []
    for result in all_results:
        month_data = result['month_results']
        total_months = len(month_data)
        covered_months = sum(1 for m in month_data if m['is_covered'])
        missing_months = total_months - covered_months
        percent_coverage = (covered_months / total_months * 100) if total_months > 0 else 0
        
        # Get years with data and missing years
        years_with_data = [m['year'] for m in month_data if m['is_covered']]
        years_with_data = sorted(set(years_with_data))
        
        all_years = set(range(START_DATE.year, END_DATE.year + 1))
        missing_years = sorted(all_years - set(years_with_data))
        
        coverage_rows.append({
            'country': result['country'],
            'iso_code': result['iso_code'],
            'total_months': total_months,
            'months_with_data': covered_months,
            'months_missing': missing_months,
            'percent_coverage': round(percent_coverage, 1),
            'data_years': format_year_ranges(years_with_data),
            'missing_years': format_year_ranges(missing_years)
        })
    
    coverage_df = pd.DataFrame(coverage_rows)
    coverage_df = coverage_df.sort_values('country')
    coverage_file = f"{REFERENCE_PATH}/baseline_surveillance_gaps_coverage.csv"
    coverage_df.to_csv(coverage_file, index=False)
    logger.info(f"  Created {coverage_file} ({len(coverage_df)} rows)")
    
    # Summary statistics
    logger.info("\nSummary Statistics:")
    logger.info(f"  Countries analyzed: {len(all_results)}")
    logger.info(f"  Total gap periods: {len(detailed_df)}")
    logger.info(f"  Countries with <50% coverage: {len(coverage_df[coverage_df['percent_coverage'] < 50])}")
    logger.info(f"  Countries with no baseline data: {len(coverage_df[coverage_df['percent_coverage'] == 0])}")
    
    logger.info("\nBaseline gap analysis complete!")

if __name__ == "__main__":
    main()