#!/usr/bin/env python3
"""
Update Metadata Format - Remove Language_Original and Split Date_Range

This script updates all existing metadata.csv files to:
1. Remove the Language_Original column
2. Split Date_Range into TL and TR columns

Usage:
    python py/update_metadata_format.py
"""

import pandas as pd
import os
import re
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DATA_PATH = "./data"

def split_date_range(date_range):
    """Split date range string into TL and TR dates."""
    if pd.isna(date_range) or not date_range:
        return None, None
    
    # Handle various date range formats
    date_range = str(date_range).strip()
    
    # Common patterns: "YYYY-MM-DD to YYYY-MM-DD", "YYYY-MM-DD - YYYY-MM-DD"
    patterns = [
        r'(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})',
        r'(\d{4}-\d{2}-\d{2})\s*-\s*(\d{4}-\d{2}-\d{2})',
        r'(\d{4}-\d{2}-\d{2})\s*–\s*(\d{4}-\d{2}-\d{2})',  # em dash
        r'(\d{4}-\d{2}-\d{2})\s*,\s*(\d{4}-\d{2}-\d{2})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, date_range)
        if match:
            return match.group(1), match.group(2)
    
    # If only one date found, use it for both TL and TR
    single_date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_range)
    if single_date_match:
        date = single_date_match.group(1)
        return date, date
    
    logger.warning(f"Could not parse date range: {date_range}")
    return None, None

def update_metadata_file(file_path):
    """Update a single metadata.csv file."""
    try:
        df = pd.read_csv(file_path)
        logger.info(f"Processing {file_path} - Original columns: {list(df.columns)}")
        
        # Check if we need to update
        needs_update = False
        
        # Remove Language_Original column if it exists
        if 'Language_Original' in df.columns:
            df = df.drop('Language_Original', axis=1)
            needs_update = True
            logger.info(f"  ✅ Removed Language_Original column")
        
        # Split Date_Range into TL and TR if Date_Range exists
        if 'Date_Range' in df.columns:
            # Split date ranges
            tl_tr_data = df['Date_Range'].apply(split_date_range)
            df['TL'] = [item[0] for item in tl_tr_data]
            df['TR'] = [item[1] for item in tl_tr_data]
            
            # Remove the original Date_Range column
            df = df.drop('Date_Range', axis=1)
            needs_update = True
            logger.info(f"  ✅ Split Date_Range into TL and TR columns")
        
        # Ensure correct column order
        expected_columns = ['Index', 'Source', 'URL', 'Description', 'TL', 'TR', 'Reliability_Level', 'source_database']
        
        # Add any missing columns with default values
        for col in expected_columns:
            if col not in df.columns:
                if col == 'source_database':
                    df[col] = 'JHU'  # Default to JHU for existing data
                elif col in ['TL', 'TR']:
                    df[col] = None
                elif col == 'Reliability_Level':
                    df[col] = 2  # Default reliability level
                else:
                    df[col] = ''
        
        # Reorder columns to match expected format
        df = df[expected_columns]
        
        if needs_update:
            # Save updated file
            df.to_csv(file_path, index=False)
            logger.info(f"  ✅ Updated {file_path} - New columns: {list(df.columns)}")
            return True
        else:
            logger.info(f"  ℹ️  No updates needed for {file_path}")
            return False
        
    except Exception as e:
        logger.error(f"  ❌ Error updating {file_path}: {str(e)}")
        return False

def main():
    """Update all metadata.csv files."""
    
    logger.info("================================================================================")
    logger.info("UPDATING METADATA FORMAT - REMOVE LANGUAGE_ORIGINAL AND SPLIT DATE_RANGE")
    logger.info("================================================================================")
    logger.info("Updating all metadata.csv files to new simplified format...")
    logger.info("")
    
    if not os.path.exists(DATA_PATH):
        logger.error("❌ Data directory not found")
        return
    
    # Get all country directories
    country_dirs = [d for d in os.listdir(DATA_PATH) if os.path.isdir(os.path.join(DATA_PATH, d)) and len(d) == 3]
    country_dirs.sort()
    
    updated_count = 0
    total_processed = 0
    
    logger.info(f"Processing {len(country_dirs)} country directories...")
    logger.info("")
    
    for country_iso in country_dirs:
        logger.info(f"Processing {country_iso}...")
        country_path = os.path.join(DATA_PATH, country_iso)
        metadata_file = os.path.join(country_path, "metadata.csv")
        
        if os.path.exists(metadata_file):
            total_processed += 1
            if update_metadata_file(metadata_file):
                updated_count += 1
        else:
            logger.warning(f"  ⚠️  metadata.csv not found in {country_path}")
        
        logger.info("")
    
    logger.info("================================================================================")
    logger.info("METADATA FORMAT UPDATE COMPLETE")
    logger.info("================================================================================")
    logger.info(f"📊 Countries processed: {len(country_dirs)}")
    logger.info(f"📁 Metadata files found: {total_processed}")
    logger.info(f"✅ Files updated: {updated_count}")
    logger.info(f"ℹ️  Files unchanged: {total_processed - updated_count}")
    logger.info("")
    logger.info("🎯 NEW METADATA FORMAT:")
    logger.info("• Index, Source, URL, Description, TL, TR, Reliability_Level, source_database")
    logger.info("• Language_Original column removed (not needed for core functionality)")
    logger.info("• Date_Range split into TL (start date) and TR (end date) for consistency")
    logger.info("• Reliability_Level uses integer values (1, 2, 3, 4)")
    logger.info("")
    logger.info("📈 BENEFITS:")
    logger.info("• Consistent date format with cholera_data.csv (TL/TR columns)")
    logger.info("• Reduced file size and simplified structure")
    logger.info("• Better alignment with data processing workflows")
    logger.info("• Cleaner metadata management")
    logger.info("================================================================================")

if __name__ == "__main__":
    main()