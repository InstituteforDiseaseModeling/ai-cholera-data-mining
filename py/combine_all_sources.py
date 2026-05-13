#!/usr/bin/env python3
"""
Combine All Cholera Data Sources

This script combines cholera_data_jhu.csv, cholera_data_who.csv, and cholera_data_ai.csv
into unified cholera_data.csv and metadata.csv files for dashboard and analysis use.

Usage:
    python py/combine_all_sources.py [ISO_CODE]
    python py/combine_all_sources.py  # Process all countries
"""

import pandas as pd
import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_PATH = "./data"

def load_source_data(country_iso, source_suffix):
    """Load data and metadata for a specific source."""
    
    country_path = f"{DATA_PATH}/{country_iso}"
    data_file = f"{country_path}/cholera_data_{source_suffix}.csv"
    metadata_file = f"{country_path}/metadata_{source_suffix}.csv"
    
    data_df = pd.DataFrame()
    metadata_df = pd.DataFrame()
    
    try:
        if os.path.exists(data_file):
            data_df = pd.read_csv(data_file)
            logger.debug(f"Loaded {len(data_df)} observations from {source_suffix} source")
    except Exception as e:
        logger.warning(f"Could not load {data_file}: {str(e)}")
    
    try:
        if os.path.exists(metadata_file):
            metadata_df = pd.read_csv(metadata_file)
            logger.debug(f"Loaded {len(metadata_df)} sources from {source_suffix} metadata")
    except Exception as e:
        logger.warning(f"Could not load {metadata_file}: {str(e)}")
    
    return data_df, metadata_df

def reindex_data(combined_data_df, combined_metadata_df):
    """Reindex combined data to ensure sequential indices and consistent references."""
    
    if combined_metadata_df.empty:
        return combined_data_df, combined_metadata_df
    
    # Reindex metadata sequentially
    combined_metadata_df = combined_metadata_df.reset_index(drop=True)
    combined_metadata_df['Index'] = range(1, len(combined_metadata_df) + 1)
    
    if combined_data_df.empty:
        return combined_data_df, combined_metadata_df
    
    # Create source name to new index mapping
    source_to_new_index = {}
    for idx, row in combined_metadata_df.iterrows():
        source_name = row['Source']
        new_index = row['Index']
        source_to_new_index[source_name] = new_index
    
    # Update data source_index references
    combined_data_df = combined_data_df.reset_index(drop=True)
    combined_data_df['Index'] = range(1, len(combined_data_df) + 1)
    
    # Map source names to new indices
    if 'source' in combined_data_df.columns:
        combined_data_df['source_index'] = combined_data_df['source'].map(source_to_new_index)
        
        # Handle any unmapped sources
        unmapped = combined_data_df['source_index'].isna()
        if unmapped.any():
            logger.warning(f"Found {unmapped.sum()} data rows with unmapped source references")
    
    return combined_data_df, combined_metadata_df

def combine_country_sources(country_iso):
    """Combine all data sources for a single country."""
    
    logger.info(f"Combining sources for {country_iso}")
    
    # Load all three sources
    jhu_data, jhu_metadata = load_source_data(country_iso, 'jhu')
    who_data, who_metadata = load_source_data(country_iso, 'who')
    ai_data, ai_metadata = load_source_data(country_iso, 'ai')
    
    # Combine data
    all_data = []
    all_metadata = []
    
    if not jhu_data.empty:
        all_data.append(jhu_data)
        logger.info(f"  JHU: {len(jhu_data)} observations")
    
    if not jhu_metadata.empty:
        all_metadata.append(jhu_metadata)
        logger.info(f"  JHU: {len(jhu_metadata)} sources")
    
    if not who_data.empty:
        all_data.append(who_data)
        logger.info(f"  WHO: {len(who_data)} observations")
    
    if not who_metadata.empty:
        all_metadata.append(who_metadata)
        logger.info(f"  WHO: {len(who_metadata)} sources")
    
    if not ai_data.empty:
        all_data.append(ai_data)
        logger.info(f"  AI: {len(ai_data)} observations")
    
    if not ai_metadata.empty:
        all_metadata.append(ai_metadata)
        logger.info(f"  AI: {len(ai_metadata)} sources")
    
    # Combine into single DataFrames
    if all_data:
        combined_data_df = pd.concat(all_data, ignore_index=True)
    else:
        combined_data_df = pd.DataFrame()
    
    if all_metadata:
        combined_metadata_df = pd.concat(all_metadata, ignore_index=True)
    else:
        combined_metadata_df = pd.DataFrame()
    
    # Reindex everything
    combined_data_df, combined_metadata_df = reindex_data(combined_data_df, combined_metadata_df)
    
    # Save combined files
    country_path = f"{DATA_PATH}/{country_iso}"
    
    if not combined_data_df.empty:
        combined_data_df.to_csv(f"{country_path}/cholera_data.csv", index=False)
        logger.info(f"  ✅ Combined: {len(combined_data_df)} total observations")
    
    if not combined_metadata_df.empty:
        combined_metadata_df.to_csv(f"{country_path}/metadata.csv", index=False)
        logger.info(f"  ✅ Combined: {len(combined_metadata_df)} total sources")
    
    # Summary by source
    if not combined_data_df.empty and 'source_database' in combined_data_df.columns:
        source_counts = combined_data_df['source_database'].value_counts()
        logger.info(f"  📊 Source breakdown: {dict(source_counts)}")
    
    return len(combined_data_df), len(combined_metadata_df)

def main():
    """Main function to combine sources."""
    
    logger.info("================================================================================")
    logger.info("COMBINING ALL CHOLERA DATA SOURCES")
    logger.info("================================================================================")
    
    # Check if specific country requested
    if len(sys.argv) > 1:
        country_iso = sys.argv[1].upper()
        logger.info(f"Processing single country: {country_iso}")
        
        if not os.path.exists(f"{DATA_PATH}/{country_iso}"):
            logger.error(f"Country directory not found: {DATA_PATH}/{country_iso}")
            sys.exit(1)
        
        obs_count, src_count = combine_country_sources(country_iso)
        logger.info(f"Complete: {country_iso} - {obs_count} observations, {src_count} sources")
    
    else:
        # Process all countries
        logger.info("Processing all MOSAIC framework countries...")
        
        total_obs = 0
        total_src = 0
        processed_countries = 0
        
        # Find all country directories
        if os.path.exists(DATA_PATH):
            for item in os.listdir(DATA_PATH):
                item_path = os.path.join(DATA_PATH, item)
                if os.path.isdir(item_path) and len(item) == 3 and item.isupper():
                    try:
                        obs_count, src_count = combine_country_sources(item)
                        total_obs += obs_count
                        total_src += src_count
                        processed_countries += 1
                    except Exception as e:
                        logger.error(f"Error processing {item}: {str(e)}")
        
        logger.info("================================================================================")
        logger.info(f"🎉 COMBINATION COMPLETE!")
        logger.info(f"📊 Summary: {processed_countries} countries processed")
        logger.info(f"📊 Total: {total_obs} observations, {total_src} sources combined")
        logger.info("📊 Combined files ready for dashboard and analysis use")
        logger.info("================================================================================")

if __name__ == "__main__":
    main()