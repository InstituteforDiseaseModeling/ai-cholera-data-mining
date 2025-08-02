#!/usr/bin/env python3
"""
Integrated Coverage Gap Analysis

This script analyzes data coverage gaps from the integrated JHU/WHO baseline datasets
in ./data/{ISO}/cholera_data.csv files, generating agent reference files for targeted
AI data collection.

Replaces the old external surveillance data approach with analysis of the actual
integrated baseline data now available.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
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

def analyze_country_integrated_coverage(country_iso, country_info):
    """
    Analyze coverage for a single country from integrated cholera_data.csv.
    
    Returns dict with coverage metrics and gap periods.
    """
    
    country_data_path = f"{DATA_PATH}/{country_iso}"
    country_name = country_info['name']
    
    # Check if country has integrated data
    cholera_data_file = f"{country_data_path}/cholera_data.csv"
    if not os.path.exists(cholera_data_file):
        logger.warning(f"No cholera_data.csv found for {country_iso} ({country_name})")
        return {
            'iso_code': country_iso,
            'country': country_name,
            'coverage_pct': 0.0,
            'data_span': 'No data',
            'search_priority': 'HIGH',
            'missing_recent_years': '2000-2024',
            'priority_periods': 'Complete data collection needed',
            'total_observations': 0,
            'meaningful_observations': 0,
            'earliest_date': None,
            'latest_date': None,
            'data_sources': 0,
            'jhu_observations': 0,
            'who_observations': 0,
            'ai_observations': 0,
            'major_gaps': 0
        }
    
    try:
        # Load integrated baseline data
        data_df = pd.read_csv(cholera_data_file)
        
        if len(data_df) == 0:
            logger.warning(f"Empty cholera_data.csv for {country_iso}")
            return None
        
        # Parse dates
        data_df['TL'] = pd.to_datetime(data_df['TL'])
        data_df['TR'] = pd.to_datetime(data_df['TR'])
        
        # Filter out zero/empty observations for coverage analysis
        # Only count rows with meaningful cholera data
        meaningful_data = data_df[
            (data_df['sCh'].notna() & (data_df['sCh'] > 0)) |
            (data_df['deaths'].notna() & (data_df['deaths'] > 0)) |
            (data_df['cCh'].notna() & (data_df['cCh'] > 0))
        ].copy()
        
        # Calculate basic metrics
        total_observations = len(data_df)
        meaningful_observations = len(meaningful_data)
        
        if meaningful_observations == 0:
            earliest_date = data_df['TL'].min()
            latest_date = data_df['TR'].max()
            coverage_pct = 5.0  # Some data exists but no meaningful cholera cases
        else:
            earliest_date = meaningful_data['TL'].min()
            latest_date = meaningful_data['TR'].max()
            
            # Calculate coverage as percentage of weeks with data
            date_range_days = (latest_date - earliest_date).days + 1
            expected_weeks = date_range_days / 7
            
            # Create weekly grid and check coverage
            weeks_covered = set()
            for _, row in meaningful_data.iterrows():
                # Count weeks covered by each observation
                start_week = row['TL'].isocalendar()[1] + (row['TL'].year * 52)
                end_week = row['TR'].isocalendar()[1] + (row['TR'].year * 52)
                weeks_covered.update(range(start_week, end_week + 1))
            
            coverage_pct = min((len(weeks_covered) / expected_weeks) * 100, 100) if expected_weeks > 0 else 0
        
        # Analyze data sources
        source_counts = data_df['source_database'].value_counts()
        jhu_observations = source_counts.get('JHU', 0)
        who_observations = source_counts.get('WHO', 0) 
        ai_observations = source_counts.get('AI', 0)
        data_sources = len(data_df['source'].unique())
        
        # Identify temporal gaps (periods ≥1 week without data)
        meaningful_data_sorted = meaningful_data.sort_values('TL')
        major_gaps = []
        
        if len(meaningful_data_sorted) > 1:
            for i in range(1, len(meaningful_data_sorted)):
                prev_end = meaningful_data_sorted.iloc[i-1]['TR']
                curr_start = meaningful_data_sorted.iloc[i]['TL']
                gap_days = (curr_start - prev_end).days
                
                # Consider gaps ≥ 7 days (1 week) as significant
                if gap_days >= 7:
                    major_gaps.append((prev_end, curr_start, gap_days))
        
        # Determine search priority
        current_year = datetime.now().year
        has_recent_data = latest_date.year >= (current_year - 2) if latest_date else False
        
        if coverage_pct < 70:
            priority = 'HIGH'
        elif coverage_pct < 90:
            priority = 'MEDIUM'
        else:
            priority = 'LOW'
        
        # Identify missing recent years (2018-2024 focus period)
        focus_years = list(range(2018, current_year + 1))
        if meaningful_observations > 0:
            data_years = set(meaningful_data['TL'].dt.year.unique())
        else:
            data_years = set(data_df['TL'].dt.year.unique())
        missing_recent = [str(year) for year in focus_years if year not in data_years]
        
        # Determine priority periods for AI agent focus
        if major_gaps:
            # Focus on the most recent major gap
            latest_gap = max(major_gaps, key=lambda x: x[1])
            priority_periods = f"{latest_gap[0].strftime('%Y-%m-%d')} to {latest_gap[1].strftime('%Y-%m-%d')}"
        elif not has_recent_data and latest_date:
            # Extend to present if no recent data
            priority_periods = f"{latest_date.strftime('%Y-%m-%d')} to {current_year}-01-01"
        elif earliest_date and earliest_date.year > 1990:
            # Historical extension if data starts after 1990
            priority_periods = f"1970-01-01 to {earliest_date.strftime('%Y-%m-%d')}"
        else:
            priority_periods = f"Post-{latest_date.year if latest_date else current_year} and historical extension"
        
        return {
            'iso_code': country_iso,
            'country': country_name,
            'coverage_pct': round(coverage_pct, 1),
            'data_span': f"{earliest_date.year}-{latest_date.year}" if earliest_date and latest_date else "No data",
            'search_priority': priority,
            'missing_recent_years': ', '.join(missing_recent) if missing_recent else 'None',
            'priority_periods': priority_periods,
            'total_observations': total_observations,
            'meaningful_observations': meaningful_observations,
            'earliest_date': earliest_date.strftime('%Y-%m-%d') if earliest_date else None,
            'latest_date': latest_date.strftime('%Y-%m-%d') if latest_date else None,
            'data_sources': data_sources,
            'jhu_observations': int(jhu_observations),
            'who_observations': int(who_observations),
            'ai_observations': int(ai_observations),
            'major_gaps': len(major_gaps)
        }
        
    except Exception as e:
        logger.error(f"Error analyzing {country_iso}: {e}")
        return None

def create_detailed_time_periods(results):
    """Create detailed time period analysis for agent reference."""
    
    detailed_periods = []
    
    for result in results:
        if result['total_observations'] == 0:
            continue
            
        country_iso = result['iso_code']
        country_data_path = f"{DATA_PATH}/{country_iso}/cholera_data.csv"
        
        try:
            data_df = pd.read_csv(country_data_path)
            data_df['TL'] = pd.to_datetime(data_df['TL'])
            data_df['TR'] = pd.to_datetime(data_df['TR'])
            
            # Group observations into continuous periods (allowing gaps up to 8 weeks)
            data_df = data_df.sort_values('TL')
            periods = []
            current_start = None
            current_end = None
            
            for _, row in data_df.iterrows():
                if current_start is None:
                    current_start = row['TL']
                    current_end = row['TR']
                else:
                    gap_days = (row['TL'] - current_end).days
                    
                    if gap_days <= 56:  # Continue current period (8 weeks tolerance)
                        current_end = max(current_end, row['TR'])
                    else:  # Start new period
                        periods.append((current_start, current_end))
                        current_start = row['TL']
                        current_end = row['TR']
            
            # Add final period
            if current_start is not None:
                periods.append((current_start, current_end))
            
            # Format periods for agent use
            period_strings = [f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}" 
                            for start, end in periods]
            
            detailed_periods.append({
                'country': result['country'],
                'iso_code': result['iso_code'],
                'first_data': result['earliest_date'],
                'last_data': result['latest_date'],
                'total_span_years': round((pd.to_datetime(result['latest_date']) - pd.to_datetime(result['earliest_date'])).days / 365.25, 1) if result['earliest_date'] and result['latest_date'] else 0,
                'coverage_percentage': result['coverage_pct'],
                'data_periods': len(periods),
                'major_gaps': result['major_gaps'],
                'covered_intervals': "; ".join(period_strings),
                'priority_search_periods': result['priority_periods']
            })
            
        except Exception as e:
            logger.error(f"Error creating detailed periods for {country_iso}: {e}")
            continue
    
    return detailed_periods

def main():
    """Generate integrated coverage gap analysis."""
    
    logger.info("================================================================================")
    logger.info("INTEGRATED COVERAGE GAP ANALYSIS")
    logger.info("================================================================================")
    logger.info("Analyzing data coverage from integrated JHU/WHO baseline datasets...")
    logger.info("Reading from ./data/{ISO}/cholera_data.csv files")
    logger.info("")
    
    # Ensure reference directory exists
    os.makedirs(REFERENCE_PATH, exist_ok=True)
    
    # Load country mapping
    country_mapping = load_country_mapping()
    if not country_mapping:
        logger.error("❌ Could not load country mapping")
        return
    
    logger.info(f"Analyzing {len(country_mapping)} MOSAIC framework countries...")
    
    # Analyze each country
    results = []
    high_priority = []
    medium_priority = []
    low_priority = []
    
    for country_iso, country_info in country_mapping.items():
        logger.info(f"  Analyzing {country_iso} ({country_info['name']})...")
        
        result = analyze_country_integrated_coverage(country_iso, country_info)
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
    
    # Create detailed time periods analysis
    detailed_periods = create_detailed_time_periods(results)
    periods_df = pd.DataFrame(detailed_periods)
    
    # Only sort if DataFrame is not empty
    if not periods_df.empty and 'coverage_percentage' in periods_df.columns:
        periods_df = periods_df.sort_values('coverage_percentage')
    
    # Save reference files
    quick_ref_file = f"{REFERENCE_PATH}/agent_quick_reference.csv"
    periods_file = f"{REFERENCE_PATH}/observed_time_periods.csv"
    
    results_df.to_csv(quick_ref_file, index=False)
    periods_df.to_csv(periods_file, index=False)
    
    # Create priority gaps file (major gaps only)
    major_gaps = []
    for result in results:
        if result.get('major_gaps', 0) > 0 and result['priority_periods'] != 'Complete data collection needed':
            # Parse priority periods to create gap entries
            if ' to ' in result['priority_periods']:
                gap_start, gap_end = result['priority_periods'].split(' to ')
                gap_days = (pd.to_datetime(gap_end) - pd.to_datetime(gap_start)).days
                major_gaps.append({
                    'country': result['country'],
                    'iso_code': result['iso_code'],
                    'gap_start': gap_start,
                    'gap_end': gap_end,
                    'gap_days': gap_days,
                    'gap_years': round(gap_days / 365.25, 1)
                })
    
    if major_gaps:
        gaps_df = pd.DataFrame(major_gaps)
        gaps_df = gaps_df.sort_values('gap_days', ascending=False)
        gaps_file = f"{REFERENCE_PATH}/priority_data_gaps.csv"
        gaps_df.to_csv(gaps_file, index=False)
        logger.info(f"✅ Priority gaps saved: {gaps_file}")
    
    # Print comprehensive summary
    logger.info("")
    logger.info("================================================================================")
    logger.info("INTEGRATED COVERAGE ANALYSIS COMPLETE")
    logger.info("================================================================================")
    logger.info(f"📊 Total countries analyzed: {len(results)}")
    logger.info(f"🔴 HIGH priority (AI focus): {len(high_priority)} countries")
    logger.info(f"🟡 MEDIUM priority: {len(medium_priority)} countries") 
    logger.info(f"🟢 LOW priority: {len(low_priority)} countries")
    logger.info("")
    
    # Data source breakdown
    total_obs = sum(r['total_observations'] for r in results)
    total_jhu = sum(r['jhu_observations'] for r in results)
    total_who = sum(r['who_observations'] for r in results)
    total_ai = sum(r['ai_observations'] for r in results)
    
    logger.info("📈 INTEGRATED BASELINE DATA SUMMARY:")
    logger.info(f"• Total observations: {total_obs:,}")
    if total_obs > 0:
        logger.info(f"• JHU database: {total_jhu:,} observations ({total_jhu/total_obs*100:.1f}%)")
        logger.info(f"• WHO dashboard: {total_who:,} observations ({total_who/total_obs*100:.1f}%)")
        logger.info(f"• AI-mined: {total_ai:,} observations ({total_ai/total_obs*100:.1f}%)")
    else:
        logger.info("• No observations found - baseline data conversion needed first")
        logger.info("• Run JHU and WHO conversion scripts to create integrated baseline data")
    logger.info("")
    
    # Priority country details
    if high_priority:
        logger.info("🔴 HIGH PRIORITY countries (major gaps, AI agents should focus here):")
        for result in sorted(high_priority, key=lambda x: x['coverage_pct']):
            logger.info(f"   • {result['country']} ({result['iso_code']}): {result['coverage_pct']:.1f}% coverage, {result['meaningful_observations']}/{result['total_observations']} meaningful obs")
        logger.info("")
    
    if medium_priority:
        logger.info("🟡 MEDIUM PRIORITY countries (partial coverage, moderate AI effort):")
        for result in sorted(medium_priority, key=lambda x: x['coverage_pct'])[:10]:  # Show top 10
            logger.info(f"   • {result['country']} ({result['iso_code']}): {result['coverage_pct']:.1f}% coverage, {result['meaningful_observations']}/{result['total_observations']} meaningful obs")
        if len(medium_priority) > 10:
            logger.info(f"   ... and {len(medium_priority) - 10} more")
        logger.info("")
    
    logger.info(f"✅ Agent reference files saved:")
    logger.info(f"   • {quick_ref_file}")
    logger.info(f"   • {periods_file}")
    if major_gaps:
        logger.info(f"   • {gaps_file}")
    logger.info("")
    
    logger.info("🎯 RECOMMENDATIONS FOR AI AGENTS:")
    logger.info("• Focus searches on HIGH priority countries first")
    logger.info("• Target specific priority_periods identified for each country")
    logger.info("• Use integrated baseline data as reference for validation")
    logger.info("• Countries with low meaningful_observations need systematic searches")
    logger.info("• Leverage JHU/WHO baseline to focus on gap-filling vs. broad discovery")
    logger.info("================================================================================")

if __name__ == "__main__":
    main()