#!/usr/bin/env python3
"""
MOSAIC AI Cholera Data Collection - Completion Checklist Auto-Updater
Automatically scans ./data directory and updates completion_checklist.csv based on actual file presence and content.

USAGE: Run from project root directory:
    python py/update_completion_checklist.py

This script:
1. Scans all country directories in ./data/
2. Analyzes file presence and content to determine completion status
3. Updates dashboard/completion_checklist.csv with current state
4. Preserves manual notes while updating automatic fields
"""

import os
import json
import csv
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

def load_country_mapping(base_path: Path) -> Dict:
    """Load country mapping from reference file"""
    mapping_file = base_path / "reference" / "country_mapping.json"
    try:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Country mapping file not found: {mapping_file}")
        return {}

def analyze_country_directory(country_dir: Path, iso_code: str) -> Dict:
    """Analyze a country directory to determine completion status and metrics"""
    
    if not country_dir.exists():
        return {
            'status': 'NOT_STARTED',
            'datetime': '',
            'sources': '',
            'observations': '',
            'date_range': '',
            'priority': '',
            'execution_time': '',
            'queries': '',
            'yield_pct': '',
            'auto_notes': f'Directory not found: {country_dir}'
        }
    
    # Check for key files
    files_present = {
        'cholera_data': (country_dir / 'cholera_data.csv').exists(),
        'metadata': (country_dir / 'metadata.csv').exists(),
        'search_protocol': (country_dir / f'search_protocol_{iso_code}.txt').exists(),
        'agentic_workflow': (country_dir / f'agentic_workflow_{iso_code}.txt').exists(),
    }
    
    # Count agent log files
    agent_logs = list(country_dir.glob('search_log_agent_*.txt'))
    num_agents = len(agent_logs)
    
    # Check for quality audit
    quality_audit = (country_dir / 'quality_audit_report_agent_6.txt').exists()
    
    # Analyze cholera_data.csv if it exists
    cholera_data_info = analyze_cholera_data(country_dir / 'cholera_data.csv')
    metadata_info = analyze_metadata(country_dir / 'metadata.csv')
    
    # Determine completion status
    status = determine_status(files_present, num_agents, quality_audit, cholera_data_info)
    
    # Get latest modification time
    latest_time = get_latest_modification_time(country_dir)
    
    # Calculate execution metrics
    execution_metrics = calculate_execution_metrics(agent_logs)
    
    return {
        'status': status,
        'datetime': latest_time,
        'sources': str(metadata_info.get('source_count', '')),
        'observations': str(cholera_data_info.get('row_count', '')),
        'date_range': cholera_data_info.get('date_range', ''),
        'priority': determine_priority(cholera_data_info),
        'execution_time': str(execution_metrics.get('total_time', '')),
        'queries': str(execution_metrics.get('total_queries', '')),
        'yield_pct': f"{execution_metrics.get('yield_pct', ''):.1f}" if execution_metrics.get('yield_pct') else '',
        'auto_notes': generate_auto_notes(files_present, num_agents, quality_audit, cholera_data_info)
    }

def analyze_cholera_data(csv_file: Path) -> Dict:
    """Analyze cholera_data.csv for metrics"""
    if not csv_file.exists():
        return {'row_count': 0, 'date_range': '', 'earliest_date': None, 'latest_date': None}
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        if not rows:
            return {'row_count': 0, 'date_range': '', 'earliest_date': None, 'latest_date': None}
        
        # Extract dates from TL and TR columns
        dates = []
        for row in rows:
            for date_col in ['TL', 'TR']:
                date_str = row.get(date_col, '').strip()
                if date_str and date_str != '':
                    try:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                        dates.append(date_obj)
                    except ValueError:
                        continue
        
        if dates:
            earliest = min(dates)
            latest = max(dates)
            date_range = f"{earliest.year}-{latest.year}"
            if earliest.year == latest.year:
                date_range = str(earliest.year)
        else:
            date_range = ''
            earliest = None
            latest = None
        
        return {
            'row_count': len(rows),
            'date_range': date_range,
            'earliest_date': earliest,
            'latest_date': latest
        }
        
    except Exception as e:
        print(f"Warning: Could not analyze {csv_file}: {e}")
        return {'row_count': 0, 'date_range': '', 'earliest_date': None, 'latest_date': None}

def analyze_metadata(csv_file: Path) -> Dict:
    """Analyze metadata.csv for source count"""
    if not csv_file.exists():
        return {'source_count': 0}
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        return {'source_count': len(rows)}
        
    except Exception as e:
        print(f"Warning: Could not analyze {csv_file}: {e}")
        return {'source_count': 0}

