#!/usr/bin/env python3
"""
Dual Timeline Plot Generator - National vs Sub-national Coverage

Creates timeline coverage plots showing data availability over time,
with separate tracks for national-level and sub-national-level data.
Each country gets two timeline plots:
1. National-level data coverage (AFR::{ISO} format)
2. Sub-national data coverage (provincial/district level)

Replaces the original single-track timeline plots with enhanced dual-level visualization.
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
from PIL import Image

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DATA_PATH = "./data"
REFERENCE_PATH = "./reference"
OUTPUT_PATH = "./dashboard/timeline_plots_dual"
GLOBAL_START_DATE = pd.Timestamp('1970-01-01')
GLOBAL_END_DATE = pd.Timestamp('2025-12-31')

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

def load_country_data(country_iso):
    """Load cholera data for a specific country."""
    country_data_path = f"{DATA_PATH}/{country_iso}/cholera_data.csv"
    
    if not os.path.exists(country_data_path):
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(country_data_path)
        if len(df) == 0:
            return pd.DataFrame()
        
        # Parse dates
        df['TL'] = pd.to_datetime(df['TL'])
        df['TR'] = pd.to_datetime(df['TR'])
        
        # Filter meaningful observations (including zero-case surveillance data)
        meaningful_data = df[
            (df['sCh'].notna() & (df['sCh'] >= 0)) |
            (df['deaths'].notna() & (df['deaths'] >= 0)) |
            (df['cCh'].notna() & (df['cCh'] >= 0))
        ].copy()
        
        return meaningful_data
        
    except Exception as e:
        logger.warning(f"Error loading {country_iso}: {e}")
        return pd.DataFrame()

def separate_national_subnational_data(data_df):
    """Separate data into national and sub-national based on Location field."""
    
    if len(data_df) == 0:
        return pd.DataFrame(), pd.DataFrame()
    
    # National data: Location format is AFR::{ISO} (no additional subdivisions)
    national_data = data_df[data_df['Location'].str.match(r'^AFR::[A-Z]{3}$', na=False)].copy()
    
    # Sub-national data: Location format includes provinces/districts (AFR::{ISO}::{PROVINCE} or more levels)
    subnational_data = data_df[~data_df['Location'].str.match(r'^AFR::[A-Z]{3}$', na=False)].copy()
    
    return national_data, subnational_data

def prepare_timeline_data(data_df):
    """Prepare timeline data by creating weekly coverage periods."""
    
    if len(data_df) == 0:
        return pd.DataFrame()
    
    timeline_data = []
    
    for _, row in data_df.iterrows():
        start_date = row['TL']
        end_date = row['TR']
        source_db = row.get('source_database', 'Unknown')
        
        # Create weekly periods for the observation
        current_date = start_date
        while current_date <= end_date:
            week_start = current_date - timedelta(days=current_date.weekday())
            timeline_data.append({
                'week_start': week_start,
                'source_database': source_db,
                'start_date': start_date,
                'end_date': end_date
            })
            current_date += timedelta(weeks=1)
    
    timeline_df = pd.DataFrame(timeline_data)
    
    if len(timeline_df) == 0:
        return pd.DataFrame()
    
    # Remove duplicates and aggregate by week and source
    timeline_df = timeline_df.drop_duplicates(subset=['week_start', 'source_database'])
    timeline_df = timeline_df.sort_values('week_start')
    
    return timeline_df

def create_dual_timeline_plot(country_iso, country_name, national_data, subnational_data):
    """Create dual timeline plot showing both national and sub-national coverage."""
    
    # Prepare timeline data for both levels
    national_timeline = prepare_timeline_data(national_data)
    subnational_timeline = prepare_timeline_data(subnational_data)
    
    # Create figure with two subplots (national on top, sub-national on bottom)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 8), sharex=True)
    
    # Color mapping for sources - more opaque colors
    source_colors = {
        'JHU': '#9467bd',    # Purple
        'WHO': '#1f77b4',    # Blue  
        'AI': '#2ca02c'      # Green
    }
    
    # All possible sources - ensure all 3 are always present
    all_sources = ['JHU', 'WHO', 'AI']
    source_y_positions = {source: i for i, source in enumerate(all_sources)}
    
    # Set global date range
    ax1.set_xlim(GLOBAL_START_DATE, GLOBAL_END_DATE)
    ax2.set_xlim(GLOBAL_START_DATE, GLOBAL_END_DATE)
    
    # Plot 1: National-level data
    ax1.set_title(f'{country_name} ({country_iso}) - National level', fontsize=14, fontweight='bold', pad=10)
    
    # Always show all 3 sources on Y-axis, even if no data
    ax1.set_yticks(list(source_y_positions.values()))
    ax1.set_yticklabels(list(source_y_positions.keys()), fontsize=11)
    ax1.set_ylim(-0.5, len(all_sources) - 0.5)
    
    if len(national_timeline) > 0:
        for _, row in national_timeline.iterrows():
            source = row['source_database']
            if source in source_y_positions:
                week_start = row['week_start']
                color = source_colors.get(source, '#gray')
                
                ax1.barh(source_y_positions[source], width=7, left=week_start, 
                        height=0.8, color=color, alpha=0.9, edgecolor='none')
    
    # Plot 2: Sub-national data
    ax2.set_title(f'{country_name} ({country_iso}) - Sub-national level', fontsize=14, fontweight='bold', pad=10)
    
    # Always show all 3 sources on Y-axis, even if no data
    ax2.set_yticks(list(source_y_positions.values()))
    ax2.set_yticklabels(list(source_y_positions.keys()), fontsize=11)
    ax2.set_ylim(-0.5, len(all_sources) - 0.5)
    
    if len(subnational_timeline) > 0:
        for _, row in subnational_timeline.iterrows():
            source = row['source_database']
            if source in source_y_positions:
                week_start = row['week_start']
                color = source_colors.get(source, '#gray')
                
                ax2.barh(source_y_positions[source], width=7, left=week_start, 
                        height=0.8, color=color, alpha=0.9, edgecolor='none')
    
    # Format x-axis
    years = mdates.YearLocator(5)
    years_minor = mdates.YearLocator(1)
    years_fmt = mdates.DateFormatter('%Y')
    
    for ax in [ax1, ax2]:
        ax.xaxis.set_major_locator(years)
        ax.xaxis.set_minor_locator(years_minor)
        ax.xaxis.set_major_formatter(years_fmt)
        ax.grid(True, alpha=0.3, which='major')
        ax.grid(True, alpha=0.1, which='minor')
    
    # Create horizontal legend at bottom - no frame/boundary
    legend_elements = []
    for source in all_sources:  # Use all_sources to ensure consistent order
        color = source_colors[source]
        legend_elements.append(plt.Rectangle((0,0),1,1, facecolor=color, alpha=0.9, label=f'{source} Database'))
    
    fig.legend(handles=legend_elements, loc='lower center', bbox_to_anchor=(0.5, -0.02), 
              fontsize=12, ncol=3, frameon=False)
    
    # Adjust layout to accommodate bottom legend
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.12)
    
    # Save plot
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    output_file = f"{OUTPUT_PATH}/{country_iso}_{country_name.replace(' ', '_')}_dual_timeline.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    return output_file

def generate_summary_stats(national_data, subnational_data, country_name):
    """Generate summary statistics for the timeline data."""
    
    national_count = len(national_data)
    subnational_count = len(subnational_data)
    total_count = national_count + subnational_count
    
    stats = {
        'country': country_name,
        'national_observations': national_count,
        'subnational_observations': subnational_count,
        'total_observations': total_count,
        'national_pct': (national_count / total_count * 100) if total_count > 0 else 0,
        'subnational_pct': (subnational_count / total_count * 100) if total_count > 0 else 0
    }
    
    # Date ranges
    if len(national_data) > 0:
        stats['national_start'] = national_data['TL'].min()
        stats['national_end'] = national_data['TR'].max()
    else:
        stats['national_start'] = None
        stats['national_end'] = None
    
    if len(subnational_data) > 0:
        stats['subnational_start'] = subnational_data['TL'].min()
        stats['subnational_end'] = subnational_data['TR'].max()
    else:
        stats['subnational_start'] = None
        stats['subnational_end'] = None
    
    return stats

def main():
    """Generate dual timeline plots for all countries."""
    
    logger.info("=" * 80)
    logger.info("DUAL TIMELINE PLOT GENERATOR - NATIONAL vs SUB-NATIONAL")
    logger.info("=" * 80)
    logger.info("Creating timeline coverage plots with national and sub-national tracks...")
    logger.info("")
    
    # Load country mapping
    country_mapping = load_country_mapping()
    
    if not country_mapping:
        logger.error("❌ No country mapping found. Cannot generate timeline plots.")
        return
    
    logger.info(f"📊 Processing {len(country_mapping)} MOSAIC framework countries")
    logger.info(f"📅 Global timeline range: {GLOBAL_START_DATE.strftime('%Y-%m-%d')} to {GLOBAL_END_DATE.strftime('%Y-%m-%d')}")
    logger.info("")
    
    # Track statistics
    countries_processed = 0
    countries_with_national = 0
    countries_with_subnational = 0
    countries_with_both = 0
    all_stats = []
    
    # Process each country
    for country_iso, country_info in country_mapping.items():
        country_name = country_info['name']
        logger.info(f"🔄 Processing {country_name} ({country_iso})...")
        
        try:
            # Load country data
            country_data = load_country_data(country_iso)
            
            if len(country_data) == 0:
                logger.info(f"  ⚠️  No data found for {country_name}")
                # Still create empty plot for consistency
                national_data = pd.DataFrame()
                subnational_data = pd.DataFrame()
            else:
                # Separate national and sub-national data
                national_data, subnational_data = separate_national_subnational_data(country_data)
                logger.info(f"  📈 National: {len(national_data)} obs | Sub-national: {len(subnational_data)} obs")
            
            # Create dual timeline plot
            output_file = create_dual_timeline_plot(country_iso, country_name, national_data, subnational_data)
            logger.info(f"  ✅ Timeline plot saved: {os.path.basename(output_file)}")
            
            # Generate statistics
            stats = generate_summary_stats(national_data, subnational_data, country_name)
            stats['iso_code'] = country_iso
            all_stats.append(stats)
            
            # Update counters
            countries_processed += 1
            if len(national_data) > 0:
                countries_with_national += 1
            if len(subnational_data) > 0:
                countries_with_subnational += 1
            if len(national_data) > 0 and len(subnational_data) > 0:
                countries_with_both += 1
                
        except Exception as e:
            logger.error(f"  ❌ Error processing {country_name}: {e}")
            continue
    
    # Save summary statistics
    if all_stats:
        stats_df = pd.DataFrame(all_stats)
        stats_file = f"{OUTPUT_PATH}/dual_timeline_summary.csv"
        stats_df.to_csv(stats_file, index=False)
        logger.info(f"📊 Summary statistics saved: {stats_file}")
    
    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("DUAL TIMELINE GENERATION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"📊 Countries processed: {countries_processed}")
    logger.info(f"📊 Countries with national data: {countries_with_national}")
    logger.info(f"📊 Countries with sub-national data: {countries_with_subnational}")
    logger.info(f"📊 Countries with both data types: {countries_with_both}")
    logger.info(f"📁 Timeline plots saved to: {OUTPUT_PATH}")
    logger.info("")
    logger.info("🎯 TIMELINE INTERPRETATION:")
    logger.info("• Top panel = National-level surveillance data")
    logger.info("• Bottom panel = Sub-national (provincial/district) surveillance data")
    logger.info("• Purple bars = JHU historical database")
    logger.info("• Blue bars = WHO dashboard data")
    logger.info("• Green bars = AI-enhanced sources")
    logger.info("")
    logger.info("✅ Dual timeline generation complete!")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()