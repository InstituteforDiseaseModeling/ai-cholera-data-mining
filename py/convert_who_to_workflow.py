#!/usr/bin/env python3
"""
Convert WHO Dashboard Data to AI Cholera Data Mining Workflow Format

This script converts WHO cholera surveillance data from ees-cholera-mapping
into the standardized metadata.csv and cholera_data.csv format used by
the AI cholera data mining workflow.

Usage:
    python py/convert_who_to_workflow.py
"""

import pandas as pd
import os
import json
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
WHO_DATA_PATH = "/Users/johngiles/Library/CloudStorage/OneDrive-Bill&MelindaGatesFoundation/Projects/MOSAIC/ees-cholera-mapping/data/cholera/who/awd/cholera_country_weekly.csv"
DATA_PATH = "./data"
COUNTRY_MAPPING_PATH = "./reference/country_mapping.json"

# WHO country names to ISO code mapping (MOSAIC framework countries only)
WHO_TO_ISO_MAPPING = {
    "ANGOLA": "AGO",
    "BURUNDI": "BDI", 
    "DEMOCRATIC REPUBLIC OF THE CONGO": "COD",
    "ETHIOPIA": "ETH",
    "GHANA": "GHA",
    "KENYA": "KEN",
    "MALAWI": "MWI",
    "MOZAMBIQUE": "MOZ",
    "NAMIBIA": "NAM",
    "NIGERIA": "NGA",
    "SOMALIA": "SOM",
    "SOUTH SUDAN": "SSD",
    "TOGO": "TGO",
    "UGANDA": "UGA",
    "UNITED REPUBLIC OF TANZANIA": "TZA",
    "ZAMBIA": "ZMB",
    "ZIMBABWE": "ZWE"
}

def load_country_mapping():
    """Load the country mapping configuration."""
    try:
        with open(COUNTRY_MAPPING_PATH, 'r') as f:
            mapping = json.load(f)
        return mapping['countries']
    except Exception as e:
        logger.error(f"Failed to load country mapping: {str(e)}")
        return {}