def determine_status(files_present: Dict, num_agents: int, quality_audit: bool, cholera_data_info: Dict) -> str:
    """Determine completion status based on file analysis"""
    
    # Check if workflow has been completed
    # Option 1: Agent 6 quality audit exists (ideal completion)
    if quality_audit and files_present['cholera_data'] and files_present['metadata']:
        return 'COMPLETED'
    
    # Option 2: All 6 agents completed with data files (workflow complete without formal audit)
    if (num_agents >= 6 and files_present['cholera_data'] and files_present['metadata'] 
        and cholera_data_info.get('row_count', 0) > 0):
        return 'COMPLETED'
    
    # Check if work is in progress (some agent logs exist or data files present)
    if num_agents > 0 or files_present['cholera_data']:
        return 'PENDING'
    
    # Check if setup files exist but no work started
    if files_present['search_protocol'] or files_present['agentic_workflow']:
        return 'NOT_STARTED'
    
    return 'NOT_STARTED'

def determine_priority(cholera_data_info: Dict) -> str:
    """Determine priority based on data coverage"""
    row_count = cholera_data_info.get('row_count', 0)
    
    if row_count == 0:
        return ''
    elif row_count < 15:
        return 'HIGH'  # Limited data suggests gaps
    elif row_count < 30:
        return 'MEDIUM'
    else:
        return 'LOW'  # Good coverage

def get_latest_modification_time(country_dir: Path) -> str:
    """Get the latest modification time of key files in the directory"""
    key_files = ['cholera_data.csv', 'metadata.csv', 'quality_audit_report_agent_6.txt']
    key_files.extend([f'search_log_agent_{i}.txt' for i in range(1, 7)])
    
    latest_time = None
    
    for file_pattern in key_files:
        file_path = country_dir / file_pattern
        if file_path.exists():
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if latest_time is None or mtime > latest_time:
                latest_time = mtime
    
    if latest_time:
        return latest_time.strftime('%Y-%m-%d %H:%M:%S')
    else:
        return ''

def calculate_execution_metrics(agent_logs: List[Path]) -> Dict:
    """Calculate execution metrics from agent log files"""
    total_queries = 0
    total_time = 0
    data_observations = 0
    
    for log_file in agent_logs:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Count queries (lines with "WebSearch" or "WebFetch")
            queries_in_log = len(re.findall(r'(WebSearch|WebFetch)', content, re.IGNORECASE))
            total_queries += queries_in_log
            
            # Look for data observations added (lines mentioning "cholera_data.csv" additions)
            data_adds = len(re.findall(r'(added|new.*row|cholera_data\.csv)', content, re.IGNORECASE))
            data_observations += data_adds
            
        except Exception as e:
            print(f"Warning: Could not analyze log file {log_file}: {e}")
            continue
    
    # Calculate yield percentage
    yield_pct = (data_observations / total_queries * 100) if total_queries > 0 else 0
    
    # Estimate execution time (rough estimate based on query count)
    estimated_minutes = total_queries * 0.3  # ~18 seconds per query average
    
    return {
        'total_queries': total_queries,
        'total_time': int(estimated_minutes),
        'yield_pct': yield_pct,
        'data_observations': data_observations
    }

def generate_auto_notes(files_present: Dict, num_agents: int, quality_audit: bool, cholera_data_info: Dict) -> str:
    """Generate automatic notes describing current state"""
    notes = []
    
    if quality_audit:
        notes.append("Quality audit completed")
    elif num_agents >= 6:
        notes.append("All agents executed")
    elif num_agents > 0:
        notes.append(f"Agent {num_agents} completed")
    
    if files_present['cholera_data'] and cholera_data_info.get('row_count', 0) > 0:
        notes.append(f"{cholera_data_info['row_count']} data observations")
    
    if not files_present['search_protocol']:
        notes.append("Setup incomplete")
    
    return "; ".join(notes) if notes else "No activity detected"

def load_existing_csv(csv_file: Path) -> Dict[str, Dict]:
    """Load existing CSV file and preserve manual notes"""
    existing_data = {}
    
    if not csv_file.exists():
        return existing_data
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                iso = row.get('iso', '').strip()
                if iso:
                    existing_data[iso] = row
    except Exception as e:
        print(f"Warning: Could not load existing CSV: {e}")
    
    return existing_data

