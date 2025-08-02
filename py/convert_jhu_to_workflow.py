#!/usr/bin/env python3
"""
JHU Cholera Database to AI Workflow Format Converter (Fixed Version)

This script converts JHU cholera database format to the enhanced AI workflow format
compatible with the MOSAIC framework requirements.

Handles variable JHU file formats and column structures robustly.
"""

import pandas as pd
import os
import json
from pathlib import Path
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
JHU_DATA_PATH = "/Users/johngiles/OneDrive/Projects/MOSAIC/jhu_cholera_data/data"
OUTPUT_DATA_PATH = "./data"
REFERENCE_PATH = "./reference"

# Country ISO code mapping for MOSAIC framework countries only
COUNTRY_ISO_MAPPING = {
    'Angola': 'AGO',
    'Benin': 'BEN', 
    'Botswana': 'BWA',
    'Burkina Faso': 'BFA',
    'Burundi': 'BDI',
    'Cameroon': 'CMR',
    'Central African Republic': 'CAF',
    'Chad': 'TCD',
    'Cote d\'Ivoire': 'CIV',  
    'Democratic Republic of the Congo': 'COD',
    'Equatorial Guinea': 'GNQ',
    'Eritrea': 'ERI',
    'Ethiopia': 'ETH',
    'Gabon': 'GAB',
    'Gambia': 'GMB',
    'Ghana': 'GHA',
    'Guinea': 'GIN',
    'Guinea-Bissau': 'GNB',
    'Kenya': 'KEN',
    'Liberia': 'LBR',
    'Mali': 'MLI',
    'Mauritania': 'MRT',
    'Mozambique': 'MOZ',
    'Namibia': 'NAM',
    'Niger': 'NER',
    'Nigeria': 'NGA',
    'Rwanda': 'RWA',
    'Senegal': 'SEN',
    'Sierra Leone': 'SLE',
    'Somalia': 'SOM',
    'South Africa': 'ZAF',
    'South Sudan': 'SSD',
    'Eswatini': 'SWZ',  # Note: JHU might use 'Swaziland'
    'Tanzania': 'TZA',
    'Togo': 'TGO',
    'Uganda': 'UGA',
    'Zambia': 'ZMB',
    'Zimbabwe': 'ZWE'
}

def get_jhu_confidence_weight(primary_flag, phantom_flag, source_tags):
    """
    Assign confidence weights based on JHU data quality indicators.
    
    JHU data is generally high quality (Level 1-2), but we differentiate based on:
    - Primary vs non-primary data
    - Phantom flag indicating potential data quality issues
    - Source tags (WHOannual, WHOafro, UNICEFcp, etc.)
    """
    
    # Start with high baseline for JHU data
    base_weight = 0.95
    
    # Adjust based on flags
    if phantom_flag:
        base_weight *= 0.7  # Phantom data has quality concerns
    
    if not primary_flag:
        base_weight *= 0.9  # Non-primary slightly lower confidence
    
    # Adjust based on source tags
    if source_tags:
        if 'WHOannual' in source_tags:
            base_weight = min(base_weight * 1.05, 1.0)  # WHO annual is highest quality
        elif 'WHOafro' in source_tags:
            base_weight = min(base_weight * 1.02, 1.0)  # WHO AFRO also high quality
        elif 'UNICEFcp' in source_tags:
            base_weight *= 0.95  # UNICEF good but slightly lower than WHO
    
    return round(min(base_weight, 1.0), 2)

def safe_get_value(obs_row, col_name, default=None):
    """Safely extract a value from observation row, handling missing columns and empty values."""
    if col_name not in obs_row.index:
        return default
    
    val = obs_row[col_name]
    if pd.isna(val) or val == '' or val == '""' or val == "''":
        return default
    return val

def safe_numeric_convert(value):
    """Safely convert value to numeric, handling various string representations."""
    if value is None:
        return None
    
    try:
        # Handle string representations
        if isinstance(value, str):
            value = value.strip().replace('"', '').replace("'", '')
            if value == '' or value.lower() in ['nan', 'na', 'null', 'none']:
                return None
        
        # Convert to float first, then int if it's a whole number
        num_val = float(value)
        if num_val.is_integer():
            return int(num_val)
        return num_val
        
    except (ValueError, TypeError, AttributeError):
        return None

