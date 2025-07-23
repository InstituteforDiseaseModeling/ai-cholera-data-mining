#!/usr/bin/env python3
"""
Enhanced embed script that includes AI-mined data, WHO data, and JHU data.
This script reads all data sources and embeds them as JavaScript variables in the dashboard.
"""

import os
import json
import csv
import pandas as pd
from pathlib import Path
import re
from datetime import datetime

def read_csv_safe(file_path):
    """Read CSV file with proper error handling and encoding."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
            return content
        except Exception as e:
            print(f"Error reading {file_path} with latin-1: {e}")
            return None
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def escape_for_javascript(csv_content):
    """Escape CSV content for embedding in JavaScript template literals."""
    if not csv_content:
        return ""
    escaped = csv_content.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')
    return escaped

def get_completed_countries():
    """Get list of completed countries from completion checklist."""
    try:
        completed = []
        with open('dashboard/completion_checklist.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('status') == 'COMPLETED':
                    completed.append(row.get('iso'))
        return completed
    except Exception as e:
        print(f"Error reading completion checklist: {e}")
        return []

def get_all_countries():
    """Get list of all countries from completion checklist."""
    try:
        countries = []
        with open('dashboard/completion_checklist.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                countries.append(row.get('iso'))
        return countries
    except Exception as e:
        print(f"Error reading completion checklist: {e}")
        return []

def process_who_data():
    """Process WHO data from MOSAIC-data directory."""
    who_data = {}
    mosaic_data_path = Path("../MOSAIC-data/processed/WHO/weekly/cholera_country_weekly_processed.csv")
    
    # Try alternative path if first doesn't exist
    if not mosaic_data_path.exists():
        mosaic_data_path = Path("../../MOSAIC-data/processed/WHO/weekly/cholera_country_weekly_processed.csv")
    
    if not mosaic_data_path.exists():
        print(f"⚠️  WHO data file not found at expected path")
        return who_data
    
    try:
        print(f"📊 Processing WHO data from {mosaic_data_path}")
        df = pd.read_csv(mosaic_data_path)
        
        # Group by country and format as CSV for embedding
        for iso_code in df['iso_code'].unique():
            country_data = df[df['iso_code'] == iso_code].copy()
            
            # Sort by year and week
            country_data = country_data.sort_values(['year', 'week'])
            
            # Convert to CSV string
            csv_content = country_data.to_csv(index=False)
            who_data[iso_code] = escape_for_javascript(csv_content)
            
            print(f"✅ Processed WHO data for {iso_code} ({len(country_data)} records)")
            
    except Exception as e:
        print(f"❌ Error processing WHO data: {e}")
    
    return who_data

def process_jhu_data():
    """Process JHU data from MOSAIC-data directory."""
    jhu_data = {}
    mosaic_data_path = Path("../MOSAIC-data/processed/JHU/weekly/cholera_country_weekly_processed.csv")
    
    # Try alternative path if first doesn't exist
    if not mosaic_data_path.exists():  
        mosaic_data_path = Path("../../MOSAIC-data/processed/JHU/weekly/cholera_country_weekly_processed.csv")
    
    if not mosaic_data_path.exists():
        print(f"⚠️  JHU data file not found at expected path")
        return jhu_data
    
    try:
        print(f"📊 Processing JHU data from {mosaic_data_path}")
        df = pd.read_csv(mosaic_data_path)
        
        # Group by country and format as CSV for embedding
        for iso_code in df['iso_code'].unique():
            country_data = df[df['iso_code'] == iso_code].copy()
            
            # Sort by year and week
            country_data = country_data.sort_values(['year', 'week'])
            
            # Convert to CSV string
            csv_content = country_data.to_csv(index=False)
            jhu_data[iso_code] = escape_for_javascript(csv_content)
            
            print(f"✅ Processed JHU data for {iso_code} ({len(country_data)} records)")
            
    except Exception as e:
        print(f"❌ Error processing JHU data: {e}")
    
    return jhu_data

def embed_all_data():
    """Embed all data sources into dashboard HTML."""
    
    print("🔄 Starting comprehensive data embedding process...")
    
    # Get completed countries for AI-mined data
    completed_countries = get_completed_countries()
    print(f"📊 Found {len(completed_countries)} completed countries: {completed_countries}")
    
    # Load completion checklist data for countryData variable
    country_data = []
    try:
        with open('dashboard/completion_checklist.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('country'):  # Skip empty rows
                    country_data.append({
                        'country': row.get('country', ''),
                        'iso': row.get('iso', ''),
                        'status': row.get('status', ''),
                        'datetime': row.get('datetime', ''),
                        'sources': int(row.get('sources', 0) or 0),
                        'observations': int(row.get('observations', 0) or 0),
                        'date_range': row.get('date_range', ''),
                        'priority': row.get('priority', ''),
                        'execution_time': int(row.get('execution_time', 0) or 0),
                        'queries': int(row.get('queries', 0) or 0),
                        'yield_pct': float(row.get('yield_pct', 0) or 0),
                        'notes': row.get('notes', '')
                    })
        print(f"📊 Loaded completion data for {len(country_data)} countries")
    except Exception as e:
        print(f"❌ Error loading completion checklist: {e}")
        country_data = []
    
    # AI-mined data (existing functionality)
    ai_data = {
        'metadata': {},
        'cholera_data': {}
    }
    
    # Read AI-mined CSV files for each completed country
    for iso in completed_countries:
        data_dir = Path(f'data/{iso}')
        
        # Read metadata.csv
        metadata_file = data_dir / 'metadata.csv'
        if metadata_file.exists():
            metadata_content = read_csv_safe(metadata_file)
            if metadata_content:
                ai_data['metadata'][iso] = escape_for_javascript(metadata_content)
                lines = len(metadata_content.split('\n')) - 1
                print(f"✅ Loaded AI metadata for {iso} ({lines} sources)")
        
        # Read cholera_data.csv
        cholera_file = data_dir / 'cholera_data.csv'
        if cholera_file.exists():
            cholera_content = read_csv_safe(cholera_file)
            if cholera_content:
                ai_data['cholera_data'][iso] = escape_for_javascript(cholera_content)
                lines = len(cholera_content.split('\n')) - 1
                print(f"✅ Loaded AI cholera data for {iso} ({lines} observations)")
    
    # Process WHO and JHU data
    who_data = process_who_data()
    jhu_data = process_jhu_data()
    
    # Generate JavaScript code for embedding all data sources
    metadata_js = "{\n"
    for iso, content in ai_data['metadata'].items():
        metadata_js += f'        "{iso}": `{content}`,\n'
    metadata_js += "    }"
    
    cholera_data_js = "{\n"
    for iso, content in ai_data['cholera_data'].items():
        cholera_data_js += f'        "{iso}": `{content}`,\n'
    cholera_data_js += "    }"
    
    who_data_js = "{\n"
    for iso, content in who_data.items():
        who_data_js += f'        "{iso}": `{content}`,\n'
    who_data_js += "    }"
    
    jhu_data_js = "{\n"
    for iso, content in jhu_data.items():
        jhu_data_js += f'        "{iso}": `{content}`,\n'
    jhu_data_js += "    }"
    
    # Generate country data JavaScript
    country_data_json = json.dumps(country_data, indent=8)
    
    js_code = f"""        // Embedded CSV data - updated automatically by py/embed_all_data.py
        const countryData = {country_data_json};
        
        const embeddedMetadata = {metadata_js};
        
        const embeddedCholeraData = {cholera_data_js};
        
        const embeddedWHOData = {who_data_js};
        
        const embeddedJHUData = {jhu_data_js};
        