def update_dashboard_html(base_path: Path, updated_data: List[Dict]):
    """Update the dashboard HTML with embedded CSV data"""
    dashboard_file = base_path / "dashboard" / "dashboard.html"
    
    if not dashboard_file.exists():
        print(f"Warning: Dashboard file not found: {dashboard_file}")
        return
    
    # Generate CSV string from updated data
    fieldnames = ['country', 'iso', 'status', 'datetime', 'sources', 'observations', 
                 'date_range', 'priority', 'execution_time', 'queries', 'yield_pct', 'notes']
    
    csv_lines = [','.join(fieldnames)]
    for row in updated_data:
        # Handle commas in data by quoting fields that contain commas
        csv_row = []
        for field in fieldnames:
            value = str(row.get(field, ''))
            if ',' in value or '"' in value:
                value = '"' + value.replace('"', '""') + '"'
            csv_row.append(value)
        csv_lines.append(','.join(csv_row))
    
    new_csv_data = '\n'.join(csv_lines)
    
    try:
        # Read current HTML
        with open(dashboard_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Find and replace the embedded CSV data
        import re
        pattern = r'const csvData = `[^`]*`;'
        replacement = f'const csvData = `{new_csv_data}`;'
        
        updated_html = re.sub(pattern, replacement, html_content, flags=re.DOTALL)
        
        # Write updated HTML
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            f.write(updated_html)
        
        print(f"📊 Dashboard HTML updated: {dashboard_file}")
        
    except Exception as e:
        print(f"Warning: Could not update dashboard HTML: {e}")

def update_completion_checklist(base_path: Path):
    """Main function to update the completion checklist"""
    print("=" * 80)
    print("MOSAIC AI CHOLERA DATA COLLECTION - COMPLETION CHECKLIST AUTO-UPDATER")
    print("=" * 80)
    
    # Load country mapping
    country_mapping = load_country_mapping(base_path)
    if not country_mapping:
        print("Error: Could not load country mapping. Exiting.")
        return
    
    mosaic_countries = {
        iso: info for iso, info in country_mapping.get('countries', {}).items()
        if info.get('mosaic_framework', False)
    }
    
    print(f"Analyzing {len(mosaic_countries)} MOSAIC framework countries...")
    
    # Load existing CSV to preserve manual notes
    csv_file = base_path / "dashboard" / "completion_checklist.csv"
    existing_data = load_existing_csv(csv_file)
    
    # Analyze each country directory
    updated_data = []
    data_dir = base_path / "data"
    
    for iso_code, country_info in mosaic_countries.items():
        country_dir = data_dir / iso_code
        country_name = country_info.get('name', 'UNKNOWN')
        
        print(f"  Analyzing {iso_code} ({country_name})...")
        
        # Get current state from file analysis
        current_state = analyze_country_directory(country_dir, iso_code)
        
        # Preserve manual notes from existing data
        existing_row = existing_data.get(iso_code, {})
        manual_notes = existing_row.get('notes', '').strip()
        
        # Combine auto notes with manual notes (avoid duplication)
        auto_notes = current_state['auto_notes']
        if manual_notes and not manual_notes.startswith(auto_notes):
            # Only add manual notes if they're different and not already included
            if '| Manual:' in manual_notes:
                # Extract just the manual part to avoid nested Manual: prefixes
                manual_part = manual_notes.split('| Manual:')[-1].strip()
                if manual_part != auto_notes:
                    combined_notes = f"{auto_notes} | Manual: {manual_part}"
                else:
                    combined_notes = auto_notes
            else:
                combined_notes = f"{auto_notes} | Manual: {manual_notes}"
        else:
            combined_notes = auto_notes
        
        # Create updated row
        updated_row = {
            'country': country_name,
            'iso': iso_code,
            'status': current_state['status'],
            'datetime': current_state['datetime'],
            'sources': current_state['sources'],
            'observations': current_state['observations'],
            'date_range': current_state['date_range'],
            'priority': current_state['priority'],
            'execution_time': current_state['execution_time'],
            'queries': current_state['queries'],
            'yield_pct': current_state['yield_pct'],
            'notes': combined_notes
        }
        
        updated_data.append(updated_row)
    
    # Write updated CSV
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['country', 'iso', 'status', 'datetime', 'sources', 'observations', 
                     'date_range', 'priority', 'execution_time', 'queries', 'yield_pct', 'notes']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_data)
    
    # Update dashboard HTML with embedded data
    update_dashboard_html(base_path, updated_data)
    
    # Generate summary statistics
    completed = sum(1 for row in updated_data if row['status'] == 'COMPLETED')
    pending = sum(1 for row in updated_data if row['status'] == 'PENDING')
    not_started = sum(1 for row in updated_data if row['status'] == 'NOT_STARTED')
    
    print("\n" + "=" * 80)
    print("✅ COMPLETION CHECKLIST UPDATED SUCCESSFULLY!")
    print("=" * 80)
    print(f"📁 Updated: {csv_file}")
    print(f"📊 Total Countries: {len(updated_data)}")
    print(f"✅ Completed: {completed}")
    print(f"⏳ Pending: {pending}")
    print(f"⭕ Not Started: {not_started}")
    print(f"📈 Progress: {completed/len(updated_data)*100:.1f}% complete")
    
    print("\n🔄 DASHBOARD WILL AUTO-REFRESH:")
    print("- Real-time status based on file analysis")
    print("- Automatic metrics calculation") 
    print("- Preserved manual notes")
    print("- Dashboard HTML auto-updated with latest data")
    print("- No manual intervention required")
    print("=" * 80)

def main():
    """Main function"""
    # Get the base path (parent directory of the py directory)
    base_path = Path(__file__).parent.parent
    
    try:
        update_completion_checklist(base_path)
    except Exception as e:
        print(f"❌ ERROR DURING UPDATE: {e}")
        raise

if __name__ == "__main__":
    main()