def week_to_date_range(year, week):
    """Convert year and week number to date range (TL, TR)."""
    try:
        # Get the first day of the year
        jan1 = datetime(year, 1, 1)
        
        # Find the first Monday of the year (ISO week 1)
        days_since_monday = jan1.weekday()
        first_monday = jan1 - timedelta(days=days_since_monday)
        if jan1.weekday() > 3:  # If Jan 1 is Fri, Sat, or Sun, first Monday is in week 1
            first_monday += timedelta(days=7)
        
        # Calculate the start date of the given week
        week_start = first_monday + timedelta(weeks=week-1)
        week_end = week_start + timedelta(days=6)
        
        return week_start.strftime('%Y-%m-%d'), week_end.strftime('%Y-%m-%d')
    except Exception as e:
        logger.warning(f"Failed to convert week {week} of {year} to date range: {str(e)}")
        # Fallback to simple month approximation
        month = min(12, max(1, (week-1) // 4 + 1))
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year}-12-31"
        else:
            end_date = f"{year}-{month:02d}-28"
        return start_date, end_date

def calculate_cfr(cases, deaths):
    """Calculate Case Fatality Rate as percentage."""
    if pd.isna(cases) or pd.isna(deaths) or cases == 0:
        return None
    return round((deaths / cases) * 100, 2)

def convert_who_data_to_workflow(who_data, country_iso, country_name):
    """Convert WHO data for a specific country to workflow format."""
    
    country_data = who_data[who_data['country'] == country_name].copy()
    if country_data.empty:
        logger.warning(f"No WHO data found for {country_name}")
        return [], []
    
    logger.info(f"Converting {len(country_data)} WHO observations for {country_name} ({country_iso})")
    
    # Sort by year and week
    country_data = country_data.sort_values(['year', 'week'])
    
    metadata_entries = []
    cholera_data_entries = []
    
    # Group data by year for metadata entries
    years = country_data['year'].unique()
    for year in sorted(years):
        year_data = country_data[country_data['year'] == year]
        
        # Get date range for this year's data
        min_week = year_data['week'].min()
        max_week = year_data['week'].max()
        
        start_date, _ = week_to_date_range(year, min_week)
        _, end_date = week_to_date_range(year, max_week)
        
        # Create metadata entry for this year
        metadata_entry = {
            'Source': f'WHO Cholera Surveillance Dashboard ({year})',
            'URL': 'https://extranet.who.int/publicemergency/',
            'Description': f'WHO cholera surveillance data for {country_name} in {year}. Weekly reporting from WHO emergency surveillance dashboard. {len(year_data)} weekly observations.',
            'Date_Range': f'{start_date} to {end_date}',
            'Data_Type': 'Surveillance',
            'Status': 'Validated',
            'Reliability_Level': 'Level 1',
            'Validation_Status': 'WHO_Dashboard',
            'Search_Technique': 'Database_Import',
            'Language_Original': 'English',
            'Citation_Depth': 'Primary',
            'Cross_References': 'WHO_Emergency_Dashboard',
            'Discovery_Method': 'WHO_Integration',
            'source_database': 'WHO'
        }
        metadata_entries.append(metadata_entry)
        
        # Create cholera data entries for each week
        for _, row in year_data.iterrows():
            year = int(row['year'])
            week = int(row['week'])
            cases = row['cases_by_week']
            deaths = row['deaths_by_week']
            
            # Skip rows with no data
            if pd.isna(cases) and pd.isna(deaths):
                continue
                
            # Convert week to date range
            tl, tr = week_to_date_range(year, week)
            
            # Calculate CFR
            cfr = calculate_cfr(cases, deaths)
            
            # Clean numeric values
            sch = int(cases) if not pd.isna(cases) and cases > 0 else None
            deaths_clean = int(deaths) if not pd.isna(deaths) and deaths > 0 else None
            
            cholera_data_entry = {
                'Location': f'AFR::{country_iso}',
                'TL': tl,
                'TR': tr,
                'deaths': deaths_clean,
                'sCh': sch,
                'cCh': None,  # WHO dashboard doesn't distinguish confirmed vs suspected
                'CFR': cfr,
                'reporting_date': tr,  # Use end of week as reporting date
                'source': f'WHO Cholera Surveillance Dashboard ({year})',
                'confidence_weight': 0.9,  # High confidence for WHO official data
                'processing_notes': f'WHO dashboard data: {cases} cases, {deaths} deaths reported for week {week} of {year}. Converted from weekly surveillance data.',
                'source_database': 'WHO'
            }
            cholera_data_entries.append(cholera_data_entry)
    
    return metadata_entries, cholera_data_entries

def update_existing_data(country_iso, new_metadata, new_cholera_data):
    """Update existing country data files with WHO data."""
    
    country_path = os.path.join(DATA_PATH, country_iso)
    metadata_file = os.path.join(country_path, "metadata.csv")
    cholera_data_file = os.path.join(country_path, "cholera_data.csv")
    
    # Load existing data or create empty DataFrames
    try:
        existing_metadata = pd.read_csv(metadata_file)
    except:
        existing_metadata = pd.DataFrame()
    
    try:
        existing_cholera_data = pd.read_csv(cholera_data_file)
    except:
        existing_cholera_data = pd.DataFrame()
    
    # Convert new data to DataFrames
    new_metadata_df = pd.DataFrame(new_metadata)
    new_cholera_data_df = pd.DataFrame(new_cholera_data)
    
    # Determine starting indices
    start_metadata_index = len(existing_metadata) + 1 if not existing_metadata.empty else 1
    start_cholera_index = len(existing_cholera_data) + 1 if not existing_cholera_data.empty else 1
    
    # Add Index column to new metadata
    if not new_metadata_df.empty:
        new_metadata_df['Index'] = range(start_metadata_index, start_metadata_index + len(new_metadata_df))
        
        # Reorder columns to put Index first
        columns = ['Index'] + [col for col in new_metadata_df.columns if col != 'Index']
        new_metadata_df = new_metadata_df[columns]
    
    # Add Index and source_index to new cholera data
    if not new_cholera_data_df.empty:
        new_cholera_data_df['Index'] = range(start_cholera_index, start_cholera_index + len(new_cholera_data_df))
        
        # Map source names to metadata indices
        source_to_index = {}
        metadata_index = start_metadata_index
        
        for source in new_metadata_df['Source'].unique():
            source_to_index[source] = metadata_index
            metadata_index += 1
        
        new_cholera_data_df['source_index'] = new_cholera_data_df['source'].map(source_to_index)
        
        # Reorder columns
        columns = ['Index', 'Location', 'TL', 'TR', 'deaths', 'sCh', 'cCh', 'CFR', 'reporting_date', 'source_index', 'source', 'confidence_weight', 'processing_notes', 'source_database']
        new_cholera_data_df = new_cholera_data_df[columns]
    
    # Combine with existing data
    if not existing_metadata.empty and not new_metadata_df.empty:
        combined_metadata = pd.concat([existing_metadata, new_metadata_df], ignore_index=True)
    elif not new_metadata_df.empty:
        combined_metadata = new_metadata_df
    else:
        combined_metadata = existing_metadata
    
    if not existing_cholera_data.empty and not new_cholera_data_df.empty:
        combined_cholera_data = pd.concat([existing_cholera_data, new_cholera_data_df], ignore_index=True)
    elif not new_cholera_data_df.empty:
        combined_cholera_data = new_cholera_data_df
    else:
        combined_cholera_data = existing_cholera_data
    
    # Save updated files
    if not combined_metadata.empty:
        combined_metadata.to_csv(metadata_file, index=False)
        logger.info(f"  ✅ Updated {metadata_file} (+{len(new_metadata_df)} sources)")
    
    if not combined_cholera_data.empty:
        combined_cholera_data.to_csv(cholera_data_file, index=False)
        logger.info(f"  ✅ Updated {cholera_data_file} (+{len(new_cholera_data_df)} observations)")
    
    return len(new_metadata_df), len(new_cholera_data_df)

def main():
    """Convert WHO dashboard data to workflow format."""
    
    logger.info("================================================================================")
    logger.info("CONVERTING WHO DASHBOARD DATA TO AI CHOLERA WORKFLOW FORMAT")
    logger.info("================================================================================")
    logger.info("Integrating WHO cholera surveillance data from ees-cholera-mapping...")
    logger.info("")
    
    # Load WHO data
    if not os.path.exists(WHO_DATA_PATH):
        logger.error(f"❌ WHO data file not found: {WHO_DATA_PATH}")
        return
    
    logger.info(f"Loading WHO data from: {WHO_DATA_PATH}")
    who_data = pd.read_csv(WHO_DATA_PATH)
    logger.info(f"📊 Loaded {len(who_data)} WHO observations")
    
    # Load country mapping
    country_mapping = load_country_mapping()
    if not country_mapping:
        logger.error("❌ Failed to load country mapping")
        return
    
    # Filter for MOSAIC framework countries
    mosaic_countries = {iso: info for iso, info in country_mapping.items() 
                       if info.get('mosaic_framework', False)}
    
    logger.info(f"🎯 Processing {len(WHO_TO_ISO_MAPPING)} WHO countries that match MOSAIC framework")
    logger.info("")
    
    # Track conversion statistics
    total_metadata_added = 0
    total_observations_added = 0
    countries_updated = 0
    
    # Process each WHO country
    for who_country, iso_code in WHO_TO_ISO_MAPPING.items():
        if iso_code not in mosaic_countries:
            logger.warning(f"⚠️  {iso_code} not in MOSAIC framework, skipping")
            continue
            
        logger.info(f"Processing {who_country} ({iso_code})...")
        
        # Ensure country directory exists
        country_path = os.path.join(DATA_PATH, iso_code)
        os.makedirs(country_path, exist_ok=True)
        
        # Convert WHO data for this country
        country_name = mosaic_countries[iso_code]['name']
        metadata_entries, cholera_data_entries = convert_who_data_to_workflow(
            who_data, iso_code, who_country
        )
        
        if not metadata_entries and not cholera_data_entries:
            logger.info(f"  ⚠️  No data found for {who_country}")
            continue
        
        # Update country files
        metadata_added, observations_added = update_existing_data(
            iso_code, metadata_entries, cholera_data_entries
        )
        
        total_metadata_added += metadata_added
        total_observations_added += observations_added
        if metadata_added > 0 or observations_added > 0:
            countries_updated += 1
        
        logger.info("")
    
    # Create summary
    summary = {
        "conversion_date": datetime.now().isoformat(),
        "who_countries_processed": len(WHO_TO_ISO_MAPPING),
        "countries_updated": countries_updated,
        "total_metadata_added": total_metadata_added,
        "total_observations_added": total_observations_added,
        "who_countries": list(WHO_TO_ISO_MAPPING.keys()),
        "mosaic_iso_codes": list(WHO_TO_ISO_MAPPING.values()),
        "source": "WHO Cholera Surveillance Dashboard",
        "source_path": WHO_DATA_PATH,
        "conversion_script": "py/convert_who_to_workflow.py"
    }
    
    # Save summary
    summary_file = os.path.join(DATA_PATH, "who_conversion_summary.json")
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info("================================================================================")
    logger.info("WHO DASHBOARD DATA CONVERSION COMPLETE")
    logger.info("================================================================================")
    logger.info(f"📊 WHO countries processed: {len(WHO_TO_ISO_MAPPING)}")
    logger.info(f"🎯 MOSAIC countries updated: {countries_updated}")
    logger.info(f"📝 Metadata sources added: {total_metadata_added}")
    logger.info(f"📈 Data observations added: {total_observations_added}")
    logger.info("")
    logger.info("🎯 WHO DATA INTEGRATION BENEFITS:")
    logger.info("• Recent surveillance data (2023-2025) from official WHO dashboard")
    logger.info("• Weekly granularity for enhanced temporal resolution")
    logger.info("• High reliability Level 1 sources with confidence weight 0.9")
    logger.info("• Comprehensive coverage across 17 MOSAIC framework countries")
    logger.info("• Seamless integration with existing JHU baseline data")
    logger.info("")
    logger.info(f"📄 Conversion summary saved: {summary_file}")
    logger.info("================================================================================")

if __name__ == "__main__":
    main()