#!/usr/bin/env python3
"""
MOSAIC AI Cholera Data Collection - Weekly Surveillance Longform Dataset Generator

Creates a comprehensive weekly longform dataset combining:
1. MOSAIC processed surveillance data (weekly format)
2. AI-enhanced data (date ranges mapped to overlapping weeks)

Output format:
country, iso_code, source, year, week, date_from, date_to, present
- Complete weekly time series from 1970 to present
- present: 1 if data exists for that week, 0 otherwise
- source: "MOSAIC" for original surveillance, "AI" for AI-enhanced data
"""

import csv
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Set, Tuple
import calendar

def load_country_mapping(base_path: Path) -> Dict[str, str]:
    """Load country name to ISO code mapping for MOSAIC framework countries"""
    mapping_file = base_path / "reference" / "country_mapping.json"
    
    if not mapping_file.exists():
        print(f"Error: {mapping_file} not found")
        return {}
    
    with open(mapping_file, 'r', encoding='utf-8') as f:
        country_mapping = json.load(f)
    
    # Extract MOSAIC framework countries
    mosaic_countries = {}
    for iso, info in country_mapping.get('countries', {}).items():
        if info.get('mosaic_framework', False):
            mosaic_countries[iso] = info.get('name', iso)
    
    return mosaic_countries

def generate_complete_weekly_framework(start_year: int = 1970) -> List[Dict]:
    """Generate complete weekly framework from start_year to present"""
    
    current_date = datetime.now()
    end_year = current_date.year
    
    weekly_framework = []
    
    print(f"Generating weekly framework from {start_year} to {end_year}...")
    
    # Start from January 1st of start_year
    current_week_start = datetime(start_year, 1, 1)
    
    # Adjust to Monday (ISO week starts on Monday)
    days_since_monday = current_week_start.weekday()
    current_week_start = current_week_start - timedelta(days=days_since_monday)
    
    week_counter = 1
    
    while current_week_start <= current_date:
        week_end = current_week_start + timedelta(days=6)  # Sunday
        
        # Get year and week number
        year = current_week_start.year
        week_num = current_week_start.isocalendar()[1]
        
        weekly_framework.append({
            'year': year,
            'week': week_num,
            'date_from': current_week_start.strftime('%Y-%m-%d'),
            'date_to': week_end.strftime('%Y-%m-%d'),
        })
        
        current_week_start += timedelta(days=7)
        week_counter += 1
    
    print(f"✅ Generated {len(weekly_framework)} weeks from {start_year} to {end_year}")
    return weekly_framework

