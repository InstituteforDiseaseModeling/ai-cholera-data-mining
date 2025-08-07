#!/usr/bin/env python3
"""
Generate Stacked Horizontal Bar Plot of Cholera Data Coverage by Source

This script creates a horizontal bar plot showing the percentage of months with cholera
observations from 1970 to present, broken down by data source (JHU, WHO, AI).
The AI contribution shows only the additional coverage beyond the JHU+WHO baseline.

Uses vectorized operations for fast processing of large datasets (~12 seconds).
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
    """Load country names from mapping file or use defaults"""
    # Default country names for all MOSAIC countries
    default_names = {
        'AGO': 'Angola', 'BDI': 'Burundi', 'BEN': 'Benin', 'BFA': 'Burkina Faso',
        'BWA': 'Botswana', 'CAF': 'Central African Republic', 'CIV': "Côte d'Ivoire",
        'CMR': 'Cameroon', 'COD': 'Democratic Republic of Congo', 'COG': 'Congo',
        'ERI': 'Eritrea', 'ETH': 'Ethiopia', 'GAB': 'Gabon', 'GHA': 'Ghana',
        'GIN': 'Guinea', 'GMB': 'Gambia', 'GNB': 'Guinea-Bissau', 'GNQ': 'Equatorial Guinea',
        'KEN': 'Kenya', 'LBR': 'Liberia', 'MLI': 'Mali', 'MOZ': 'Mozambique',
        'MRT': 'Mauritania', 'MWI': 'Malawi', 'NAM': 'Namibia', 'NER': 'Niger',
        'NGA': 'Nigeria', 'RWA': 'Rwanda', 'SEN': 'Senegal', 'SLE': 'Sierra Leone',
        'SOM': 'Somalia', 'SSD': 'South Sudan', 'SWZ': 'Eswatini', 'TCD': 'Chad',
        'TGO': 'Togo', 'TZA': 'Tanzania', 'UGA': 'Uganda', 'ZAF': 'South Africa',
        'ZMB': 'Zambia', 'ZWE': 'Zimbabwe'
    }
    
    mapping_file = Path('reference/country_mapping.json')
    if mapping_file.exists():
        try:
            with open(mapping_file, 'r') as f:
                mapping = json.load(f)
            loaded_names = {item['iso_code']: item['country_name'] for item in mapping.values() 
                          if isinstance(item, dict) and 'iso_code' in item}
            # Update defaults with loaded names
            default_names.update(loaded_names)
        except Exception:
            pass  # Use defaults if loading fails
    
    return default_names

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
                    df = df[df['TL'].notna() & df['TR'].notna()]
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
    end = pd.to_datetime(datetime.now()) if end_date is None else pd.to_datetime(end_date)
    
    # Create month range
    months = pd.date_range(start=start, end=end, freq='MS')
    total_months = len(months)
    
    months_with_data = {
        'JHU': set(),
        'WHO': set(),
        'AI': set()
    }
    
    # Process each source
    for source in ['JHU', 'WHO', 'AI']:
        source_df = df[df['source'] == source].copy()
        if source_df.empty:
            continue
        
        # For each month, use vectorized operations to check coverage
        for month_start in months:
            month_end = month_start + pd.DateOffset(months=1) - pd.DateOffset(days=1)
            days_in_month = month_end.day
            
            # Vectorized check for overlapping observations
            overlaps = (source_df['TL'] <= month_end) & (source_df['TR'] >= month_start)
            
            if not overlaps.any():
                continue
            
            # Get overlapping observations
            month_obs = source_df[overlaps]
            
            # Calculate covered days more efficiently
            # Clip observations to month boundaries
            clipped_starts = np.maximum(month_obs['TL'].values, np.datetime64(month_start))
            clipped_ends = np.minimum(month_obs['TR'].values, np.datetime64(month_end))
            
            # Create a boolean array for each day of the month
            covered = np.zeros(days_in_month, dtype=bool)
            
            for start, end in zip(clipped_starts, clipped_ends):
                # Convert numpy datetime64 to pandas timestamp for calculation
                start_ts = pd.Timestamp(start)
                end_ts = pd.Timestamp(end)
                
                # Calculate which days are covered (1-indexed)
                start_day = max(1, (start_ts - month_start).days + 1)
                end_day = min(days_in_month, (end_ts - month_start).days + 1)
                covered[start_day-1:end_day] = True
            
            # Check if ≥50% of days are covered
            if covered.sum() >= days_in_month / 2:
                months_with_data[source].add(month_start)
    
    # Calculate baseline coverage (JHU + WHO)
    baseline_months = months_with_data['JHU'] | months_with_data['WHO']
    
    # Calculate additional AI coverage (months covered by AI but not by baseline)
    ai_additional_months = months_with_data['AI'] - baseline_months
    
    # Calculate percentages
    coverage = {
        'JHU': len(months_with_data['JHU']) / total_months * 100 if total_months > 0 else 0,
        'WHO': len(months_with_data['WHO'] - months_with_data['JHU']) / total_months * 100 if total_months > 0 else 0,
        'AI_additional': len(ai_additional_months) / total_months * 100 if total_months > 0 else 0,
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
    
    import time
    start_time = time.time()
    
    for i, iso in enumerate(countries, 1):
        country_start = time.time()
        print(f"Processing {iso} ({i}/{len(countries)})...", end='')
        
        df = load_cholera_data(iso)
        if not df.empty:
            print(f" {len(df)} observations...", end='')
        
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
        
        print(f" done ({time.time() - country_start:.1f}s)")
    
    print(f"\nTotal processing time: {time.time() - start_time:.1f} seconds")
    
    # Create DataFrame and sort by total coverage
    coverage_df = pd.DataFrame(coverage_data)
    coverage_df = coverage_df.sort_values('Total', ascending=True)
    
    # Create the plot with much larger size for better readability
    fig, ax = plt.subplots(figsize=(18, 20))
    
    # Plot stacked horizontal bars
    y_pos = np.arange(len(coverage_df))
    
    # JHU baseline
    p1 = ax.barh(y_pos, coverage_df['JHU'], 
                 color=COLORS['JHU'], label='JHU Historical Database', height=0.8)
    
    # WHO additional (not overlapping with JHU)
    p2 = ax.barh(y_pos, coverage_df['WHO'], 
                 left=coverage_df['JHU'],
                 color=COLORS['WHO'], label='WHO Dashboard', height=0.8)
    
    # AI additional (beyond baseline)
    p3 = ax.barh(y_pos, coverage_df['AI'], 
                 left=coverage_df['JHU'] + coverage_df['WHO'],
                 color=COLORS['AI'], label='AI Enhancement', height=0.8)
    
    # Customize the plot with much larger fonts
    ax.set_yticks(y_pos)
    ax.set_yticklabels(coverage_df['Country'], fontsize=14)  # Increased from 11
    ax.set_xlabel('Percentage of Months with Observations (1970-Present)', 
                  fontsize=18, fontweight='bold', labelpad=20)  # Increased from 14
    ax.set_title('Cholera Surveillance Data Coverage by Source\nMOSAIC Framework Countries', 
                 fontsize=22, fontweight='bold', pad=25)  # Increased from 16
    
    # Set x-axis limits and ticks with larger font
    ax.set_xlim(0, 105)
    ax.set_xticks(range(0, 110, 10))
    ax.set_xticklabels([f'{x}%' for x in range(0, 110, 10)], fontsize=14)  # Increased from 12
    
    # Add grid
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    # Add reference line at 100%
    ax.axvline(x=100, color='gray', linestyle='--', alpha=0.5, linewidth=1)
    
    # Add legend horizontally below the plot, without border
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.04), 
              ncol=3, frameon=False, fontsize=16)  # Much larger font
    
    # Add value labels on bars with much larger font
    for i, (idx, row) in enumerate(coverage_df.iterrows()):
        # JHU label
        if row['JHU'] > 5:
            ax.text(row['JHU']/2, i, f"{row['JHU']:.1f}%", 
                   ha='center', va='center', color='white', fontsize=11, fontweight='bold')
        
        # WHO label - show even for smaller values if there's some space
        if row['WHO'] > 0.3:  # Lowered threshold to show more WHO labels
            # Only show if text would fit (roughly 3% width needed for label)
            if row['WHO'] > 3:
                ax.text(row['JHU'] + row['WHO']/2, i, f"{row['WHO']:.1f}%", 
                       ha='center', va='center', color='white', fontsize=11, fontweight='bold')
            else:
                # For small WHO bars, place text slightly offset if there's room
                ax.text(row['JHU'] + row['WHO']/2, i, f"{row['WHO']:.1f}", 
                       ha='center', va='center', color='white', fontsize=9)
        
        # AI label
        if row['AI'] > 5:
            ax.text(row['JHU'] + row['WHO'] + row['AI']/2, i, f"{row['AI']:.1f}%", 
                   ha='center', va='center', color='white', fontsize=11, fontweight='bold')
        
        # Total label at the end with larger font
        if row['Total'] > 0:
            ax.text(row['Total'] + 1, i, f"{row['Total']:.1f}%", 
                   ha='left', va='center', color='black', fontsize=12, fontweight='bold')
    
    # Adjust layout
    plt.tight_layout()
    
    # Save the plot with very high resolution
    output_dir = Path('figures')
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / 'cholera_coverage_barplot.png'
    plt.savefig(output_file, dpi=600, bbox_inches='tight')
    print(f"\n✅ Bar plot saved to: {output_file}")
    
    # Also save to dashboard directory
    dashboard_dir = Path('dashboard/plots')
    dashboard_dir.mkdir(exist_ok=True)
    dashboard_file = dashboard_dir / 'cholera_coverage_barplot.png'
    plt.savefig(dashboard_file, dpi=600, bbox_inches='tight')
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
    
    plt.close()
    
    return coverage_df

if __name__ == "__main__":
    coverage_df = create_coverage_barplot()