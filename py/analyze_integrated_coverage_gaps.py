#!/usr/bin/env python3
"""
Integrated Coverage Gap Analysis

This script analyzes data coverage gaps from separate JHU/WHO baseline datasets
in ./data/{ISO}/cholera_data_jhu.csv and ./data/{ISO}/cholera_data_who.csv files, 
generating agent reference files for targeted AI data collection.

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
    
    # Check for separate baseline data files (JHU + WHO)
    jhu_file = f"{country_data_path}/cholera_data_jhu.csv"
    who_file = f"{country_data_path}/cholera_data_who.csv"
    
    # Load baseline data from separate files
    data_df = pd.DataFrame()
    
    if os.path.exists(jhu_file):
        try:
            jhu_df = pd.read_csv(jhu_file)
            data_df = pd.concat([data_df, jhu_df], ignore_index=True)
            logger.debug(f"Loaded {len(jhu_df)} JHU observations for {country_iso}")
        except Exception as e:
            logger.warning(f"Error reading JHU file for {country_iso}: {e}")
    
    if os.path.exists(who_file):
        try:
            who_df = pd.read_csv(who_file)
            data_df = pd.concat([data_df, who_df], ignore_index=True)
            logger.debug(f"Loaded {len(who_df)} WHO observations for {country_iso}")
        except Exception as e:
            logger.warning(f"Error reading WHO file for {country_iso}: {e}")
    
    if len(data_df) == 0:
        logger.warning(f"No baseline data files found for {country_iso} ({country_name})")
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
        
        if len(data_df) == 0:
            logger.warning(f"No baseline data available for {country_iso}")
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
    logger.info("Analyzing data coverage from separate JHU/WHO baseline datasets...")
    logger.info("Reading from ./data/{ISO}/cholera_data_jhu.csv and ./data/{ISO}/cholera_data_who.csv files")
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
    
    # Create comprehensive gaps inventory and agent-specific targeting
    logger.info("")
    logger.info("================================================================================")
    logger.info("COMPREHENSIVE GAP ANALYSIS")
    logger.info("================================================================================")
    
    gaps_df, comprehensive_gaps_file = create_comprehensive_gaps_inventory(results)
    
    if gaps_df is not None:
        create_agent_targeted_gaps(gaps_df)
        logger.info("")
        logger.info(f"✅ Enhanced gap analysis files saved:")
        logger.info(f"   • {comprehensive_gaps_file}")
        logger.info(f"   • ./reference/agent_1_priority_gaps.csv")
        logger.info(f"   • ./reference/agent_2_geographic_gaps.csv") 
        logger.info(f"   • ./reference/agent_3_validation_gaps.csv")
        logger.info(f"   • ./reference/agent_4_historical_gaps.csv")
    
    logger.info("")
    logger.info("🎯 RECOMMENDATIONS FOR AI AGENTS:")
    logger.info("• Focus searches on HIGH priority countries first")
    logger.info("• Target specific priority_periods identified for each country")
    logger.info("• Use comprehensive gaps inventory for systematic gap-filling")
    logger.info("• Use agent-specific gap files for targeted search strategies")
    logger.info("• Countries with low meaningful_observations need systematic searches")
    logger.info("• Leverage JHU/WHO baseline to focus on gap-filling vs. broad discovery")
    logger.info("================================================================================")

def get_geographic_level(location):
    """Determine geographic level from location string."""
    if not location or location == '' or pd.isna(location):
        return 'unknown'
    
    parts = str(location).split('::')
    if len(parts) == 2:  # AFR::ISO
        return 'national'
    elif len(parts) == 3:  # AFR::ISO::PROVINCE
        return 'provincial'
    elif len(parts) == 4:  # AFR::ISO::PROVINCE::DISTRICT
        return 'district'
    elif len(parts) >= 5:  # AFR::ISO::PROVINCE::DISTRICT::MUNICIPALITY
        return 'municipal'
    else:
        return 'unknown'

def get_seasonal_context(gap_start, gap_end):
    """Determine seasonal context of gap period."""
    gap_start_month = gap_start.month
    gap_end_month = gap_end.month
    
    # Simplified seasonal classification for Sub-Saharan Africa
    if gap_start_month in [12, 1, 2]:
        start_season = 'dry_season'
    elif gap_start_month in [3, 4, 5]:
        start_season = 'pre_rainy'
    elif gap_start_month in [6, 7, 8, 9]:
        start_season = 'rainy_season'
    else:  # 10, 11
        start_season = 'post_rainy'
    
    if gap_end_month in [12, 1, 2]:
        end_season = 'dry_season'
    elif gap_end_month in [3, 4, 5]:
        end_season = 'pre_rainy'
    elif gap_end_month in [6, 7, 8, 9]:
        end_season = 'rainy_season'
    else:  # 10, 11
        end_season = 'post_rainy'
    
    if start_season == end_season:
        return start_season
    else:
        return f"{start_season}_to_{end_season}"

def get_outbreak_scale(observation_row):
    """Categorize outbreak scale from observation data."""
    if pd.isna(observation_row['sCh']) or observation_row['sCh'] == 0:
        return 'no_cases'
    
    cases = observation_row['sCh']
    if cases < 10:
        return 'minimal'
    elif cases < 100:
        return 'small'
    elif cases < 1000:
        return 'moderate'
    elif cases < 5000:
        return 'large'
    else:
        return 'major'

def calculate_gap_priority_score(gap_row, current_year=None):
    """
    Calculate priority score for a gap based on multiple factors:
    - Recency (more recent = higher priority)
    - Size/Duration (larger gaps = higher priority) 
    - Geographic level (national > provincial > district)
    - Country search priority (HIGH > MEDIUM > LOW)
    
    Returns score from 0-100 (higher = more priority)
    """
    if current_year is None:
        current_year = datetime.now().year
    
    # Factor 1: Recency Score (0-40 points)
    gap_end_year = pd.to_datetime(gap_row['gap_end']).year
    years_ago = current_year - gap_end_year
    
    if years_ago <= 1:
        recency_score = 40  # Very recent
    elif years_ago <= 3:
        recency_score = 35  # Recent
    elif years_ago <= 5:
        recency_score = 25  # Moderately recent
    elif years_ago <= 10:
        recency_score = 15  # Older
    else:
        recency_score = 5   # Very old
    
    # Factor 2: Duration Score (0-30 points)
    gap_days = gap_row['gap_days']
    
    if gap_days >= 1825:  # 5+ years
        duration_score = 30
    elif gap_days >= 1095:  # 3+ years
        duration_score = 25
    elif gap_days >= 365:   # 1+ year
        duration_score = 20
    elif gap_days >= 90:    # 3+ months
        duration_score = 15
    elif gap_days >= 30:    # 1+ month
        duration_score = 10
    else:  # 7-30 days
        duration_score = 5
    
    # Factor 3: Geographic Level Score (0-20 points)
    geo_level = gap_row.get('geographic_level', 'national')
    
    if geo_level == 'national':
        geo_score = 20
    elif geo_level == 'provincial':
        geo_score = 15
    elif geo_level == 'district':
        geo_score = 10
    elif geo_level == 'municipal':
        geo_score = 5
    else:
        geo_score = 8  # unknown
    
    # Factor 4: Country Priority Score (0-10 points)
    country_priority = gap_row.get('search_priority', 'MEDIUM')
    
    if country_priority == 'HIGH':
        country_score = 10
    elif country_priority == 'MEDIUM':
        country_score = 6
    else:  # LOW
        country_score = 2
    
    # Calculate total score
    total_score = recency_score + duration_score + geo_score + country_score
    
    return min(total_score, 100)  # Cap at 100

def create_comprehensive_gaps_inventory(results):
    """
    Create comprehensive inventory of ALL gaps ≥7 days with prioritization framework.
    
    Returns: DataFrame with all gaps and priority scores
    """
    logger.info("🔍 Creating comprehensive gaps inventory...")
    
    all_gaps = []
    
    for result in results:
        if result['total_observations'] == 0:
            continue
            
        country_iso = result['iso_code']
        country_name = result['country']
        
        logger.debug(f"Processing gaps for {country_name} ({country_iso})")
        
        # Load baseline data files
        country_data_path = f"{DATA_PATH}/{country_iso}"
        jhu_file = f"{country_data_path}/cholera_data_jhu.csv"
        who_file = f"{country_data_path}/cholera_data_who.csv"
        
        # Combine baseline data
        data_df = pd.DataFrame()
        
        if os.path.exists(jhu_file):
            try:
                jhu_df = pd.read_csv(jhu_file)
                data_df = pd.concat([data_df, jhu_df], ignore_index=True)
            except Exception as e:
                logger.warning(f"Error reading JHU file for {country_iso}: {e}")
        
        if os.path.exists(who_file):
            try:
                who_df = pd.read_csv(who_file)
                data_df = pd.concat([data_df, who_df], ignore_index=True)
            except Exception as e:
                logger.warning(f"Error reading WHO file for {country_iso}: {e}")
        
        if len(data_df) == 0:
            logger.debug(f"No baseline data found for {country_iso}")
            continue
        
        # Parse dates
        data_df['TL'] = pd.to_datetime(data_df['TL'])
        data_df['TR'] = pd.to_datetime(data_df['TR'])
        
        # Filter meaningful data and group by geographic level
        meaningful_data = data_df[
            (data_df['sCh'].notna() & (data_df['sCh'] > 0)) |
            (data_df['deaths'].notna() & (data_df['deaths'] > 0)) |
            (data_df['cCh'].notna() & (data_df['cCh'] > 0))
        ].copy()
        
        if len(meaningful_data) == 0:
            continue
        
        # Add geographic level classification
        meaningful_data['geographic_level'] = meaningful_data['Location'].apply(get_geographic_level)
        
        # Process gaps by geographic level (prioritize national level)
        for geo_level in ['national', 'provincial', 'district', 'municipal']:
            level_data = meaningful_data[meaningful_data['geographic_level'] == geo_level].sort_values('TL')
            
            if len(level_data) <= 1:
                continue
                
            # Find gaps ≥7 days at this geographic level
            for i in range(1, len(level_data)):
                prev_row = level_data.iloc[i-1]
                curr_row = level_data.iloc[i]
                
                prev_end = prev_row['TR']
                curr_start = curr_row['TL']
                gap_days = (curr_start - prev_end).days
                
                if gap_days >= 7:
                    # Get outbreak scale context
                    preceding_scale = get_outbreak_scale(prev_row)
                    following_scale = get_outbreak_scale(curr_row)
                    
                    # Get seasonal context
                    seasonal_context = get_seasonal_context(prev_end, curr_start)
                    
                    gap_record = {
                        'country': country_name,
                        'iso_code': country_iso,
                        'gap_start': prev_end.strftime('%Y-%m-%d'),
                        'gap_end': curr_start.strftime('%Y-%m-%d'),
                        'gap_days': gap_days,
                        'gap_years': round(gap_days / 365.25, 2),
                        'geographic_level': geo_level,
                        'search_priority': result['search_priority'],
                        'seasonal_context': seasonal_context,
                        'preceding_outbreak_scale': preceding_scale,
                        'following_outbreak_scale': following_scale,
                        'preceding_location': prev_row['Location'],
                        'following_location': curr_row['Location'],
                        'country_coverage_pct': result['coverage_pct']
                    }
                    
                    all_gaps.append(gap_record)
        
        logger.debug(f"Found {len([g for g in all_gaps if g['iso_code'] == country_iso])} gaps for {country_name}")
    
    if not all_gaps:
        logger.warning("No gaps ≥7 days found across all countries")
        return None, None
    
    # Create DataFrame and calculate priority scores
    gaps_df = pd.DataFrame(all_gaps)
    logger.info(f"📊 Found {len(gaps_df)} total gaps ≥7 days across {gaps_df['country'].nunique()} countries")
    
    # Calculate priority scores
    gaps_df['priority_score'] = gaps_df.apply(calculate_gap_priority_score, axis=1)
    
    # Add priority tier classification
    gaps_df['priority_tier'] = pd.cut(
        gaps_df['priority_score'], 
        bins=[0, 50, 70, 85, 100], 
        labels=['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'],
        include_lowest=True
    )
    
    # Sort by priority score (highest first)
    gaps_df = gaps_df.sort_values(['priority_score', 'gap_days'], ascending=[False, False])
    
    # Save comprehensive gaps inventory
    all_gaps_file = f"{REFERENCE_PATH}/comprehensive_gaps_inventory.csv"
    gaps_df.to_csv(all_gaps_file, index=False)
    
    logger.info(f"✅ Comprehensive gaps inventory saved: {all_gaps_file}")
    
    # Print priority distribution
    priority_dist = gaps_df['priority_tier'].value_counts()
    logger.info("📈 Gap Priority Distribution:")
    for tier in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        if tier in priority_dist.index:
            logger.info(f"   • {tier}: {priority_dist[tier]} gaps")
    
    # Print top gaps
    logger.info("")
    logger.info("🎯 TOP 10 PRIORITY GAPS:")
    top_gaps = gaps_df.head(10)
    for _, gap in top_gaps.iterrows():
        logger.info(f"   • {gap['country']} ({gap['iso_code']}): {gap['gap_start']} to {gap['gap_end']} "
                   f"({gap['gap_days']} days, {gap['geographic_level']}, Score: {gap['priority_score']:.1f})")
    
    return gaps_df, all_gaps_file

def create_agent_targeted_gaps(gaps_df):
    """
    Create agent-specific gap targeting files based on comprehensive inventory.
    
    Agent 1: Top priority national/provincial gaps for baseline establishment
    Agent 2: Geographic expansion gaps (provincial/district level)
    Agent 3: Medium-duration gaps for zero-transmission validation
    Agent 4: Historical/obscure gaps requiring specialized sources
    """
    if gaps_df is None or len(gaps_df) == 0:
        return
    
    logger.info("🎯 Creating agent-specific gap targeting files...")
    
    # Agent 1: Baseline collector - Top priority national/provincial gaps
    agent1_gaps = gaps_df[
        (gaps_df['priority_tier'].isin(['CRITICAL', 'HIGH'])) &
        (gaps_df['geographic_level'].isin(['national', 'provincial'])) &
        (gaps_df['gap_days'] >= 30)  # Focus on substantial gaps
    ].head(50)  # Top 50 priority gaps
    
    agent1_file = f"{REFERENCE_PATH}/agent_1_priority_gaps.csv"
    agent1_gaps.to_csv(agent1_file, index=False)
    logger.info(f"   • Agent 1 gaps: {len(agent1_gaps)} priority national/provincial gaps → {agent1_file}")
    
    # Agent 2: Geographic expansion - District/municipal level gaps
    agent2_gaps = gaps_df[
        (gaps_df['geographic_level'].isin(['district', 'municipal'])) |
        ((gaps_df['geographic_level'] == 'provincial') & (gaps_df['priority_score'] >= 60))
    ].head(40)
    
    agent2_file = f"{REFERENCE_PATH}/agent_2_geographic_gaps.csv"
    agent2_gaps.to_csv(agent2_file, index=False)
    logger.info(f"   • Agent 2 gaps: {len(agent2_gaps)} geographic expansion gaps → {agent2_file}")
    
    # Agent 3: Zero-transmission validator - Medium gaps for absence validation
    agent3_gaps = gaps_df[
        (gaps_df['gap_days'] >= 7) & (gaps_df['gap_days'] <= 365) &  # 7 days to 1 year
        (gaps_df['priority_score'] >= 40)  # Reasonable priority
    ].head(60)
    
    agent3_file = f"{REFERENCE_PATH}/agent_3_validation_gaps.csv"
    agent3_gaps.to_csv(agent3_file, index=False)
    logger.info(f"   • Agent 3 gaps: {len(agent3_gaps)} validation-target gaps → {agent3_file}")
    
    # Agent 4: Obscure source explorer - Historical/difficult gaps
    current_year = datetime.now().year
    agent4_gaps = gaps_df[
        (pd.to_datetime(gaps_df['gap_end']).dt.year < (current_year - 5)) |  # Historical gaps
        (gaps_df['gap_days'] >= 1095)  # Very long gaps (3+ years)
    ].head(30)
    
    agent4_file = f"{REFERENCE_PATH}/agent_4_historical_gaps.csv"
    agent4_gaps.to_csv(agent4_file, index=False)
    logger.info(f"   • Agent 4 gaps: {len(agent4_gaps)} historical/obscure gaps → {agent4_file}")
    
    # Summary statistics
    total_targeted = len(agent1_gaps) + len(agent2_gaps) + len(agent3_gaps) + len(agent4_gaps)
    logger.info(f"📊 Total agent-targeted gaps: {total_targeted}")

if __name__ == "__main__":
    main()