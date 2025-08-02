#!/usr/bin/env python3
"""
Add source_database Column to Existing Data Files

This script adds the source_database column to all existing metadata.csv and cholera_data.csv files,
ensuring proper data provenance tracking for JHU, WHO, and AI-mined data.

Usage:
    python py/add_source_database_column.py
"""

import pandas as pd
import os
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DATA_PATH = "./data"

def add_source_database_to_metadata(file_path):
    """Add source_database column to metadata.csv file."""
    try:
        df = pd.read_csv(file_path)
        
        # Check if source_database column already exists
        if 'source_database' in df.columns:
            logger.info(f"  source_database column already exists in {file_path}")
            return True
        
        # Determine source_database based on existing data
        def determine_source_database(row):
            source = str(row.get('Source', '')).lower()
            discovery_method = str(row.get('Discovery_Method', '')).lower()
            validation_status = str(row.get('Validation_Status', '')).lower()
            
            # JHU database entries
            if 'jhu' in source or 'jhu' in discovery_method or 'jhu' in validation_status:
                return 'JHU'
            
            # WHO dashboard entries
            if 'who annual' in source or 'who afro' in source or 'who surveillance' in source:
                return 'WHO'
            
            # AI mined entries (default for new discoveries)
            return 'AI'
        
        # Add source_database column
        df['source_database'] = df.apply(determine_source_database, axis=1)
        
        # Save updated file
        df.to_csv(file_path, index=False)
        logger.info(f"  ✅ Added source_database column to {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Error updating {file_path}: {str(e)}")
        return False

def add_source_database_to_cholera_data(file_path):
    """Add source_database column to cholera_data.csv file."""
    try:
        df = pd.read_csv(file_path)
        
        # Check if source_database column already exists
        if 'source_database' in df.columns:
            logger.info(f"  source_database column already exists in {file_path}")
            return True
        
        # Determine source_database based on existing data
        def determine_source_database(row):
            source = str(row.get('source', '')).lower()
            processing_notes = str(row.get('processing_notes', '')).lower()
            
            # JHU database entries
            if 'jhu' in source or 'jhu' in processing_notes:
                return 'JHU'
            
            # WHO dashboard entries  
            if 'who annual' in source or 'who afro' in source or 'who surveillance' in source:
                return 'WHO'
            
            # AI mined entries (default for new discoveries)
            return 'AI'
        
        # Add source_database column
        df['source_database'] = df.apply(determine_source_database, axis=1)
        
        # Save updated file
        df.to_csv(file_path, index=False)
        logger.info(f"  ✅ Added source_database column to {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Error updating {file_path}: {str(e)}")
        return False

def main():
    """Add source_database column to all existing data files."""
    
    logger.info("================================================================================")
    logger.info("ADDING SOURCE_DATABASE COLUMN TO EXISTING DATA FILES")
    logger.info("================================================================================")
    logger.info("Adding data provenance tracking for JHU, WHO, and AI-mined sources...")
    logger.info("")
    
    if not os.path.exists(DATA_PATH):
        logger.error("❌ Data directory not found")
        return
    
    # Get all country directories
    country_dirs = [d for d in os.listdir(DATA_PATH) if os.path.isdir(os.path.join(DATA_PATH, d)) and len(d) == 3]
    country_dirs.sort()
    
    metadata_success = 0
    cholera_data_success = 0
    total_countries = len(country_dirs)
    
    logger.info(f"Processing {total_countries} country directories...")
    logger.info("")
    
    for country_iso in country_dirs:
        logger.info(f"Processing {country_iso}...")
        country_path = os.path.join(DATA_PATH, country_iso)
        
        # Update metadata.csv
        metadata_file = os.path.join(country_path, "metadata.csv")
        if os.path.exists(metadata_file):
            if add_source_database_to_metadata(metadata_file):
                metadata_success += 1
        else:
            logger.warning(f"  ⚠️  metadata.csv not found in {country_path}")
        
        # Update cholera_data.csv
        cholera_data_file = os.path.join(country_path, "cholera_data.csv")
        if os.path.exists(cholera_data_file):
            if add_source_database_to_cholera_data(cholera_data_file):
                cholera_data_success += 1
        else:
            logger.warning(f"  ⚠️  cholera_data.csv not found in {country_path}")
        
        logger.info("")
    
    logger.info("================================================================================")
    logger.info("SOURCE_DATABASE COLUMN ADDITION COMPLETE")
    logger.info("================================================================================")
    logger.info(f"📊 Countries processed: {total_countries}")
    logger.info(f"✅ metadata.csv files updated: {metadata_success}")
    logger.info(f"✅ cholera_data.csv files updated: {cholera_data_success}")
    logger.info("")
    logger.info("🎯 SOURCE_DATABASE VALUES:")
    logger.info("• 'JHU' - Data from JHU cholera database baseline")
    logger.info("• 'WHO' - Data from WHO surveillance dashboards")
    logger.info("• 'AI' - Data discovered through AI agent searches")
    logger.info("")
    logger.info("📈 BENEFITS:")
    logger.info("• Clear data provenance tracking")
    logger.info("• Enhanced quality control and validation")
    logger.info("• Better understanding of data source contributions")
    logger.info("• Improved dashboard analytics and reporting")
    logger.info("================================================================================")

if __name__ == "__main__":
    main()