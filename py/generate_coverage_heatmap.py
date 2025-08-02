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
OUTPUT_PATH = "./figures"

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
        country_data_path = f"{DATA_PATH}/{country_iso}/cholera_data.csv"
        
        if os.path.exists(country_data_path):
            try:
                df = pd.read_csv(country_data_path)
                if len(df) > 0:
                    df['country_iso'] = country_iso
                    df['country_name'] = country_info['name']
                    all_data.append(df)
                    logger.info(f"Loaded {len(df)} observations from {country_iso}")
            except Exception as e:
                logger.warning(f"Error loading {country_iso}: {e}")
                continue
    
    if not all_data:
        logger.error("No country data found!")
        return pd.DataFrame()
    
    # Combine all data
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Parse dates
    combined_df['TL'] = pd.to_datetime(combined_df['TL'])
    combined_df['TR'] = pd.to_datetime(combined_df['TR'])
    
    # Filter meaningful observations
    meaningful_data = combined_df[
        (combined_df['sCh'].notna() & (combined_df['sCh'] > 0)) |
        (combined_df['deaths'].notna() & (combined_df['deaths'] > 0)) |
        (combined_df['cCh'].notna() & (combined_df['cCh'] > 0))
    ].copy()
    
    logger.info(f"Total observations: {len(combined_df)}")
    logger.info(f"Meaningful observations: {len(meaningful_data)}")
    
    return meaningful_data

def create_coverage_heatmap(data_df, start_year=1970, end_year=2025):
    """Generate coverage heatmap by country and year."""
    
    # Create year range
    years = list(range(start_year, end_year + 1))
    
    # Get unique countries sorted by total data availability
    country_counts = data_df.groupby(['country_iso', 'country_name']).size().reset_index(name='count')
    country_counts = country_counts.sort_values('count', ascending=True)
    countries = [(row['country_iso'], row['country_name']) for _, row in country_counts.iterrows()]
    
    # Create coverage matrix
    coverage_matrix = np.zeros((len(countries), len(years)), dtype=int)
    source_matrix = np.full((len(countries), len(years)), '', dtype=object)
    
    # Source database mapping to colors
    source_colors = {
        'JHU': 1,      # Blue
        'WHO': 2,      # Orange  
        'AI': 3,       # Green
        'Mixed': 4     # Purple (multiple sources in same year)
    }
    
    for i, (country_iso, country_name) in enumerate(countries):
        country_data = data_df[data_df['country_iso'] == country_iso]
        
        for year in years:
            year_data = country_data[
                (country_data['TL'].dt.year <= year) & 
                (country_data['TR'].dt.year >= year)
            ]
            
            if len(year_data) > 0:
                # Check sources for this year
                year_sources = year_data['source_database'].unique()
                year_sources = [s for s in year_sources if pd.notna(s)]
                
                if len(year_sources) == 1:
                    source = year_sources[0]
                    coverage_matrix[i, year - start_year] = source_colors.get(source, 1)
                    source_matrix[i, year - start_year] = source
                elif len(year_sources) > 1:
                    coverage_matrix[i, year - start_year] = source_colors['Mixed']
                    source_matrix[i, year - start_year] = 'Mixed'
                else:
                    coverage_matrix[i, year - start_year] = 1  # Default to JHU
                    source_matrix[i, year - start_year] = 'Unknown'
    
    return coverage_matrix, source_matrix, countries, years, source_colors

def plot_heatmap(coverage_matrix, source_matrix, countries, years, source_colors):
    """Create and save the coverage heatmap."""
    
    # Create figure with wider aspect ratio for better readability
    fig, ax = plt.subplots(figsize=(32, 14))
    
    # Create custom colormap
    colors = ['white', '#1f77b4', '#ff7f0e', '#2ca02c', '#9467bd']  # white, blue, orange, green, purple
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap(colors)
    
    # Plot heatmap
    im = ax.imshow(coverage_matrix, cmap=cmap, aspect='auto', vmin=0, vmax=4)
    
    # Set country labels (Y-axis) with larger font
    country_labels = [f"{iso} - {name}" for iso, name in countries]
    ax.set_yticks(range(len(countries)))
    ax.set_yticklabels(country_labels, fontsize=14)
    
    # Set year labels (X-axis) - show every 5 years with larger font
    year_indices = [i for i, year in enumerate(years) if year % 5 == 0]
    year_labels = [str(years[i]) for i in year_indices]
    ax.set_xticks(year_indices)
    ax.set_xticklabels(year_labels, rotation=45, fontsize=14)
    
    # Add minor ticks for all years
    ax.set_xticks(range(len(years)), minor=True)
    
    # Labels and title with larger fonts
    ax.set_xlabel('Year', fontsize=18, fontweight='bold')
    ax.set_ylabel('Country', fontsize=18, fontweight='bold')
    ax.set_title('Cholera Surveillance Data Coverage by Country and Source\n(MOSAIC Framework Countries)', 
                fontsize=22, fontweight='bold', pad=30)
    
    # Create legend with larger font
    legend_elements = [
        plt.Rectangle((0,0),1,1, facecolor='white', edgecolor='black', label='No Data'),
        plt.Rectangle((0,0),1,1, facecolor='#1f77b4', label='JHU Database'),
        plt.Rectangle((0,0),1,1, facecolor='#ff7f0e', label='WHO Dashboard'),
        plt.Rectangle((0,0),1,1, facecolor='#2ca02c', label='AI Enhanced'),
        plt.Rectangle((0,0),1,1, facecolor='#9467bd', label='Mixed Sources')
    ]
    
    ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1.02, 1), 
             fontsize=14, title='Data Source', title_fontsize=16)
    
    # Add grid
    ax.grid(True, which='major', alpha=0.3, linewidth=0.5)
    ax.grid(True, which='minor', alpha=0.1, linewidth=0.3)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save figure (PNG only)
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    output_file = f"{OUTPUT_PATH}/cholera_coverage_heatmap.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    logger.info(f"✅ Heatmap saved: {output_file}")
    
    plt.show()
    
    return output_file

