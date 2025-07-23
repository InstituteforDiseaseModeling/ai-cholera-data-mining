#!/usr/bin/env python3
"""
Embed CSV data directly into the dashboard HTML file to avoid CORS issues.
This script reads all completed countries' metadata.csv and cholera_data.csv files
and embeds them as JavaScript variables in the dashboard.
"""

import os
import json
import csv
from pathlib import Path
import re

def read_csv_safe(file_path):
    """Read CSV file with proper error handling and encoding."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except UnicodeDecodeError:
        # Try with different encoding
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
    # Escape backticks and backslashes for template literals
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

def embed_csv_data():
    """Embed CSV data for all completed countries into dashboard HTML."""
    
    print("🔄 Starting CSV data embedding process...")
    
    # Get completed countries
    completed_countries = get_completed_countries()
    print(f"📊 Found {len(completed_countries)} completed countries: {completed_countries}")
    
    # Dictionary to store all CSV data
    embedded_data = {
        'metadata': {},
        'cholera_data': {}
    }
    
    # Read CSV files for each completed country
    for iso in completed_countries:
        data_dir = Path(f'data/{iso}')
        
        # Read metadata.csv
        metadata_file = data_dir / 'metadata.csv'
        if metadata_file.exists():
            metadata_content = read_csv_safe(metadata_file)
            if metadata_content:
                embedded_data['metadata'][iso] = escape_for_javascript(metadata_content)
                lines = len(metadata_content.split('\n')) - 1  # -1 for header
                print(f"✅ Loaded metadata for {iso} ({lines} sources)")
            else:
                print(f"⚠️  Failed to read metadata for {iso}")
        else:
            print(f"⚠️  No metadata.csv found for {iso}")
        
        # Read cholera_data.csv
        cholera_file = data_dir / 'cholera_data.csv'
        if cholera_file.exists():
            cholera_content = read_csv_safe(cholera_file)
            if cholera_content:
                embedded_data['cholera_data'][iso] = escape_for_javascript(cholera_content)
                lines = len(cholera_content.split('\n')) - 1  # -1 for header
                print(f"✅ Loaded cholera data for {iso} ({lines} observations)")
            else:
                print(f"⚠️  Failed to read cholera data for {iso}")
        else:
            print(f"⚠️  No cholera_data.csv found for {iso}")
    
    # Generate JavaScript code for embedding
    metadata_js = "{\n"
    for iso, content in embedded_data['metadata'].items():
        metadata_js += f'        "{iso}": `{content}`,\n'
    metadata_js += "    }"
    
    cholera_data_js = "{\n"
    for iso, content in embedded_data['cholera_data'].items():
        cholera_data_js += f'        "{iso}": `{content}`,\n'
    cholera_data_js += "    }"
    
    js_code = f"""        // Embedded CSV data - updated automatically by py/embed_csv_data.py
        const embeddedMetadata = {metadata_js};
        
        const embeddedCholeraData = {cholera_data_js};
        
"""
    
    # Read current dashboard HTML
    dashboard_file = Path('dashboard/dashboard.html')
    print(f"📄 Reading dashboard HTML from {dashboard_file}")
    
    with open(dashboard_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Find the location to insert the embedded data
    # Look for the existing embedded data section and replace it
    start_marker = "        // Embedded CSV data - updated automatically by the Python script"
    end_marker = "        let countryData = [];"
    
    start_pos = html_content.find(start_marker)
    if start_pos == -1:
        # Try alternative marker
        start_marker = "        // Embedded CSV data - updated automatically by py/embed_csv_data.py"
        start_pos = html_content.find(start_marker)
    
    if start_pos == -1:
        print("❌ Could not find insertion point in dashboard HTML")
        print("Looking for marker:", start_marker)
        return False
    
    # Insert the embedded data right after the marker
    insertion_point = start_pos
    new_content = (
        html_content[:insertion_point] +
        js_code +
        html_content[insertion_point:]
    )
    
    # Write updated HTML
    print(f"💾 Writing updated dashboard HTML...")
    with open(dashboard_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    # Calculate statistics
    total_metadata_sources = sum(len(content.split('\n')) - 1 for content in embedded_data['metadata'].values())
    total_cholera_observations = sum(len(content.split('\n')) - 1 for content in embedded_data['cholera_data'].values())
    
    print(f"\n🎉 Successfully embedded CSV data into dashboard!")
    print(f"📈 Summary:")
    print(f"   • {len(completed_countries)} countries processed")
    print(f"   • {len(embedded_data['metadata'])} metadata files embedded")
    print(f"   • {len(embedded_data['cholera_data'])} cholera data files embedded")
    print(f"   • {total_metadata_sources} total metadata sources")
    print(f"   • {total_cholera_observations} total cholera observations")
    print(f"   • Dashboard updated: {dashboard_file}")
    
    return True

if __name__ == "__main__":
    # Change to the project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    print(f"🏠 Working directory: {Path.cwd()}")
    
    success = embed_csv_data()
    if success:
        print(f"\n✨ CSV data embedding completed successfully!")
        print(f"🌐 Dashboard data tabs should now work without a web server.")
    else:
        print(f"\n❌ CSV data embedding failed!")
        exit(1)