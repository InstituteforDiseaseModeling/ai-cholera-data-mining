#!/usr/bin/env python3
"""
Simplify Metadata Column Structure

Removes unnecessary columns from metadata.csv files and converts reliability_level to integer.

Columns to remove:
- Data_Type
- Status  
- Validation_Status
- Search_Technique
- Citation_Depth
- Cross_References
- Discovery_Method

Columns to keep:
- Index
- Source
- URL
- Description  
- Date_Range
- Reliability_Level (convert to integer: Level 1 -> 1, Level 2 -> 2, etc.)
- Language_Original
- source_database

Usage:
    python py/simplify_metadata_columns.py
"""

import pandas as pd
import os
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DATA_PATH = "./data"

def convert_reliability_level(reliability_str):
    """Convert reliability level string to integer."""
    if pd.isna(reliability_str):
        return None
    
    # Extract number from "Level X" format
    match = re.search(r'Level (\d+)', str(reliability_str))
    if match:
        return int(match.group(1))
    
    # Handle direct integer values
    try:
        return int(reliability_str)
    except:
        logger.warning(f"Could not parse reliability level: {reliability_str}, defaulting to 2")
        return 2

def simplify_metadata_file(file_path):
    """Simplify a single metadata.csv file."""
    try:
        df = pd.read_csv(file_path)
        logger.info(f"  Processing {file_path} - {len(df)} rows, {len(df.columns)} columns")
        
        # Define columns to keep (in desired order)
        columns_to_keep = [
            'Index',
            'Source', 
            'URL',
            'Description',
            'Date_Range',
            'Reliability_Level',
            'Language_Original',
            'source_database'
        ]
        
        # Check which columns exist
        existing_columns = []
        for col in columns_to_keep:
            if col in df.columns:
                existing_columns.append(col)
            else:
                logger.warning(f"    Column '{col}' not found in {file_path}")
        
        # Select only existing columns
        df_simplified = df[existing_columns].copy()
        
        # Convert reliability level to integer
        if 'Reliability_Level' in df_simplified.columns:
            df_simplified['Reliability_Level'] = df_simplified['Reliability_Level'].apply(convert_reliability_level)
        
        # Save simplified file
        df_simplified.to_csv(file_path, index=False)
        
        logger.info(f"    ✅ Simplified: {len(df_simplified)} rows, {len(df_simplified.columns)} columns")
        logger.info(f"    Kept columns: {list(df_simplified.columns)}")
        
        return True
        
    except Exception as e:
        logger.error(f"    ❌ Error processing {file_path}: {str(e)}")
        return False

def main():
    """Simplify all metadata.csv files."""
    
    logger.info("================================================================================")
    logger.info("SIMPLIFYING METADATA COLUMN STRUCTURE")
    logger.info("================================================================================")
    logger.info("Removing unnecessary columns and converting reliability_level to integer...")
    logger.info("")
    
    logger.info("📋 COLUMNS TO REMOVE:")
    logger.info("• Data_Type, Status, Validation_Status") 
    logger.info("• Search_Technique, Citation_Depth, Cross_References, Discovery_Method")
    logger.info("")
    logger.info("📋 COLUMNS TO KEEP:")
    logger.info("• Index, Source, URL, Description, Date_Range")
    logger.info("• Reliability_Level (converted to integer), Language_Original, source_database")
    logger.info("")
    
    if not os.path.exists(DATA_PATH):
        logger.error("❌ Data directory not found")
        return
    
    # Get all country directories
    country_dirs = [d for d in os.listdir(DATA_PATH) if os.path.isdir(os.path.join(DATA_PATH, d)) and len(d) == 3]
    country_dirs.sort()
    
    success_count = 0
    total_countries = len(country_dirs)
    
    logger.info(f"Processing {total_countries} country directories...")
    logger.info("")
    
    for country_iso in country_dirs:
        logger.info(f"Processing {country_iso}...")
        country_path = os.path.join(DATA_PATH, country_iso)
        
        metadata_file = os.path.join(country_path, "metadata.csv")
        if os.path.exists(metadata_file):
            if simplify_metadata_file(metadata_file):
                success_count += 1
        else:
            logger.warning(f"  ⚠️  metadata.csv not found in {country_path}")
        
        logger.info("")
    
    logger.info("================================================================================")
    logger.info("METADATA SIMPLIFICATION COMPLETE")
    logger.info("================================================================================")
    logger.info(f"📊 Countries processed: {total_countries}")
    logger.info(f"✅ Files successfully updated: {success_count}")
    logger.info("")
    logger.info("🎯 SIMPLIFICATION BENEFITS:")
    logger.info("• Reduced file size and complexity")
    logger.info("• Cleaner data structure for analysis")
    logger.info("• Integer reliability levels for easier processing")
    logger.info("• Maintained essential metadata for data provenance")
    logger.info("• Improved readability and maintenance")
    logger.info("")
    logger.info("📋 FINAL COLUMN STRUCTURE:")
    logger.info("1. Index (integer) - Sequential reference number")
    logger.info("2. Source (text) - Source name/description")
    logger.info("3. URL (text) - Source URL or reference")
    logger.info("4. Description (text) - Detailed source description")
    logger.info("5. Date_Range (text) - Date range covered by source")
    logger.info("6. Reliability_Level (integer) - 1=highest, 2=high, 3=medium, 4=low")
    logger.info("7. Language_Original (text) - Original language of source")
    logger.info("8. source_database (text) - JHU, WHO, or AI")
    logger.info("================================================================================")

if __name__ == "__main__":
    main()