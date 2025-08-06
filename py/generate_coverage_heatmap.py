#!/usr/bin/env python3
"""
Coverage Heatmap Generator

Creates a visual heatmap showing temporal coverage by country and data source.
Countries on Y-axis, dates on X-axis, cells colored by source_database.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import seaborn as sns
import os
import json
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DATA_PATH = "./data"
REFERENCE_PATH = "./reference"
OUTPUT_PATH = "./dashboard/heatmaps"

def load_country_mapping():
    """Load country name to ISO code mapping."""
    try:
        with open(f"{REFERENCE_PATH}/country_mapping.json", 'r') as f:
            data = json.load(f)
        
        # Extract MOSAIC framework countries
        countries = data.get('countries', {})
        return {k: v for k, v in countries.items() if v.get('mosaic_framework', False)}
    except FileNotFoundError:
        logger.error(f"country_mapping.json not found in {REFERENCE_PATH}")
        return {}

def load_all_country_data():
    """Load cholera data from all countries with data."""
    
    country_mapping = load_country_mapping()
    all_data = []
    
    for country_iso, country_info in country_mapping.items():
        # Try separate files first, then unified file as fallback
        country_data_paths = [
            f"{DATA_PATH}/{country_iso}/cholera_data_jhu.csv",
            f"{DATA_PATH}/{country_iso}/cholera_data_who.csv", 
            f"{DATA_PATH}/{country_iso}/cholera_data_ai.csv",
            f"{DATA_PATH}/{country_iso}/cholera_data.csv"  # Fallback unified file
        ]
        
        country_data_combined = []
        for data_path in country_data_paths:
            if os.path.exists(data_path):
                try:
                    df = pd.read_csv(data_path)
                    if len(df) > 0:
                        df['country_iso'] = country_iso
                        df['country_name'] = country_info['name']
                        country_data_combined.append(df)
                        logger.info(f"Loaded {len(df)} observations from {os.path.basename(data_path)} for {country_iso}")
                except Exception as e:
                    logger.warning(f"Error reading {data_path}: {e}")
        
        # Combine all data sources for this country
        if country_data_combined:
            combined_df = pd.concat(country_data_combined, ignore_index=True)
            all_data.append(combined_df)
            logger.info(f"Combined {len(combined_df)} total observations for {country_iso}")
        else:
            logger.info(f"No data files found for {country_iso}")
    
    if not all_data:
        logger.error("No country data found!")
        return pd.DataFrame()
    
    # Combine all data
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Parse dates
    combined_df['TL'] = pd.to_datetime(combined_df['TL'])
    combined_df['TR'] = pd.to_datetime(combined_df['TR'])
    
    # Filter meaningful observations (including zero-case surveillance data)
    meaningful_data = combined_df[
        (combined_df['sCh'].notna() & (combined_df['sCh'] >= 0)) |
        (combined_df['deaths'].notna() & (combined_df['deaths'] >= 0)) |
        (combined_df['cCh'].notna() & (combined_df['cCh'] >= 0))
    ].copy()
    
    logger.info(f"Total observations: {len(combined_df)}")
    logger.info(f"Meaningful observations: {len(meaningful_data)}")
    
    return meaningful_data

def separate_national_subnational_data(data_df):
    """Separate data into national and sub-national based on Location field."""
    
    # National data: Location format is AFR::{ISO} (no additional subdivisions)
    national_data = data_df[data_df['Location'].str.match(r'^AFR::[A-Z]{3}$', na=False)].copy()
    
    # Sub-national data: Location format includes provinces/districts (AFR::{ISO}::{PROVINCE} or more levels)
    subnational_data = data_df[~data_df['Location'].str.match(r'^AFR::[A-Z]{3}$', na=False)].copy()
    
    logger.info(f"National observations: {len(national_data)}")
    logger.info(f"Sub-national observations: {len(subnational_data)}")
    
    return national_data, subnational_data

def create_coverage_heatmap(data_df, data_type="National", start_year=1970, end_year=2025, monthly=False):
    """Generate coverage heatmap by country and year or month."""
    
    if monthly:
        # Create month range for specified years
        import datetime
        months = []
        month_labels = []
        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                months.append(datetime.date(year, month, 1))
                if month == 1 or (year % 5 == 0 and month % 3 == 1):  # Show label every 3 months for 5-year intervals
                    month_labels.append(f"{year}-{month:02d}")
                else:
                    month_labels.append("")
        time_periods = months
        time_labels = month_labels
    else:
        # Create year range
        years = list(range(start_year, end_year + 1))
        time_periods = years
        time_labels = [str(y) if y % 5 == 0 else "" for y in years]
    
    # Get unique countries sorted alphabetically by country name
    country_counts = data_df.groupby(['country_iso', 'country_name']).size().reset_index(name='count')
    country_counts = country_counts.sort_values('country_name', ascending=True)  # Sort alphabetically by name
    countries = [(row['country_iso'], row['country_name']) for _, row in country_counts.iterrows()]
    
    # Create coverage matrix
    coverage_matrix = np.zeros((len(countries), len(time_periods)), dtype=int)
    source_matrix = np.full((len(countries), len(time_periods)), '', dtype=object)
    
    # Source database mapping to colors
    source_colors = {
        'JHU': 1,      # Blue
        'WHO': 2,      # Red  
        'AI': 3,       # Green
        'Mixed': 4     # Purple (multiple sources in same period)
    }
    
    for i, (country_iso, country_name) in enumerate(countries):
        country_data = data_df[data_df['country_iso'] == country_iso]
        
        for j, time_period in enumerate(time_periods):
            if monthly:
                # Check if data overlaps with this month
                month_start = pd.Timestamp(time_period)
                month_end = month_start + pd.DateOffset(months=1) - pd.Timedelta(days=1)
                
                period_data = country_data[
                    (country_data['TL'] <= month_end) & 
                    (country_data['TR'] >= month_start)
                ]
            else:
                # Original yearly logic
                period_data = country_data[
                    (country_data['TL'].dt.year <= time_period) & 
                    (country_data['TR'].dt.year >= time_period)
                ]
            
            if len(period_data) > 0:
                # Check sources for this period
                period_sources = period_data['source_database'].unique()
                period_sources = [s for s in period_sources if pd.notna(s)]
                
                if len(period_sources) == 1:
                    source = period_sources[0]
                    coverage_matrix[i, j] = source_colors.get(source, 1)
                    source_matrix[i, j] = source
                elif len(period_sources) > 1:
                    coverage_matrix[i, j] = source_colors['Mixed']
                    source_matrix[i, j] = 'Mixed'
                else:
                    coverage_matrix[i, j] = 1  # Default to JHU
                    source_matrix[i, j] = 'Unknown'
    
    return coverage_matrix, source_matrix, countries, time_periods, time_labels, source_colors

def plot_heatmap(coverage_matrix, source_matrix, countries, time_periods, time_labels, source_colors, data_type="National", monthly=False):
    """Create and save the coverage heatmap."""
    
    # Create figure with wider aspect ratio for better readability
    fig, ax = plt.subplots(figsize=(36, 18))  # Larger figure for better text readability
    
    # Create custom colormap with complementary color scheme
    colors = ['white', '#0167af', '#E74C3C', '#2ECC71', '#9B59B6']  # white, JHU blue, WHO red, AI green, mixed purple
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap(colors)
    
    # Plot heatmap
    im = ax.imshow(coverage_matrix, cmap=cmap, aspect='auto', vmin=0, vmax=4)
    
    # Set country labels (Y-axis) with larger font
    country_labels = [f"{iso} - {name}" for iso, name in countries]
    ax.set_yticks(range(len(countries)))
    ax.set_yticklabels(country_labels, fontsize=22)  # Increased text size for better readability
    
    # Set year labels (X-axis) - show every 5 years with larger font
    year_indices = [i for i, period in enumerate(time_periods) if period % 5 == 0]
    year_labels = [str(time_periods[i]) for i in year_indices]
    ax.set_xticks(year_indices)
    ax.set_xticklabels(year_labels, rotation=45, fontsize=22)  # Increased text size for better readability
    
    # Add minor ticks for all years
    ax.set_xticks(range(len(time_periods)), minor=True)
    
    # Remove axis titles as requested
    
    if data_type == "Sub-national":
        title = 'Cholera Surveillance Data Coverage - Sub-national Level'
    else:
        title = 'Cholera Surveillance Data Coverage - National Level'
    
    ax.set_title(title, fontsize=32, fontweight='bold', pad=35)
    
    # Create legend with larger font
    legend_elements = [
        plt.Rectangle((0,0),1,1, facecolor='white', edgecolor='black', label='No Data'),
        plt.Rectangle((0,0),1,1, facecolor='#0167af', label='JHU Database'),
        plt.Rectangle((0,0),1,1, facecolor='#E74C3C', label='WHO Dashboard'),
        plt.Rectangle((0,0),1,1, facecolor='#2ECC71', label='AI Enhanced'),
        plt.Rectangle((0,0),1,1, facecolor='#9B59B6', label='Mixed Sources')
    ]
    
    # Place legend below heatmap in 1 horizontal row
    ax.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, -0.10), 
             fontsize=22, ncol=5, frameon=False, columnspacing=1.2)  # Increased text size for better readability
    
    # Add grid
    ax.grid(True, which='major', alpha=0.3, linewidth=0.5)
    ax.grid(True, which='minor', alpha=0.1, linewidth=0.3)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save figure (PNG only) - different filenames for each type
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    file_suffix = "national" if data_type == "National" else "subnational"
    output_file = f"{OUTPUT_PATH}/cholera_coverage_heatmap_{file_suffix}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    logger.info(f"✅ {data_type} heatmap saved: {output_file}")
    
    # Close the figure to free memory
    plt.close()
    
    return output_file

def generate_summary_stats(data_df, countries, data_type="Combined"):
    """Generate summary statistics for the heatmap."""
    
    logger.info("\n" + "="*80)
    logger.info(f"COVERAGE HEATMAP SUMMARY STATISTICS - {data_type.upper()}")
    logger.info("="*80)
    
    # Overall stats
    total_countries = len(countries)
    countries_with_data = len(data_df['country_iso'].unique()) if len(data_df) > 0 else 0
    
    logger.info(f"📊 Total MOSAIC countries: {total_countries}")
    logger.info(f"📊 Countries with {data_type.lower()} data: {countries_with_data}")
    logger.info(f"📊 Total {data_type.lower()} observations: {len(data_df):,}")
    
    # Source breakdown
    if len(data_df) > 0 and 'source_database' in data_df.columns:
        source_counts = data_df['source_database'].value_counts()
        total_obs = len(data_df)
        
        logger.info(f"\n📈 DATA SOURCE BREAKDOWN ({data_type.upper()}):")
        for source, count in source_counts.items():
            percentage = (count / total_obs) * 100
            logger.info(f"   • {source}: {count:,} observations ({percentage:.1f}%)")
    
    # Temporal coverage
    if len(data_df) > 0:
        earliest = data_df['TL'].min()
        latest = data_df['TR'].max()
        span_years = (latest - earliest).days / 365.25
        
        logger.info(f"\n📅 TEMPORAL COVERAGE ({data_type.upper()}):")
        logger.info(f"   • Earliest data: {earliest.strftime('%Y-%m-%d')}")
        logger.info(f"   • Latest data: {latest.strftime('%Y-%m-%d')}")
        logger.info(f"   • Total span: {span_years:.1f} years")
    
    # Geographic breakdown for sub-national data
    if data_type == "Sub-national" and len(data_df) > 0:
        if 'Location' in data_df.columns:
            # Count unique administrative levels
            location_levels = data_df['Location'].str.split('::').str.len()
            level_counts = location_levels.value_counts().sort_index()
            
            logger.info(f"\n🗺️  ADMINISTRATIVE LEVEL BREAKDOWN:")
            for level, count in level_counts.items():
                if level == 3:
                    level_name = "Provincial"
                elif level == 4:
                    level_name = "District"
                elif level > 4:
                    level_name = f"Level {level-2}"
                else:
                    level_name = f"Unknown Level {level}"
                logger.info(f"   • {level_name}: {count:,} observations")
    
    logger.info("="*80 + "\n")

def main():
    """Generate coverage heatmap visualizations for both national and sub-national data."""
    
    logger.info("=" * 80)
    logger.info("CHOLERA COVERAGE HEATMAP GENERATOR - DUAL PLOTS")
    logger.info("=" * 80)
    logger.info("Creating visual coverage analysis by country and data source...")
    logger.info("Generating separate plots for national and sub-national data...")
    logger.info("")
    
    # Load all country data
    logger.info("Loading integrated cholera data from all countries...")
    data_df = load_all_country_data()
    
    if len(data_df) == 0:
        logger.error("❌ No data found. Cannot generate heatmaps.")
        return
    
    # Separate national and sub-national data
    logger.info("Separating national and sub-national observations...")
    national_data, subnational_data = separate_national_subnational_data(data_df)
    
    output_files = []
    
    # Generate national-level heatmap
    if len(national_data) > 0:
        logger.info("\n🏛️  GENERATING NATIONAL-LEVEL HEATMAP...")
        logger.info("Creating coverage matrix for country-level data...")
        coverage_matrix_nat, source_matrix_nat, countries_nat, time_periods, time_labels, source_colors = create_coverage_heatmap(
            national_data, data_type="National", monthly=False
        )
        
        logger.info("Creating national-level visualization...")
        output_file_nat = plot_heatmap(
            coverage_matrix_nat, source_matrix_nat, countries_nat, time_periods, time_labels, source_colors, data_type="National", monthly=False
        )
        output_files.append(output_file_nat)
        
        # Generate summary statistics for national data
        generate_summary_stats(national_data, countries_nat, data_type="National")
    else:
        logger.warning("⚠️  No national-level data found. Skipping national heatmap.")
    
    # Generate sub-national heatmap
    if len(subnational_data) > 0:
        logger.info("\n🗺️  GENERATING SUB-NATIONAL HEATMAP...")
        logger.info("Creating coverage matrix for provincial/district-level data...")
        coverage_matrix_sub, source_matrix_sub, countries_sub, time_periods, time_labels, source_colors = create_coverage_heatmap(
            subnational_data, data_type="Sub-national", monthly=False
        )
        
        logger.info("Creating sub-national visualization...")
        output_file_sub = plot_heatmap(
            coverage_matrix_sub, source_matrix_sub, countries_sub, time_periods, time_labels, source_colors, data_type="Sub-national", monthly=False
        )
        output_files.append(output_file_sub)
        
        # Generate summary statistics for sub-national data
        generate_summary_stats(subnational_data, countries_sub, data_type="Sub-national")
    else:
        logger.warning("⚠️  No sub-national data found. Skipping sub-national heatmap.")
    
    # Overall priority breakdown (once for both plots)
    coverage_ref = f"{REFERENCE_PATH}/agent_quick_reference.csv"
    if os.path.exists(coverage_ref):
        ref_df = pd.read_csv(coverage_ref)
        high_priority = len(ref_df[ref_df['search_priority'] == 'HIGH'])
        medium_priority = len(ref_df[ref_df['search_priority'] == 'MEDIUM'])
        low_priority = len(ref_df[ref_df['search_priority'] == 'LOW'])
        
        logger.info("\n" + "="*80)
        logger.info("🎯 OVERALL PRIORITY BREAKDOWN (ALL MOSAIC COUNTRIES):")
        logger.info(f"   • HIGH priority (AI focus): {high_priority} countries")
        logger.info(f"   • MEDIUM priority: {medium_priority} countries")
        logger.info(f"   • LOW priority: {low_priority} countries")
        logger.info("="*80)
    
    logger.info("\n🎯 HEATMAP INTERPRETATION:")
    logger.info("• White cells = No cholera data available")
    logger.info("• Blue cells = JHU historical database")
    logger.info("• Red cells = WHO dashboard data")
    logger.info("• Green cells = AI-enhanced sources")
    logger.info("• Purple cells = Multiple sources in same year")
    logger.info("")
    logger.info("✅ Coverage heatmap generation complete!")
    logger.info(f"📁 Output files generated: {len(output_files)}")
    for output_file in output_files:
        logger.info(f"   • {output_file}")
    
    return output_files

if __name__ == "__main__":
    main()