def convert_jhu_observation_to_workflow(obs_row, metadata_df, country_iso, source_index_start):
    """
    Convert a single JHU observation row to AI workflow format.
    
    Handles variable JHU formats robustly.
    """
    
    # Get core values with robust handling
    location = safe_get_value(obs_row, 'Location', '')
    tl = safe_get_value(obs_row, 'TL', '')
    tr = safe_get_value(obs_row, 'TR', '')
    primary = safe_get_value(obs_row, 'Primary', True)
    phantom = safe_get_value(obs_row, 'Phantom', False)
    
    # Handle deaths and cases with robust numeric conversion
    deaths = safe_numeric_convert(safe_get_value(obs_row, 'deaths'))
    sch = safe_numeric_convert(safe_get_value(obs_row, 'sCh'))
    
    # Try to get confirmed cases if available (some JHU files have extended columns)
    cch = None
    for col in ['cCh', 'cCh_RDT', 'cCh_PCR']:
        if col in obs_row.index:
            cch = safe_numeric_convert(safe_get_value(obs_row, col))
            if cch is not None:
                break
    
    # Calculate CFR if possible
    cfr = None
    if deaths is not None and sch is not None and sch > 0:
        cfr = round((deaths / sch) * 100, 1)
    
    # Use TR as reporting date for JHU data (end of observation period)
    reporting_date = tr
    
    # Generate processing notes
    processing_notes = f"Converted from JHU database. Primary: {primary}, Phantom: {phantom}"
    if deaths is not None and sch is not None:
        processing_notes += f" - JHU reported {sch} cases, {deaths} deaths"
    elif sch is not None:
        processing_notes += f" - JHU reported {sch} cases"
    elif deaths is not None:
        processing_notes += f" - JHU reported {deaths} deaths"
    
    # Handle zero transmission periods (phantom data with 0 cases)
    if phantom and (sch is None or sch == 0):
        processing_notes += " - Zero transmission period validated by JHU"
    
    # Skip rows with no meaningful data
    if location == '' or tl == '' or tr == '' or (deaths is None and sch is None):
        return None
    
    return {
        'Location': location,  # Already in AFR::ISO format
        'TL': tl,
        'TR': tr, 
        'deaths': deaths if deaths is not None else '',
        'sCh': sch if sch is not None else '',
        'cCh': cch if cch is not None else '',
        'CFR': cfr if cfr is not None else '',
        'reporting_date': reporting_date,
        'source_index': source_index_start,  # Will be updated with actual metadata index
        'source': 'JHU Cholera Database',  # Will be updated with specific source
        'confidence_weight': get_jhu_confidence_weight(primary, phantom, ''),
        'processing_notes': processing_notes,
        'source_database': 'JHU'
    }

def convert_jhu_metadata_to_workflow(jhu_metadata_df, country_name):
    """
    Convert JHU metadata to AI workflow metadata format.
    """
    
    workflow_metadata = []
    
    for idx, row in jhu_metadata_df.iterrows():
        # Extract source information from UID and Tags
        uid = row['UID']
        tags = row['Tags'] if pd.notna(row['Tags']) else ''
        
        # Determine source name based on tags
        if 'WHOannual' in tags:
            source_name = f"WHO Annual Cholera Report (UID: {uid})"
        elif 'WHOafro' in tags:
            source_name = f"WHO AFRO Surveillance Report (UID: {uid})"
        elif 'UNICEFcp' in tags:
            source_name = f"UNICEF Country Programme Report (UID: {uid})"
        else:
            source_name = f"JHU Cholera Database (UID: {uid})"
        
        # Date range
        date_range = f"{row['Earliest observation']} to {row['Latest observation']}"
        
        # Description
        description = f"JHU cholera database entry with {row['# of observations']} observations. Frequency: {row['Observation Frequency']}. Updated: {row['Updated On']}"
        if tags:
            description += f" Source tags: {tags}"
        
        # Reliability level based on source tags
        if 'WHOannual' in tags or 'WHOafro' in tags:
            reliability_level = 'Level 1'
        elif 'UNICEFcp' in tags:
            reliability_level = 'Level 2'
        else:
            reliability_level = 'Level 2'  # JHU data is generally high quality
        
        workflow_metadata.append({
            'Index': idx + 1,  # Sequential indexing starting from 1
            'Source': source_name,
            'URL': f"https://github.com/InstituteforDiseaseModeling/jhu_cholera_data/blob/main/data/{country_name}/ObservationCollection{uid}.csv",
            'Description': description,
            'Date_Range': date_range,
            'Data_Type': 'Surveillance',
            'Status': 'Validated',
            'Reliability_Level': reliability_level,
            'Validation_Status': 'JHU_Integrated',
            'Search_Technique': 'Database_Import',
            'Language_Original': 'English',
            'Citation_Depth': 'Primary',
            'Cross_References': 'JHU_Database',
            'Discovery_Method': 'JHU_Integration',
            'source_database': 'JHU'
        })
    
    return workflow_metadata

