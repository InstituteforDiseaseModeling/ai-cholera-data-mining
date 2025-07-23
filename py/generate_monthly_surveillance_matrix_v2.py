#!/usr/bin/env python3
"""
MOSAIC AI Cholera Data Collection - Monthly Surveillance Matrix Generator v2
Creates a comprehensive monthly surveillance matrix using the full MOSAIC processed surveillance data.

Uses comprehensive data from MOSAIC-data/processed/cholera/weekly/cholera_surveillance_weekly_combined.csv
This is much more detailed than the reference/observed_time_periods.csv summary file.

Output format:
country, iso_code, year, month, surveillance_orig, surveillance_ai
- surveillance_orig: 1 if original surveillance data exists for that month, 0 otherwise  
- surveillance_ai: 1 if AI-enhanced data exists for that month, 0 otherwise
- Years: 1970-present
- Months: 1-12 (Jan-Dec)
"""

import csv
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Set, Tuple
import calendar

def load_country_mapping(base_path: Path) -> Dict[str, str]:
    """Load country name to ISO code mapping"""
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

def load_comprehensive_surveillance_data(base_path: Path) -> Dict[str, Set[Tuple[int, int]]]:
    """Load comprehensive original surveillance data from MOSAIC-data/processed"""
    
    surveillance_file = base_path.parent / "MOSAIC-data" / "processed" / "cholera" / "weekly" / "cholera_surveillance_weekly_combined.csv"
    surveillance_months = {}
    
    if not surveillance_file.exists():
        print(f"Warning: {surveillance_file} not found")
        print("Falling back to reference file...")
        return load_reference_surveillance_data(base_path)
    
    print(f"Loading comprehensive surveillance data from: {surveillance_file}")
    
    try:
        with open(surveillance_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                iso_code = row['iso_code'].strip('"')  # Remove quotes
                date_start = row['date_start'].strip('"')
                cases = row['cases'].strip('"')
                deaths = row['deaths'].strip('"')
                
                # Only count months where we have actual surveillance data (not NA)
                if date_start and date_start != 'NA' and cases != 'NA':
                    try:
                        date_obj = datetime.strptime(date_start, '%Y-%m-%d')
                        year_month = (date_obj.year, date_obj.month)
                        
                        if iso_code not in surveillance_months:
                            surveillance_months[iso_code] = set()
                        surveillance_months[iso_code].add(year_month)
                        
                    except ValueError:
                        continue  # Skip invalid dates
    
    except Exception as e:
        print(f"Error reading {surveillance_file}: {e}")
        print("Falling back to reference file...")
        return load_reference_surveillance_data(base_path)
    
    # Print coverage summary
    print(f"✅ Loaded comprehensive surveillance data:")
    for iso, months in list(surveillance_months.items())[:10]:
        print(f"   {iso}: {len(months)} months of data")
    if len(surveillance_months) > 10:
        print(f"   ... and {len(surveillance_months) - 10} more countries")
    
    return surveillance_months

def load_reference_surveillance_data(base_path: Path) -> Dict[str, Set[Tuple[int, int]]]:
    """Fallback: Load original surveillance data from reference file"""
    
    observed_file = base_path / "reference" / "observed_time_periods.csv"
    surveillance_months = {}
    
    if not observed_file.exists():
        print(f"Warning: {observed_file} not found")
        return surveillance_months
    
    print(f"Loading reference surveillance data from: {observed_file}")
    
    def parse_date_range(date_range_str: str) -> List[Tuple[datetime, datetime]]:
        """Parse date range string into list of (start, end) datetime tuples"""
        ranges = []
        
        if not date_range_str or date_range_str.strip() == 'None':
            return ranges
        
        # Handle multiple ranges separated by semicolons
        range_parts = date_range_str.split(';')
        
        for range_part in range_parts:
            range_part = range_part.strip()
            if ' to ' in range_part:
                start_str, end_str = range_part.split(' to ')
                try:
                    start_date = datetime.strptime(start_str.strip(), '%Y-%m-%d')
                    end_date = datetime.strptime(end_str.strip(), '%Y-%m-%d')
                    ranges.append((start_date, end_date))
                except ValueError:
                    print(f"Warning: Could not parse date range '{range_part}'")
        
        return ranges
    
    with open(observed_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            iso_code = row['iso_code'].strip()
            covered_intervals = row.get('covered_intervals', '')
            
            # Parse covered intervals
            date_ranges = parse_date_range(covered_intervals)
            
            months_set = set()
            for start_date, end_date in date_ranges:
                # Generate all months in the range
                current_date = start_date.replace(day=1)  # Start of month
                while current_date <= end_date:
                    months_set.add((current_date.year, current_date.month))
                    current_date += relativedelta(months=1)
            
            surveillance_months[iso_code] = months_set
    
    return surveillance_months

def get_ai_enhanced_months(base_path: Path, iso_code: str) -> Set[Tuple[int, int]]:
    """Get AI-enhanced data months for a specific country"""
    
    cholera_file = base_path / "data" / iso_code / "cholera_data.csv"
    ai_months = set()
    
    if not cholera_file.exists():
        return ai_months
    
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
                        
                        # Generate all months in the range
                        current_date = start_date.replace(day=1)
                        while current_date <= end_date:
                            ai_months.add((current_date.year, current_date.month))
                            current_date += relativedelta(months=1)
                            
                    except ValueError:
                        print(f"Warning: Could not parse dates '{tl}' to '{tr}' for {iso_code}")
    
    except Exception as e:
        print(f"Warning: Could not read {cholera_file}: {e}")
    
    return ai_months

def generate_monthly_matrix(base_path: Path) -> List[Dict]:
    """Generate the complete monthly surveillance matrix"""
    
    print("Loading country mapping...")
    country_mapping = load_country_mapping(base_path)
    
    print("Loading comprehensive original surveillance data...")
    original_months = load_comprehensive_surveillance_data(base_path)
    
    # Generate year-month combinations (1970 to present)
    current_year = datetime.now().year
    matrix_data = []
    
    print(f"Generating matrix for years 1970-{current_year}...")
    
    for iso_code, country_name in country_mapping.items():
        print(f"  Processing {country_name} ({iso_code})...")
        
        # Get AI-enhanced months for this country
        ai_months = get_ai_enhanced_months(base_path, iso_code)
        orig_months = original_months.get(iso_code, set())
        
        # Generate all year-month combinations
        for year in range(1970, current_year + 1):
            for month in range(1, 13):
                
                # Check if data exists for this month
                has_original = 1 if (year, month) in orig_months else 0
                has_ai = 1 if (year, month) in ai_months else 0
                
                matrix_data.append({
                    'country': country_name,
                    'iso_code': iso_code,
                    'year': year,
                    'month': month,
                    'surveillance_orig': has_original,
                    'surveillance_ai': has_ai
                })
    
    return matrix_data

def save_monthly_matrix(base_path: Path, matrix_data: List[Dict]):
    """Save the monthly surveillance matrix to CSV"""
    
    output_file = base_path / "dashboard" / "monthly_surveillance_matrix.csv"
    
    print(f"Saving matrix to {output_file}...")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['country', 'iso_code', 'year', 'month', 'surveillance_orig', 'surveillance_ai']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(matrix_data)
    
    print(f"✅ Monthly surveillance matrix saved: {len(matrix_data):,} rows")

def print_summary_stats(matrix_data: List[Dict]):
    """Print summary statistics"""
    
    df = pd.DataFrame(matrix_data)
    
    print("\n" + "="*60)
    print("MONTHLY SURVEILLANCE MATRIX SUMMARY (v2 - Comprehensive)")
    print("="*60)
    
    print(f"📊 Total rows: {len(df):,}")
    print(f"🌍 Countries: {df['iso_code'].nunique()}")
    print(f"📅 Year range: {df['year'].min()}-{df['year'].max()}")
    print(f"📅 Total months: {len(df):,}")
    
    print(f"\\n🔬 Original surveillance coverage:")
    orig_coverage = df['surveillance_orig'].sum()
    print(f"   Months with data: {orig_coverage:,} ({orig_coverage/len(df)*100:.1f}%)")
    
    print(f"\\n🤖 AI-enhanced coverage:")
    ai_coverage = df['surveillance_ai'].sum() 
    print(f"   Months with data: {ai_coverage:,} ({ai_coverage/len(df)*100:.1f}%)")
    
    print(f"\\n📈 Combined coverage:")
    combined = df[(df['surveillance_orig'] == 1) | (df['surveillance_ai'] == 1)]
    print(f"   Months with any data: {len(combined):,} ({len(combined)/len(df)*100:.1f}%)")
    
    print(f"\\n🎯 AI contribution:")
    ai_only = df[(df['surveillance_orig'] == 0) & (df['surveillance_ai'] == 1)]
    print(f"   Months filled by AI only: {len(ai_only):,} ({len(ai_only)/len(df)*100:.1f}%)")
    
    # Country-level summary
    print(f"\\n🌍 Top 10 countries by original surveillance coverage:")
    country_stats = df.groupby(['country', 'iso_code']).agg({
        'surveillance_orig': 'sum',
        'surveillance_ai': 'sum'
    }).reset_index()
    
    country_stats['total_coverage'] = country_stats['surveillance_orig'] + country_stats['surveillance_ai']
    country_stats = country_stats.sort_values('surveillance_orig', ascending=False)
    
    for _, row in country_stats.head(10).iterrows():
        print(f"   {row['country']} ({row['iso_code']}): Original={row['surveillance_orig']}, AI={row['surveillance_ai']}")
    
    if len(country_stats) > 10:
        print(f"   ... and {len(country_stats) - 10} more countries")
    
    print("="*60)

def main():
    """Main function"""
    base_path = Path(__file__).parent.parent
    
    print("="*60)
    print("MOSAIC AI Cholera Data - Monthly Surveillance Matrix Generator v2")
    print("Using comprehensive MOSAIC processed surveillance data")
    print("="*60)
    
    # Generate the matrix
    matrix_data = generate_monthly_matrix(base_path)
    
    # Save to CSV
    save_monthly_matrix(base_path, matrix_data)
    
    # Print summary statistics
    print_summary_stats(matrix_data)

if __name__ == "__main__":
    main()