def load_mosaic_surveillance_data(base_path: Path) -> Dict[str, Set[Tuple[int, int]]]:
    """Load MOSAIC processed surveillance data"""
    
    surveillance_file = base_path.parent / "MOSAIC-data" / "processed" / "cholera" / "weekly" / "cholera_surveillance_weekly_combined.csv"
    mosaic_data = {}
    
    if not surveillance_file.exists():
        print(f"Warning: {surveillance_file} not found")
        return mosaic_data
    
    print(f"Loading MOSAIC surveillance data from: {surveillance_file}")
    
    try:
        with open(surveillance_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                iso_code = row['iso_code'].strip('"')
                year = int(row['year'].strip('"'))
                week = int(row['week'].strip('"'))
                cases = row['cases'].strip('"')
                deaths = row['deaths'].strip('"')
                
                # Only count weeks where we have actual surveillance data (not NA)
                if cases != 'NA':
                    if iso_code not in mosaic_data:
                        mosaic_data[iso_code] = set()
                    mosaic_data[iso_code].add((year, week))
    
    except Exception as e:
        print(f"Error reading {surveillance_file}: {e}")
        return mosaic_data
    
    print(f"✅ Loaded MOSAIC data for {len(mosaic_data)} countries")
    return mosaic_data

def load_ai_enhanced_data(base_path: Path, iso_code: str) -> Set[Tuple[int, int]]:
    """Load AI-enhanced data and map to overlapping weeks"""
    
    cholera_file = base_path / "data" / iso_code / "cholera_data.csv"
    ai_weeks = set()
    
    if not cholera_file.exists():
        return ai_weeks
    
    try:
        with open(cholera_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                tl = row.get('TL', '').strip()
                tr = row.get('TR', '').strip()
                
                if tl:
                    try:
                        start_date = datetime.strptime(tl, '%Y-%m-%d')
                        end_date = datetime.strptime(tr, '%Y-%m-%d') if tr else start_date
                        
                        # Map date range to all overlapping weeks
                        current_date = start_date
                        while current_date <= end_date:
                            year = current_date.year
                            week = current_date.isocalendar()[1]
                            ai_weeks.add((year, week))
                            current_date += timedelta(days=1)
                            
                    except ValueError:
                        continue  # Skip invalid dates
    
    except Exception as e:
        pass  # Silently skip files that can't be read
    
    return ai_weeks

def generate_longform_dataset(base_path: Path) -> List[Dict]:
    """Generate complete longform weekly surveillance dataset"""
    
    # Load components
    country_mapping = load_country_mapping(base_path)
    weekly_framework = generate_complete_weekly_framework(1970)
    mosaic_data = load_mosaic_surveillance_data(base_path)
    
    longform_data = []
    
    print("Generating longform dataset...")
    
    for iso_code, country_name in country_mapping.items():
        print(f"  Processing {country_name} ({iso_code})...")
        
        # Get data availability for this country
        mosaic_weeks = mosaic_data.get(iso_code, set())
        ai_weeks = load_ai_enhanced_data(base_path, iso_code)
        
        # Generate records for each week
        for week_info in weekly_framework:
            year = week_info['year']
            week = week_info['week']
            date_from = week_info['date_from']
            date_to = week_info['date_to']
            
            # Check MOSAIC data availability
            has_mosaic = 1 if (year, week) in mosaic_weeks else 0
            has_ai = 1 if (year, week) in ai_weeks else 0
            
            # Add MOSAIC record
            longform_data.append({
                'country': country_name,
                'iso_code': iso_code,
                'source': 'MOSAIC',
                'year': year,
                'week': week,
                'date_from': date_from,
                'date_to': date_to,
                'present': has_mosaic
            })
            
            # Add AI record
            longform_data.append({
                'country': country_name,
                'iso_code': iso_code,
                'source': 'AI',
                'year': year,
                'week': week,
                'date_from': date_from,
                'date_to': date_to,
                'present': has_ai
            })
    
    return longform_data

def save_longform_dataset(base_path: Path, longform_data: List[Dict]):
    """Save the longform dataset to CSV"""
    
    output_file = base_path / "dashboard" / "weekly_surveillance_longform.csv"
    
    print(f"Saving longform dataset to {output_file}...")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['country', 'iso_code', 'source', 'year', 'week', 'date_from', 'date_to', 'present']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(longform_data)
    
    print(f"✅ Longform dataset saved: {len(longform_data):,} rows")

def print_summary_stats(longform_data: List[Dict]):
    """Print summary statistics for the longform dataset"""
    
    df = pd.DataFrame(longform_data)
    
    print("\\n" + "="*60)
    print("WEEKLY SURVEILLANCE LONGFORM DATASET SUMMARY")
    print("="*60)
    
    print(f"📊 Total rows: {len(df):,}")
    print(f"🌍 Countries: {df['iso_code'].nunique()}")
    print(f"📅 Year range: {df['year'].min()}-{df['year'].max()}")
    print(f"📅 Total weeks: {df[df['source'] == 'MOSAIC']['week'].nunique()}")
    
    # Source breakdown
    source_stats = df.groupby('source').agg({
        'present': ['sum', 'count']
    }).round(2)
    
    print(f"\\n📊 Data availability by source:")
    for source in ['MOSAIC', 'AI']:
        present_count = df[(df['source'] == source) & (df['present'] == 1)].shape[0]
        total_count = df[df['source'] == source].shape[0]
        coverage_pct = (present_count / total_count * 100) if total_count > 0 else 0
        
        print(f"   {source}: {present_count:,} / {total_count:,} weeks ({coverage_pct:.1f}%)")
    
    # Country breakdown
    print(f"\\n🌍 Top 10 countries by MOSAIC coverage:")
    mosaic_df = df[df['source'] == 'MOSAIC']
    country_mosaic = mosaic_df.groupby(['country', 'iso_code'])['present'].sum().reset_index()
    country_mosaic = country_mosaic.sort_values('present', ascending=False)
    
    for _, row in country_mosaic.head(10).iterrows():
        print(f"   {row['country']} ({row['iso_code']}): {row['present']} weeks")
    
    print(f"\\n🤖 Countries with AI-enhanced data:")
    ai_df = df[df['source'] == 'AI']
    country_ai = ai_df.groupby(['country', 'iso_code'])['present'].sum().reset_index()
    country_ai = country_ai[country_ai['present'] > 0].sort_values('present', ascending=False)
    
    print(f"   {len(country_ai)} countries have AI data")
    for _, row in country_ai.head(10).iterrows():
        print(f"   {row['country']} ({row['iso_code']}): {row['present']} weeks")
    
    print("="*60)

def main():
    """Main function"""
    base_path = Path(__file__).parent.parent
    
    print("="*60)
    print("MOSAIC AI Cholera Data - Weekly Surveillance Longform Dataset")
    print("="*60)
    
    # Generate the longform dataset
    longform_data = generate_longform_dataset(base_path)
    
    # Save to CSV
    save_longform_dataset(base_path, longform_data)
    
    # Print summary statistics
    print_summary_stats(longform_data)

if __name__ == "__main__":
    main()