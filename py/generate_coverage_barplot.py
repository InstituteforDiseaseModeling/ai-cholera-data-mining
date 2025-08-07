#!/usr/bin/env python3
"""
Generate Stacked Horizontal Bar Plot of Cholera Data Coverage by Source

This script creates a horizontal bar plot showing the percentage of months with cholera
observations from 1970 to present, broken down by data source (JHU, WHO, AI).
The AI contribution shows only the additional coverage beyond the JHU+WHO baseline.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
import json
import warnings
warnings.filterwarnings('ignore')

# Dashboard color scheme matching the website
COLORS = {
    'JHU': '#1976d2',  # Blue for JHU historical data
    'WHO': '#d32f2f',  # Red for WHO dashboard data  
    'AI': '#388e3c'    # Green for AI-enhanced data
}

def load_country_names():
    """Load country names from mapping file"""
    mapping_file = Path('reference/country_mapping.json')
    if mapping_file.exists():
        with open(mapping_file, 'r') as f:
            mapping = json.load(f)
        return {item['iso_code']: item['country_name'] for item in mapping.values() 
                if isinstance(item, dict) and 'iso_code' in item}
    return {}

def load_cholera_data(iso_code):
    """Load all cholera data files for a country"""
    data_dir = Path(f'data/{iso_code}')
    
    all_data = []
    sources = ['jhu', 'who', 'ai']
    
    for source in sources:
        file_path = data_dir / f'cholera_data_{source}.csv'
        if file_path.exists():
            try:
                df = pd.read_csv(file_path)
                if not df.empty and 'TL' in df.columns:
                    df['source'] = source.upper()
                    df['TL'] = pd.to_datetime(df['TL'], errors='coerce')
                    df['TR'] = pd.to_datetime(df['TR'], errors='coerce')
                    # Filter to valid dates
                    df = df[df['TL'].notna()]
                    all_data.append(df)
            except Exception as e:
                print(f"  Warning: Could not load {file_path}: {e}")
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()

def calculate_monthly_coverage(df, start_date='1970-01-01', end_date=None):
    """Calculate percentage of months with observations by source
    
    A month is considered 'observed' by a source if the combined coverage 
    from all observations of that source covers ≥50% of the month's days.
    """
    if df.empty:
        return {'JHU': 0, 'WHO': 0, 'AI_additional': 0, 'Total': 0}
    
    # Set date range
    start = pd.to_datetime(start_date)
    if end_date is None:
        end = pd.to_datetime(datetime.now())
    else:
        end = pd.to_datetime(end_date)
    
    # Create month range
    months = pd.date_range(start=start, end=end, freq='MS')
    total_months = len(months)
    
    # Track which days are covered by each source
    # Structure: {source: {month: set of covered days}}
    days_covered_by_source = {
        'JHU': {},
        'WHO': {},
        'AI': {}
    }
    
    # Process observations more efficiently by grouping by source first
    for source in ['JHU', 'WHO', 'AI']:
        source_df = df[df['source'] == source]
        if source_df.empty:
            continue
            
        # For each month in our analysis period, check coverage
        for month_start in months:
            month_end = (month_start + pd.DateOffset(months=1)) - pd.DateOffset(days=1)
            
            # Find all observations that overlap with this month
            mask = (source_df['TL'] <= month_end) & (source_df['TR'] >= month_start)
            month_obs = source_df[mask]
            
            if month_obs.empty:
                continue
            
            # Calculate which days are covered in this month
            covered_days = set()
            for _, row in month_obs.iterrows():
                # Calculate the overlap period
                overlap_start = max(row['TL'], month_start)
                overlap_end = min(row['TR'], month_end)
                
                # Add all days in the overlap to covered_days
                for day_num in range(overlap_start.day, min(overlap_end.day + 1, month_end.day + 1)):
                    covered_days.add(day_num)
            
            # Store the covered days for this source and month
            if month_start not in days_covered_by_source[source]:
                days_covered_by_source[source][month_start] = set()
            days_covered_by_source[source][month_start].update(covered_days)
    
    # Now determine which months meet the ≥50% threshold for each source
    months_with_data = {
        'JHU': set(),
        'WHO': set(),
        'AI': set()
    }
    
    for source in ['JHU', 'WHO', 'AI']:
        for month_start, covered_days in days_covered_by_source[source].items():
            # Get total days in this month
            month_end = (month_start + pd.DateOffset(months=1)) - pd.DateOffset(days=1)
            total_days_in_month = month_end.day
            
            # Check if ≥50% of days are covered
            if len(covered_days) >= total_days_in_month / 2:
                months_with_data[source].add(month_start)
    
    # Calculate baseline coverage (JHU + WHO)
    baseline_months = months_with_data['JHU'] | months_with_data['WHO']
    
    # Calculate additional AI coverage (months covered by AI but not by baseline)
    ai_additional_months = months_with_data['AI'] - baseline_months
    
    # Calculate percentages
    coverage = {
        'JHU': len(months_with_data['JHU']) / total_months * 100 if total_months > 0 else 0,
        'WHO': len(months_with_data['WHO'] - months_with_data['JHU']) / total_months * 100 if total_months > 0 else 0,  # WHO not in JHU
        'AI_additional': len(ai_additional_months) / total_months * 100 if total_months > 0 else 0,  # AI beyond baseline
        'Total': len(months_with_data['JHU'] | months_with_data['WHO'] | months_with_data['AI']) / total_months * 100 if total_months > 0 else 0
    }
    
    return coverage

def get_mosaic_countries():
    """Get list of MOSAIC framework countries"""
    return [
        'AGO', 'BDI', 'BEN', 'BFA', 'BWA', 'CAF', 'CIV', 'CMR', 'COD', 'COG',
        'ERI', 'ETH', 'GAB', 'GHA', 'GIN', 'GMB', 'GNB', 'GNQ', 'KEN', 'LBR',
        'MLI', 'MOZ', 'MRT', 'MWI', 'NAM', 'NER', 'NGA', 'RWA', 'SEN', 'SLE',
        'SOM', 'SSD', 'SWZ', 'TCD', 'TGO', 'TZA', 'UGA', 'ZAF', 'ZMB', 'ZWE'
    ]

def create_coverage_barplot():
    """Create stacked horizontal bar plot of coverage by country"""
    
    print("=" * 80)
    print("CHOLERA DATA COVERAGE ANALYSIS - STACKED BAR PLOT")
    print("=" * 80)
    print("Calculating monthly coverage from 1970 to present by data source...\n")
    
    # Get country names
    country_names = load_country_names()
    
    # Collect coverage data for all countries
    countries = get_mosaic_countries()
    coverage_data = []
    
    for i, iso in enumerate(countries, 1):
        print(f"Processing {iso} ({i}/{len(countries)})...")
        df = load_cholera_data(iso)
        if not df.empty:
            print(f"  Found {len(df)} observations")
        coverage = calculate_monthly_coverage(df)
        
        country_name = country_names.get(iso, iso)
        coverage_data.append({
            'Country': f"{country_name} ({iso})",
            'ISO': iso,
            'JHU': coverage['JHU'],
            'WHO': coverage['WHO'],
            'AI': coverage['AI_additional'],
            'Total': coverage['Total']
        })
    
    # Create DataFrame and sort by total coverage
    coverage_df = pd.DataFrame(coverage_data)
    coverage_df = coverage_df.sort_values('Total', ascending=True)
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(12, 14))
    
    # Plot stacked horizontal bars
    y_pos = np.arange(len(coverage_df))
    
    # JHU baseline
    p1 = ax.barh(y_pos, coverage_df['JHU'], 
                 color=COLORS['JHU'], label='JHU Historical Database')
    
    # WHO additional (not overlapping with JHU)
    p2 = ax.barh(y_pos, coverage_df['WHO'], 
                 left=coverage_df['JHU'],
                 color=COLORS['WHO'], label='WHO Dashboard')
    
    # AI additional (beyond baseline)
    p3 = ax.barh(y_pos, coverage_df['AI'], 
                 left=coverage_df['JHU'] + coverage_df['WHO'],
                 color=COLORS['AI'], label='AI Enhancement')
    
    # Customize the plot
    ax.set_yticks(y_pos)
    ax.set_yticklabels(coverage_df['Country'], fontsize=9)
    ax.set_xlabel('Percentage of Months with Observations (1970-Present)', fontsize=11, fontweight='bold')
    ax.set_title('Cholera Surveillance Data Coverage by Source\nMOSAIC Framework Countries', 
                 fontsize=14, fontweight='bold', pad=20)
    
    # Set x-axis limits and ticks
    ax.set_xlim(0, 105)
    ax.set_xticks(range(0, 110, 10))
    ax.set_xticklabels([f'{x}%' for x in range(0, 110, 10)])
    
    # Add grid
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    # Add reference line at 100%
    ax.axvline(x=100, color='gray', linestyle='--', alpha=0.5, linewidth=1)
    
    # Add legend
    ax.legend(loc='lower right', frameon=True, fancybox=True, shadow=True)
    
    # Add value labels on bars (only for values > 5%)
    for i, (idx, row) in enumerate(coverage_df.iterrows()):
        # JHU label
        if row['JHU'] > 5:
            ax.text(row['JHU']/2, i, f"{row['JHU']:.1f}%", 
                   ha='center', va='center', color='white', fontsize=7, fontweight='bold')
        
        # WHO label
        if row['WHO'] > 5:
            ax.text(row['JHU'] + row['WHO']/2, i, f"{row['WHO']:.1f}%", 
                   ha='center', va='center', color='white', fontsize=7, fontweight='bold')
        
        # AI label
        if row['AI'] > 5:
            ax.text(row['JHU'] + row['WHO'] + row['AI']/2, i, f"{row['AI']:.1f}%", 
                   ha='center', va='center', color='white', fontsize=7, fontweight='bold')
        
        # Total label at the end
        if row['Total'] > 0:
            ax.text(row['Total'] + 1, i, f"{row['Total']:.1f}%", 
                   ha='left', va='center', color='black', fontsize=7)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save the plot
    output_dir = Path('figures')
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / 'cholera_coverage_barplot.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n✅ Bar plot saved to: {output_file}")
    
    # Also save to dashboard directory
    dashboard_dir = Path('dashboard/plots')
    dashboard_dir.mkdir(exist_ok=True)
    dashboard_file = dashboard_dir / 'cholera_coverage_barplot.png'
    plt.savefig(dashboard_file, dpi=150, bbox_inches='tight')
    print(f"✅ Bar plot saved to: {dashboard_file}")
    
    # Print summary statistics
    print("\n" + "=" * 80)
    print("COVERAGE SUMMARY STATISTICS")
    print("=" * 80)
    
    print(f"\nTotal countries analyzed: {len(coverage_df)}")
    print(f"Countries with >50% coverage: {len(coverage_df[coverage_df['Total'] > 50])}")
    print(f"Countries with >75% coverage: {len(coverage_df[coverage_df['Total'] > 75])}")
    print(f"Countries with 100% coverage: {len(coverage_df[coverage_df['Total'] >= 100])}")
    
    print("\nTop 5 countries by coverage:")
    for i, row in coverage_df.tail(5).iterrows():
        print(f"  {row['Country']}: {row['Total']:.1f}% (JHU: {row['JHU']:.1f}%, WHO: {row['WHO']:.1f}%, AI: {row['AI']:.1f}%)")
    
    print("\nBottom 5 countries by coverage:")
    for i, row in coverage_df.head(5).iterrows():
        print(f"  {row['Country']}: {row['Total']:.1f}% (JHU: {row['JHU']:.1f}%, WHO: {row['WHO']:.1f}%, AI: {row['AI']:.1f}%)")
    
    print("\nAverage coverage by source:")
    print(f"  JHU: {coverage_df['JHU'].mean():.1f}%")
    print(f"  WHO: {coverage_df['WHO'].mean():.1f}%")
    print(f"  AI Additional: {coverage_df['AI'].mean():.1f}%")
    print(f"  Total: {coverage_df['Total'].mean():.1f}%")
    
    # Don't show interactively to avoid hanging
    # plt.show()
    plt.close()
    
    return coverage_df

if __name__ == "__main__":
    coverage_df = create_coverage_barplot()