def generate_summary_stats(data_df, countries):
    """Generate summary statistics for the heatmap."""
    
    logger.info("\n" + "="*80)
    logger.info("COVERAGE HEATMAP SUMMARY STATISTICS")
    logger.info("="*80)
    
    # Overall stats
    total_countries = len(countries)
    countries_with_data = len(data_df['country_iso'].unique())
    
    logger.info(f"📊 Total MOSAIC countries: {total_countries}")
    logger.info(f"📊 Countries with data: {countries_with_data}")
    logger.info(f"📊 Countries needing complete collection: {total_countries - countries_with_data}")
    
    # Source breakdown
    if 'source_database' in data_df.columns:
        source_counts = data_df['source_database'].value_counts()
        total_obs = len(data_df)
        
        logger.info(f"\n📈 DATA SOURCE BREAKDOWN:")
        for source, count in source_counts.items():
            percentage = (count / total_obs) * 100
            logger.info(f"   • {source}: {count:,} observations ({percentage:.1f}%)")
    
    # Temporal coverage
    if len(data_df) > 0:
        earliest = data_df['TL'].min()
        latest = data_df['TR'].max()
        span_years = (latest - earliest).days / 365.25
        
        logger.info(f"\n📅 TEMPORAL COVERAGE:")
        logger.info(f"   • Earliest data: {earliest.strftime('%Y-%m-%d')}")
        logger.info(f"   • Latest data: {latest.strftime('%Y-%m-%d')}")
        logger.info(f"   • Total span: {span_years:.1f} years")
    
    # Countries by coverage level
    coverage_ref = f"{REFERENCE_PATH}/agent_quick_reference.csv"
    if os.path.exists(coverage_ref):
        ref_df = pd.read_csv(coverage_ref)
        high_priority = len(ref_df[ref_df['search_priority'] == 'HIGH'])
        medium_priority = len(ref_df[ref_df['search_priority'] == 'MEDIUM'])
        low_priority = len(ref_df[ref_df['search_priority'] == 'LOW'])
        
        logger.info(f"\n🎯 PRIORITY BREAKDOWN:")
        logger.info(f"   • HIGH priority (AI focus): {high_priority} countries")
        logger.info(f"   • MEDIUM priority: {medium_priority} countries")
        logger.info(f"   • LOW priority: {low_priority} countries")
    
    logger.info("="*80 + "\n")

def main():
    """Generate coverage heatmap visualization."""
    
    logger.info("=" * 80)
    logger.info("CHOLERA COVERAGE HEATMAP GENERATOR")
    logger.info("=" * 80)
    logger.info("Creating visual coverage analysis by country and data source...")
    logger.info("")
    
    # Load all country data
    logger.info("Loading integrated cholera data from all countries...")
    data_df = load_all_country_data()
    
    if len(data_df) == 0:
        logger.error("❌ No data found. Cannot generate heatmap.")
        return
    
    # Create coverage heatmap
    logger.info("Generating coverage matrix...")
    coverage_matrix, source_matrix, countries, years, source_colors = create_coverage_heatmap(data_df)
    
    # Plot and save heatmap
    logger.info("Creating visualization...")
    output_file = plot_heatmap(coverage_matrix, source_matrix, countries, years, source_colors)
    
    # Generate summary statistics
    generate_summary_stats(data_df, countries)
    
    logger.info("🎯 HEATMAP INTERPRETATION:")
    logger.info("• White cells = No cholera data available")
    logger.info("• Blue cells = JHU historical database")
    logger.info("• Orange cells = WHO dashboard data")
    logger.info("• Green cells = AI-enhanced sources")
    logger.info("• Purple cells = Multiple sources in same year")
    logger.info("")
    logger.info("✅ Coverage heatmap generation complete!")
    logger.info(f"📁 Output saved: {output_file}")

if __name__ == "__main__":
    main()