def process_country(country_name, country_iso):
    """Process a single country's JHU data and convert to workflow format."""
    
    logger.info(f"Processing {country_name} ({country_iso})")
    
    # Paths
    jhu_country_path = f"{JHU_DATA_PATH}/{country_name}"
    output_country_path = f"{OUTPUT_DATA_PATH}/{country_iso}"
    
    # Check if JHU data exists
    if not os.path.exists(jhu_country_path):
        logger.warning(f"JHU data not found for {country_name}")
        return False
    
    # Create output directory
    os.makedirs(output_country_path, exist_ok=True)
    
    try:
        # Load JHU metadata
        jhu_metadata_path = f"{jhu_country_path}/metadata.csv"
        if not os.path.exists(jhu_metadata_path):
            logger.warning(f"No metadata found for {country_name}")
            return False
            
        jhu_metadata_df = pd.read_csv(jhu_metadata_path)
        logger.info(f"Found {len(jhu_metadata_df)} metadata entries for {country_name}")
        
        # Convert metadata to workflow format
        workflow_metadata = convert_jhu_metadata_to_workflow(jhu_metadata_df, country_name)
        
        # Process all observation files
        workflow_data = []
        observation_files = [f for f in os.listdir(jhu_country_path) if f.startswith('ObservationCollection') and f.endswith('.csv')]
        
        for obs_file in observation_files:
            # Extract UID from filename
            uid = obs_file.replace('ObservationCollection', '').replace('.csv', '')
            
            try:
                # Find corresponding metadata entry
                metadata_entry = jhu_metadata_df[jhu_metadata_df['UID'] == int(uid)]
                if metadata_entry.empty:
                    logger.warning(f"No metadata found for {obs_file}")
                    continue
                    
                metadata_index = metadata_entry.index[0] + 1  # 1-based indexing
                
                # Load observation data with robust error handling
                try:
                    obs_df = pd.read_csv(f"{jhu_country_path}/{obs_file}")
                except Exception as e:
                    logger.warning(f"Could not read {obs_file}: {str(e)}")
                    continue
                
                # Convert each observation
                for _, obs_row in obs_df.iterrows():
                    workflow_obs = convert_jhu_observation_to_workflow(obs_row, jhu_metadata_df, country_iso, metadata_index)
                    
                    if workflow_obs is None:  # Skip rows with no meaningful data
                        continue
                    
                    # Update source information from metadata
                    workflow_obs['source_index'] = metadata_index
                    workflow_obs['source'] = workflow_metadata[metadata_index - 1]['Source']
                    
                    # Update confidence weight based on metadata tags
                    tags = metadata_entry.iloc[0]['Tags'] if pd.notna(metadata_entry.iloc[0]['Tags']) else ''
                    workflow_obs['confidence_weight'] = get_jhu_confidence_weight(
                        workflow_obs['Location'] != '' and workflow_obs['TL'] != '',  # Use data completeness as primary indicator
                        safe_get_value(obs_row, 'Phantom', False), 
                        tags
                    )
                    
                    workflow_data.append(workflow_obs)
                    
            except Exception as e:
                logger.warning(f"Error processing {obs_file}: {str(e)}")
                continue
        
        # Create workflow DataFrames
        if not workflow_data:
            logger.warning(f"No valid data converted for {country_name}")
            return False
            
        workflow_data_df = pd.DataFrame(workflow_data)
        workflow_metadata_df = pd.DataFrame(workflow_metadata)
        
        # Add Index column to data (sequential numbering)
        workflow_data_df.insert(0, 'Index', range(1, len(workflow_data_df) + 1))
        
        # Save to CSV files
        workflow_data_df.to_csv(f"{output_country_path}/cholera_data.csv", index=False)
        workflow_metadata_df.to_csv(f"{output_country_path}/metadata.csv", index=False)
        
        logger.info(f"Successfully converted {country_name}: {len(workflow_data_df)} observations, {len(workflow_metadata_df)} sources")
        return True
        
    except Exception as e:
        logger.error(f"Error processing {country_name}: {str(e)}")
        return False

def main():
    """Main conversion process."""
    
    logger.info("Starting JHU to AI Workflow conversion (Fixed Version)")
    logger.info(f"JHU data path: {JHU_DATA_PATH}")
    logger.info(f"Output path: {OUTPUT_DATA_PATH}")
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DATA_PATH, exist_ok=True)
    
    # Process each MOSAIC framework country
    success_count = 0
    total_count = 0
    successful_countries = []
    failed_countries = []
    
    for country_name, country_iso in COUNTRY_ISO_MAPPING.items():
        total_count += 1
        if process_country(country_name, country_iso):
            success_count += 1
            successful_countries.append(f"{country_name} ({country_iso})")
        else:
            failed_countries.append(f"{country_name} ({country_iso})")
    
    logger.info(f"Conversion complete: {success_count}/{total_count} countries processed successfully")
    logger.info(f"Successful: {', '.join(successful_countries)}")
    if failed_countries:
        logger.info(f"Failed: {', '.join(failed_countries)}")
    
    # Generate summary report
    summary = {
        'conversion_date': datetime.now().isoformat(),
        'total_countries': total_count,
        'successful_conversions': success_count,
        'failed_conversions': total_count - success_count,
        'successful_countries': successful_countries,
        'failed_countries': failed_countries,
        'source': 'JHU Cholera Database',
        'conversion_script': 'py/convert_jhu_to_workflow_fixed.py'
    }
    
    with open(f"{OUTPUT_DATA_PATH}/jhu_conversion_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info("JHU conversion summary saved to data/jhu_conversion_summary.json")

if __name__ == "__main__":
    main()