"""
    
    # Read current dashboard HTML
    dashboard_file = Path('dashboard/dashboard.html')
    print(f"📄 Reading dashboard HTML from {dashboard_file}")
    
    with open(dashboard_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Find and replace existing embedded data section
    embed_start_marker = "        // Embedded CSV data - updated automatically by py/"
    embed_end_marker = "        // Embedded week counts data"
    
    embed_start = html_content.find(embed_start_marker)
    if embed_start != -1:
        print("🔄 Replacing existing embedded data...")
        # Find the end of the embedded data section
        search_start = embed_start
        embed_end = html_content.find(embed_end_marker, search_start)
        
        if embed_end == -1:
            print("❌ Could not find end of embedded data section")
            return False
            
        new_content = (
            html_content[:embed_start] +
            js_code + "\n        " +
            html_content[embed_end:]
        )
    else:
        # No existing embedded data, find insertion point
        csvdata_marker = "        const weekCountsCSV = `"
        csvdata_pos = html_content.find(csvdata_marker)
        if csvdata_pos == -1:
            print("❌ Could not find insertion point in dashboard HTML")
            return False
        
        new_content = (
            html_content[:csvdata_pos] +
            js_code + "\n        " +
            html_content[csvdata_pos:]
        )
    
    # Write updated HTML
    print(f"💾 Writing updated dashboard HTML...")
    with open(dashboard_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    # Calculate statistics
    total_metadata_sources = sum(len(content.split('\n')) - 1 for content in ai_data['metadata'].values())
    total_cholera_observations = sum(len(content.split('\n')) - 1 for content in ai_data['cholera_data'].values())
    total_who_records = sum(len(content.split('\n')) - 1 for content in who_data.values())
    total_jhu_records = sum(len(content.split('\n')) - 1 for content in jhu_data.values())
    
    print(f"\n🎉 Successfully embedded all data sources into dashboard!")
    print(f"📈 Summary:")
    print(f"   • AI-mined data: {len(completed_countries)} countries, {total_metadata_sources} sources, {total_cholera_observations} observations")
    print(f"   • WHO data: {len(who_data)} countries, {total_who_records} weekly records")
    print(f"   • JHU data: {len(jhu_data)} countries, {total_jhu_records} weekly records")
    print(f"   • Dashboard updated: {dashboard_file}")
    
    return True

if __name__ == "__main__":
    # Change to the project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    print(f"🏠 Working directory: {Path.cwd()}")
    
    success = embed_all_data()
    if success:
        print(f"\n✨ Comprehensive data embedding completed successfully!")
        print(f"🌐 All dashboard tabs should now display real data.")
    else:
        print(f"\n❌ Data embedding failed!")
        exit(1)