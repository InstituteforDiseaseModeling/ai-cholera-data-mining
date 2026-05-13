#!/usr/bin/env python3
"""
MOSAIC AI Cholera Data Collection - Completion Checklist Auto-Updater
Scans ./data directory and updates completion_checklist.csv based on actual file presence.

Implementation notes:
1. Checks search_report.txt (not legacy quality_audit files)
2. Agent log analysis detects actual completion vs initialization
3. Check for correct workflow file names
4. Validate that agents produced meaningful outputs
5. Better priority determination based on gap analysis
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
    
    # Check for key files (FIXED: check for correct file names)
    files_present = {
        # Baseline files
        'cholera_data_jhu': (country_dir / 'cholera_data_jhu.csv').exists(),
        'cholera_data_who': (country_dir / 'cholera_data_who.csv').exists(),
        # AI-enhanced files
        'cholera_data_ai': (country_dir / 'cholera_data_ai.csv').exists(),
        'metadata_ai': (country_dir / 'metadata_ai.csv').exists(),
        # Workflow files (FIXED: check for correct names)
        'workflow_orchestrator': (country_dir / f'workflow_orchestrator_{iso_code}.txt').exists(),
        'prompt': (country_dir / f'prompt_{iso_code}.txt').exists(),
        # Output files (FIXED: check for search_report.txt)
        'search_report': (country_dir / 'search_report.txt').exists(),
    }
    
    # Analyze agent log files with better detection
    agent_logs = list(country_dir.glob('search_log_agent_*.txt'))
    agent_analysis = analyze_agent_logs_improved(agent_logs)
    
    # Count only truly completed agents
    completed_agents = [num for num, status in agent_analysis.items() 
                       if status in ['completed', 'completed_with_data']]
    num_completed_agents = len(completed_agents)
    
    # Analyze data files
    cholera_data_info = analyze_cholera_data(country_dir / 'cholera_data_ai.csv')
    metadata_info = analyze_metadata(country_dir / 'metadata_ai.csv')
    
    # FIXED: Better completion status determination
    status = determine_status_improved(
        files_present, 
        agent_analysis, 
        cholera_data_info,
        metadata_info
    )
    
    # Get latest modification time
    latest_time = get_latest_modification_time(country_dir)
    
    # Calculate execution metrics
    execution_metrics = calculate_execution_metrics(agent_logs)
    
    # FIXED: Better priority determination
    priority = determine_priority_improved(
        cholera_data_info, 
        files_present,
        status
    )
    
    return {
        'status': status,
        'datetime': latest_time,
        'sources': str(metadata_info.get('source_count', '')),
        'observations': str(cholera_data_info.get('row_count', '')),
        'date_range': cholera_data_info.get('date_range', ''),
        'priority': priority,
        'execution_time': str(execution_metrics.get('total_time', '')),
        'queries': str(execution_metrics.get('total_queries', '')),
        'yield_pct': f"{execution_metrics.get('yield_pct', ''):.1f}" if execution_metrics.get('yield_pct') else '',
        'auto_notes': generate_auto_notes_improved(
            files_present, 
            agent_analysis, 
            cholera_data_info,
            metadata_info
        )
    }

def analyze_agent_logs_improved(agent_logs: List[Path]) -> Dict:
    """Improved agent log analysis with better completion detection"""
    agent_status = {}
    
    for log_file in agent_logs:
        # Extract agent number from filename
        agent_match = re.search(r'agent_(\d+)', log_file.name)
        if not agent_match:
            continue
            
        agent_num = int(agent_match.group(1))
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Analyze content to determine actual status
            lines = content.strip().split('\n')
            
            # Check if this is just initialization
            if len(lines) <= 10 and "INITIALIZATION" in content:
                agent_status[agent_num] = 'initialized'
            # Check for errors or failures
            elif any(error_term in content.upper() for error_term in 
                    ['ERROR', 'FAILED', 'EXCEPTION', 'TRACEBACK']):
                agent_status[agent_num] = 'error'
            # Check if agent actually found and added data
            elif 'cholera_data_ai.csv' in content and any(term in content for term in 
                    ['added', 'new row', 'CSV Updates:', 'observations added']):
                agent_status[agent_num] = 'completed_with_data'
            # Check if agent completed but found no data
            elif any(term in content for term in 
                    ['no data found', 'zero observations', 'no new data']):
                agent_status[agent_num] = 'completed_no_data'
            # Default to completed if log has substantial content
            elif len(lines) > 50:
                agent_status[agent_num] = 'completed'
            else:
                agent_status[agent_num] = 'partial'
                
        except Exception as e:
            print(f"Warning: Could not analyze agent log {log_file}: {e}")
            agent_status[agent_num] = 'unknown'
    
    return agent_status

def determine_status_improved(files_present: Dict, agent_analysis: Dict, 
                            cholera_data_info: Dict, metadata_info: Dict) -> str:
    """Improved status determination with better accuracy"""
    
    # Check for ideal completion: search_report.txt exists with AI data
    if (files_present['search_report'] and 
        files_present['cholera_data_ai'] and 
        files_present['metadata_ai'] and
        cholera_data_info.get('row_count', 0) > 0):
        return 'COMPLETED'
    
    # Check if all 6 agents completed successfully with data
    completed_agents = [num for num, status in agent_analysis.items() 
                       if status in ['completed', 'completed_with_data']]
    
    if (len(completed_agents) >= 6 and 
        files_present['cholera_data_ai'] and 
        files_present['metadata_ai'] and
        cholera_data_info.get('row_count', 0) > 0):
        return 'COMPLETED'
    
    # Check if work is in progress
    if (any(agent_analysis.values()) or 
        files_present['cholera_data_ai'] or 
        files_present['metadata_ai']):
        # Distinguish between active work and stalled work
        if any(status in ['error', 'partial'] for status in agent_analysis.values()):
            return 'PENDING_ISSUES'
        else:
            return 'PENDING'
    
    # Check if setup exists but no work started
    if files_present['workflow_orchestrator'] or files_present['prompt']:
        return 'SETUP_READY'
    
    return 'NOT_STARTED'

def determine_priority_improved(cholera_data_info: Dict, files_present: Dict, 
                              status: str) -> str:
    """Improved priority determination considering multiple factors"""
    
    # If completed, priority is based on data quality/quantity
    if status == 'COMPLETED':
        row_count = cholera_data_info.get('row_count', 0)
        if row_count < 20:
            return 'MEDIUM'  # Completed but limited data
        else:
            return 'LOW'     # Well covered
    
    # If pending with issues, high priority
    elif status == 'PENDING_ISSUES':
        return 'HIGH'
    
    # If work started but not completed
    elif status == 'PENDING':
        return 'MEDIUM'
    
    # If setup ready but not started
    elif status == 'SETUP_READY':
        return 'HIGH'
    
    # Not started at all
    else:
        return 'CRITICAL'

def generate_auto_notes_improved(files_present: Dict, agent_analysis: Dict,
                               cholera_data_info: Dict, metadata_info: Dict) -> str:
    """Improved note generation with more accurate status descriptions"""
    notes = []
    
    # Report on agent completion status
    if files_present['search_report']:
        notes.append("Search report completed")
    
    # Analyze agent statuses
    completed_with_data = [n for n, s in agent_analysis.items() if s == 'completed_with_data']
    completed_no_data = [n for n, s in agent_analysis.items() if s == 'completed_no_data']
    errors = [n for n, s in agent_analysis.items() if s == 'error']
    partial = [n for n, s in agent_analysis.items() if s == 'partial']
    
    if len(agent_analysis) >= 6:
        if errors:
            notes.append(f"Agents with errors: {','.join(map(str, errors))}")
        elif partial:
            notes.append(f"Agents incomplete: {','.join(map(str, partial))}")
        else:
            notes.append("All 6 agents completed")
    elif agent_analysis:
        max_agent = max(agent_analysis.keys())
        status = agent_analysis[max_agent]
        if status == 'completed_with_data':
            notes.append(f"Agent {max_agent} completed with data")
        elif status == 'completed_no_data':
            notes.append(f"Agent {max_agent} completed (no new data)")
        elif status == 'error':
            notes.append(f"Agent {max_agent} encountered errors")
        elif status == 'partial':
            notes.append(f"Agent {max_agent} partially complete")
        else:
            notes.append(f"Agent {max_agent} status: {status}")
    
    # Report on data collected
    if files_present['cholera_data_ai'] and cholera_data_info.get('row_count', 0) > 0:
        notes.append(f"{cholera_data_info['row_count']} AI observations")
        if metadata_info.get('source_count', 0) > 0:
            notes.append(f"{metadata_info['source_count']} sources")
    
    # Report on setup status
    if not files_present['workflow_orchestrator']:
        notes.append("Workflow not initialized")
    
    return "; ".join(notes) if notes else "No activity detected"

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

def get_latest_modification_time(country_dir: Path) -> str:
    """Get the latest modification time of key files in the directory"""
    key_files = [
        'cholera_data_ai.csv', 'metadata_ai.csv', 'search_report.txt',
        'search_log_agent_1.txt', 'search_log_agent_2.txt', 'search_log_agent_3.txt',
        'search_log_agent_4.txt', 'search_log_agent_5.txt', 'search_log_agent_6.txt'
    ]
    
    latest_time = None
    
    for file_name in key_files:
        file_path = country_dir / file_name
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
            
            # Look for data observations added
            data_adds = len(re.findall(r'(added.*row|CSV Updates:.*\d+|observations added)', content, re.IGNORECASE))
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
    print("MOSAIC AI CHOLERA DATA COLLECTION - COMPLETION CHECKLIST AUTO-UPDATER (FIXED)")
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
        
        # Combine auto notes with manual notes
        auto_notes = current_state['auto_notes']
        if manual_notes and '| Manual:' in manual_notes:
            # Extract just the manual part
            manual_part = manual_notes.split('| Manual:')[-1].strip()
            combined_notes = f"{auto_notes} | Manual: {manual_part}"
        elif manual_notes and manual_notes != auto_notes:
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
    
    # Generate summary statistics with new statuses
    status_counts = {}
    for row in updated_data:
        status = row['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print("\n" + "=" * 80)
    print("✅ COMPLETION CHECKLIST UPDATED SUCCESSFULLY!")
    print("=" * 80)
    print(f"📁 Updated: {csv_file}")
    print(f"📊 Total Countries: {len(updated_data)}")
    
    # Print status breakdown
    for status, count in sorted(status_counts.items()):
        print(f"   {status}: {count}")
    
    completed = status_counts.get('COMPLETED', 0)
    progress = completed / len(updated_data) * 100 if updated_data else 0
    print(f"📈 Progress: {progress:.1f}% complete")
    
    print("\n🔄 IMPROVEMENTS IN THIS VERSION:")
    print("- Checks for search_report.txt (Agent 6 output)")
    print("- Better agent log analysis (detects errors, partial completion)")
    print("- Correct workflow file names (workflow_orchestrator_*.txt)")
    print("- New status: PENDING_ISSUES for workflows with errors")
    print("- New status: SETUP_READY when files prepared but work not started")
    print("- Priority based on actual completion and data quality")
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