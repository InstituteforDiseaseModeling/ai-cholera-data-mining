#!/usr/bin/env python3
"""
MOSAIC AI Cholera Data Collection - Unified Dashboard Data Updater

This script combines all dashboard data updates into a single command:
1. Updates completion checklist based on file analysis
2. Generates 3-source timeline coverage plots for all countries
3. Creates timeline week counts CSV
4. Updates dashboard HTML with embedded data

USAGE: Run from project root directory:
    python py/update_dashboard_data.py

This is the single command that agents should run to update all dashboard data.
"""

import os
import json
import csv
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np
from PIL import Image

# ============================================================================
# COMPLETION CHECKLIST FUNCTIONS
# ============================================================================

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
    
    # Analyze agent log files
    agent_logs = list(country_dir.glob('search_log_agent_*.txt'))
    agent_analysis = analyze_agent_logs(agent_logs)
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
        'auto_notes': generate_auto_notes(files_present, num_agents, quality_audit, cholera_data_info, agent_analysis)
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

def analyze_agent_logs(agent_logs: List[Path]) -> Dict:
    """Analyze agent log files to determine their status"""
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
                
            # Determine if agent is initialized vs completed
            if "=== AGENT 1 INITIALIZATION ===" in content and "Agent 1 Status: INITIALIZED" in content:
                # This is just an initialization - agent hasn't actually started work yet
                if len(content.strip().split('\n')) <= 10:  # Very short file = just initialization
                    agent_status[agent_num] = 'initialized'
                else:
                    agent_status[agent_num] = 'completed'
            else:
                # Regular agent log with actual work
                agent_status[agent_num] = 'completed'
                
        except Exception as e:
            print(f"Warning: Could not analyze agent log {log_file}: {e}")
            agent_status[agent_num] = 'unknown'
    
    return agent_status

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

def generate_auto_notes(files_present: Dict, num_agents: int, quality_audit: bool, cholera_data_info: Dict, agent_analysis: Dict) -> str:
    """Generate automatic notes describing current state"""
    notes = []
    
    if quality_audit:
        notes.append("Quality audit completed")
    elif num_agents >= 6:
        notes.append("All agents executed")
    elif num_agents > 0:
        # Check if we have any completed agents or just initialized
        completed_agents = [num for num, status in agent_analysis.items() if status == 'completed']
        initialized_agents = [num for num, status in agent_analysis.items() if status == 'initialized']
        
        if completed_agents:
            max_completed = max(completed_agents)
            notes.append(f"Agent {max_completed} completed")
        elif initialized_agents:
            # Only initialized agents, no completed work yet
            notes.append("Agent 1 initialized - starting work")
    
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

# ============================================================================
# SURVEILLANCE DATA MANAGEMENT FUNCTIONS
# ============================================================================

def embed_original_surveillance_data(base_path: Path):
    """
    Embed MOSAIC surveillance data into reference/ directory for CI environments.
    
    This function copies the essential MOSAIC surveillance data to ./reference/
    so it's available in GitHub Pages and other CI environments that don't have
    access to the full MOSAIC project structure.
    """
    print("🔄 EMBEDDING ORIGINAL SURVEILLANCE DATA...")
    
    # Source file (full MOSAIC project structure)
    source_file = base_path.parent / "MOSAIC-data" / "processed" / "cholera" / "weekly" / "cholera_surveillance_weekly_combined.csv"
    
    # Destination file (this repo's reference directory)
    dest_file = base_path / "reference" / "cholera_surveillance_weekly_combined.csv"
    
    if not source_file.exists():
        print(f"❌ Source MOSAIC surveillance file not found: {source_file}")
        print("   Cannot embed surveillance data - only AI data will be available in CI environments")
        return False
    
    # Load MOSAIC country mapping to filter data
    country_mapping = load_country_mapping(base_path)
    mosaic_iso_codes = set(country_mapping.keys())
    
    print(f"📂 Reading source: {source_file}")
    print(f"📂 Writing to: {dest_file}")
    print(f"🌍 Filtering to {len(mosaic_iso_codes)} MOSAIC framework countries")
    
    # Process and filter the data
    filtered_rows = []
    total_rows = 0
    filtered_count = 0
    
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                total_rows += 1
                iso_code = row['iso_code'].strip('"')
                
                # Filter to MOSAIC framework countries only
                if iso_code in mosaic_iso_codes:
                    # Keep only rows with actual data (not NA)
                    cases = row['cases'].strip('"')
                    date_start = row['date_start'].strip('"')
                    
                    if cases != 'NA' and date_start != 'NA':
                        filtered_rows.append(row)
                        filtered_count += 1
        
        print(f"📊 Processed {total_rows:,} total rows")
        print(f"✅ Filtered to {filtered_count:,} MOSAIC framework rows with data")
        
        # Write filtered data to reference directory
        dest_file.parent.mkdir(exist_ok=True)
        
        with open(dest_file, 'w', newline='', encoding='utf-8') as f:
            if filtered_rows:
                fieldnames = filtered_rows[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                writer.writeheader()
                writer.writerows(filtered_rows)
        
        print(f"✅ Successfully embedded surveillance data to {dest_file}")
        print(f"📈 Data includes WHO, JHU, and supplementary sources for timeline generation")
        return True
        
    except Exception as e:
        print(f"❌ Error embedding surveillance data: {e}")
        return False

# ============================================================================
# TIMELINE PLOT FUNCTIONS
# ============================================================================

def load_separated_surveillance_data(base_path: Path) -> pd.DataFrame:
    """
    Load surveillance data - simplified to use AI data only within this repo.
    
    This function now returns an empty DataFrame to allow the dashboard to work
    entirely with AI-enhanced data collected within this repository.
    """
    
    print("Using AI-enhanced data only (no external surveillance dependencies)...")
    return pd.DataFrame()

def load_ai_enhanced_data(base_path: Path, iso_code: str) -> pd.DataFrame:
    """Load AI-enhanced data and convert to weekly format"""
    
    cholera_file = base_path / "data" / iso_code / "cholera_data.csv"
    ai_data = []
    
    if not cholera_file.exists():
        return pd.DataFrame()
    
    try:
        with open(cholera_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                tl = row.get('TL', '').strip()
                tr = row.get('TR', '').strip()
                
                if tl:
                    try:
                        start_date = datetime.strptime(tl, '%Y-%m-%d')
                        end_date = datetime.strptime(tr, '%Y-%m-%d') if tr else start_date
                        
                        # Map date range to all overlapping weeks
                        current_date = start_date
                        while current_date <= end_date:
                            year = current_date.year
                            week = current_date.isocalendar()[1]
                            
                            ai_data.append({
                                'iso_code': iso_code,
                                'source': 'AI',
                                'year': year,
                                'week': week,
                                'date_from': current_date.strftime('%Y-%m-%d'),
                                'date_to': (current_date + pd.Timedelta(days=6)).strftime('%Y-%m-%d'),
                                'present': 1
                            })
                            current_date += pd.Timedelta(days=7)
                            
                    except ValueError:
                        continue  # Skip invalid dates
    
    except Exception as e:
        pass  # Silently skip files that can't be read
    
    return pd.DataFrame(ai_data).drop_duplicates(['iso_code', 'source', 'year', 'week'])

def find_data_blocks(df_source):
    """Find continuous blocks of data availability"""
    
    if df_source.empty:
        return []
    
    df_source = df_source.copy()
    df_source['date'] = pd.to_datetime(df_source['date_from'])
    df_source = df_source.sort_values('date')
    
    blocks = []
    start_date = None
    prev_date = None
    
    for _, row in df_source.iterrows():
        current_date = row['date']
        
        if start_date is None:
            # Start of first block
            start_date = current_date
        elif prev_date is not None and (current_date - prev_date).days > 14:
            # Gap detected (more than 2 weeks), end previous block
            blocks.append((start_date, prev_date))
            start_date = current_date
        
        prev_date = current_date
    
    # Don't forget the last block
    if start_date is not None and prev_date is not None:
        blocks.append((start_date, prev_date))
    
    return blocks

def find_global_date_range(base_path: Path, country_mapping: dict) -> tuple:
    """Find the global minimum and maximum dates across all countries and sources"""
    all_dates = []
    
    print("Finding global date range across all countries and sources...")
    
    # Load MOSAIC surveillance data for global dates
    surveillance_df = load_separated_surveillance_data(base_path)
    for _, row in surveillance_df.iterrows():
        try:
            date = pd.to_datetime(row['date_from'])
            all_dates.append(date)
        except:
            continue
    
    # Load AI data for all countries for global dates
    for iso_code in country_mapping.keys():
        ai_data = load_ai_enhanced_data(base_path, iso_code)
        for _, row in ai_data.iterrows():
            try:
                date = pd.to_datetime(row['date_from'])
                all_dates.append(date)
            except:
                continue
    
    if all_dates:
        min_date = min(all_dates)
        max_date = max(all_dates)
        print(f"  Global date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
        return min_date, max_date
    else:
        # Fallback dates if no data found
        return pd.Timestamp('1970-01-01'), pd.Timestamp('2025-12-31')

def crop_timeline_plot(image_path, crop_cm=1.0):
    """Crop the top portion of timeline plot to remove title and week counts
    
    Args:
        image_path: Path to the PNG file
        crop_cm: Amount to crop from top in centimeters (default 1.0cm)
    """
    try:
        # Open the image
        with Image.open(image_path) as img:
            # Get image dimensions
            width, height = img.size
            
            # Calculate crop amount in pixels
            # Assuming 300 DPI: 1 cm = 300/2.54 ≈ 118 pixels
            dpi = 300
            pixels_per_cm = dpi / 2.54
            crop_pixels = int(crop_cm * pixels_per_cm)
            
            # Ensure we don't crop more than 25% of the image
            max_crop = height // 4
            crop_pixels = min(crop_pixels, max_crop)
            
            # Crop the image (left, top, right, bottom)
            cropped_img = img.crop((0, crop_pixels, width, height))
            
            # Save the cropped image
            cropped_img.save(image_path, dpi=(300, 300))
            
    except Exception as e:
        print(f"    Warning: Could not crop {image_path}: {e}")

def create_3source_timeline_plot(country_data, country_name, iso_code, output_dir, global_min_date, global_max_date):
    """Create timeline coverage plot with 3 separate source tracks"""
    
    # Separate data by source
    ai_data = country_data[country_data['source'] == 'AI']
    who_data = country_data[country_data['source'] == 'WHO'] 
    jhu_data = country_data[country_data['source'] == 'JHU']
    
    # Find continuous blocks for each source
    ai_blocks = find_data_blocks(ai_data)
    who_blocks = find_data_blocks(who_data)
    jhu_blocks = find_data_blocks(jhu_data)
    
    # Skip countries with no data
    if not ai_blocks and not who_blocks and not jhu_blocks:
        print(f"  Skipping {country_name} - no data blocks found")
        return
    
    # Set up the plot
    fig, ax = plt.subplots(figsize=(16, 5))
    
    # Define y-positions and colors for each source - Analogous cool palette
    sources = {
        'AI': {'y': 3, 'color': '#2ECC71', 'label': 'AI'},           # Emerald green (top)
        'WHO': {'y': 2, 'color': '#0167af', 'label': 'WHO'},        # Dashboard blue (middle)
        'JHU': {'y': 1, 'color': '#9B59B6', 'label': 'JHU'}         # Purple (bottom)
    }
    
    # Plot AI blocks (emerald green, top)
    for start_date, end_date in ai_blocks:
        width = (end_date - start_date).days + 7  # Add a week for visibility
        rect = patches.Rectangle(
            (start_date, sources['AI']['y'] - 0.35), 
            pd.Timedelta(days=width), 0.7,
            linewidth=0, facecolor=sources['AI']['color'], alpha=0.8
        )
        ax.add_patch(rect)
    
    # Plot WHO blocks (dashboard blue, middle)
    for start_date, end_date in who_blocks:
        width = (end_date - start_date).days + 7
        rect = patches.Rectangle(
            (start_date, sources['WHO']['y'] - 0.35), 
            pd.Timedelta(days=width), 0.7,
            linewidth=0, facecolor=sources['WHO']['color'], alpha=0.8
        )
        ax.add_patch(rect)
    
    # Plot JHU blocks (purple, bottom)
    for start_date, end_date in jhu_blocks:
        width = (end_date - start_date).days + 7
        rect = patches.Rectangle(
            (start_date, sources['JHU']['y'] - 0.35), 
            pd.Timedelta(days=width), 0.7,
            linewidth=0, facecolor=sources['JHU']['color'], alpha=0.8
        )
        ax.add_patch(rect)
    
    # Set up axes
    ax.set_ylim(0.5, 3.8)
    ax.set_yticks([1, 2, 3])
    ax.set_yticklabels(['JHU', 'WHO', 'AI'], fontsize=14)
    
    # Format x-axis to show years using global date range
    # Set x-axis limits - small buffer on left, padding on right
    ax.set_xlim(global_min_date - pd.Timedelta(days=180), global_max_date + pd.Timedelta(days=365))
    
    # Generate year ticks based on global range
    year_range = range(global_min_date.year, global_max_date.year + 2)
    year_ticks = [datetime(year, 1, 1) for year in year_range if year % 2 == 0]  # Every 2 years
    ax.set_xticks(year_ticks)
    ax.set_xticklabels([str(year) for year in year_range if year % 2 == 0], rotation=45, fontsize=12)
    
    # Add title and formatting
    plt.title(f'{country_name} ({iso_code})', 
              fontsize=16, fontweight='bold', pad=20)
    
    # Add grid for better readability
    ax.grid(True, alpha=0.3, axis='x')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Add legend - horizontal, no box, positioned under x-axis
    legend_elements = [
        patches.Patch(color=sources['AI']['color'], alpha=0.8, label='AI Enhanced Data'),
        patches.Patch(color=sources['WHO']['color'], alpha=0.8, label='WHO Surveillance'),
        patches.Patch(color=sources['JHU']['color'], alpha=0.8, label='JHU Database')
    ]
    ax.legend(handles=legend_elements, loc='upper center', frameon=False, 
              bbox_to_anchor=(0.5, -0.3), ncol=3, fontsize=12)
    
    # Add data summary text - moved to right top margin, no box
    ai_weeks = len(ai_data)
    who_weeks = len(who_data) 
    jhu_weeks = len(jhu_data)
    
    summary_text = f"AI: {ai_weeks} weeks | WHO: {who_weeks} weeks | JHU: {jhu_weeks} weeks"
    ax.text(0.98, 1.05, summary_text, transform=ax.transAxes, fontsize=12, 
            verticalalignment='bottom', horizontalalignment='right')
    
    # Save plot
    plt.tight_layout()
    output_file = output_dir / f"{iso_code}_{country_name.replace(' ', '_')}_3sources_timeline.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    # Crop the top 1cm to remove title and week counts
    crop_timeline_plot(output_file, crop_cm=1.0)
    
    print(f"  ✅ Timeline plot: {output_file.name}")

def count_weeks_by_source(country_data: pd.DataFrame) -> tuple:
    """Count unique weeks for each source"""
    
    if country_data.empty or 'source' not in country_data.columns:
        return 0, 0, 0
    
    ai_weeks = len(country_data[country_data['source'] == 'AI'])
    who_weeks = len(country_data[country_data['source'] == 'WHO'])
    jhu_weeks = len(country_data[country_data['source'] == 'JHU'])
    
    return ai_weeks, who_weeks, jhu_weeks

# ============================================================================
# MAIN UNIFIED UPDATE FUNCTION
# ============================================================================

def update_dashboard_html(base_path: Path, updated_data: List[Dict], week_counts_data: List[Dict]):
    """Update the dashboard HTML with embedded CSV data"""
    dashboard_file = base_path / "dashboard" / "dashboard.html"
    
    if not dashboard_file.exists():
        print(f"Warning: Dashboard file not found: {dashboard_file}")
        return
    
    # Generate completion checklist CSV string
    checklist_fieldnames = ['country', 'iso', 'status', 'datetime', 'sources', 'observations', 
                           'date_range', 'priority', 'execution_time', 'queries', 'yield_pct', 'notes']
    
    checklist_csv_lines = [','.join(checklist_fieldnames)]
    for row in updated_data:
        # Handle commas in data by quoting fields that contain commas
        csv_row = []
        for field in checklist_fieldnames:
            value = str(row.get(field, ''))
            if ',' in value or '"' in value:
                value = '"' + value.replace('"', '""') + '"'
            csv_row.append(value)
        checklist_csv_lines.append(','.join(csv_row))
    
    checklist_csv_data = '\n'.join(checklist_csv_lines)
    
    # Generate week counts CSV string
    week_counts_fieldnames = ['country', 'iso_code', 'ai_weeks', 'who_weeks', 'jhu_weeks']
    week_counts_csv_lines = [','.join(week_counts_fieldnames)]
    for row in week_counts_data:
        csv_row = [str(row.get(field, '')) for field in week_counts_fieldnames]
        week_counts_csv_lines.append(','.join(csv_row))
    
    week_counts_csv_data = '\n'.join(week_counts_csv_lines)
    
    try:
        # Read current HTML
        with open(dashboard_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Find and replace the embedded CSV data
        import re
        
        # Update completion checklist data
        checklist_pattern = r'const csvData = `[^`]*`;'
        checklist_replacement = f'const csvData = `{checklist_csv_data}`;'
        html_content = re.sub(checklist_pattern, checklist_replacement, html_content, flags=re.DOTALL)
        
        # Update week counts data
        week_counts_pattern = r'const weekCountsCSV = `[^`]*`;'
        week_counts_replacement = f'const weekCountsCSV = `{week_counts_csv_data}`;'
        html_content = re.sub(week_counts_pattern, week_counts_replacement, html_content, flags=re.DOTALL)
        
        # Write updated HTML
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📊 Dashboard HTML updated: {dashboard_file}")
        
    except Exception as e:
        print(f"Warning: Could not update dashboard HTML: {e}")

def update_all_dashboard_data(base_path: Path):
    """Main function to update all dashboard data"""
    print("=" * 80)
    print("MOSAIC AI CHOLERA DATA - UNIFIED DASHBOARD DATA UPDATER")
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
    
    print(f"Processing {len(mosaic_countries)} MOSAIC framework countries...")
    
    # ========================================================================
    # 1. UPDATE COMPLETION CHECKLIST
    # ========================================================================
    print("\n🔄 STEP 1: Updating completion checklist...")
    
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
    
    print(f"✅ Completion checklist updated: {csv_file}")
    
    # ========================================================================
    # 2. GENERATE TIMELINE PLOTS
    # ========================================================================
    print("\n📊 STEP 2: Generating 3-source timeline coverage plots...")
    
    # Load surveillance data
    surveillance_df = load_separated_surveillance_data(base_path)
    
    # Find global date range across all countries
    global_min_date, global_max_date = find_global_date_range(base_path, mosaic_countries)
    
    # Create output directory
    output_dir = base_path / "dashboard" / "timeline_plots"
    output_dir.mkdir(exist_ok=True)
    
    print(f"Using consistent date range: {global_min_date.strftime('%Y-%m-%d')} to {global_max_date.strftime('%Y-%m-%d')}")
    
    countries_with_data = 0
    
    for iso_code, country_info in mosaic_countries.items():
        country_name = country_info.get('name', iso_code)
        print(f"  Processing {country_name} ({iso_code})...")
        
        # Get surveillance data for this country
        if not surveillance_df.empty and 'iso_code' in surveillance_df.columns:
            country_surveillance = surveillance_df[surveillance_df['iso_code'] == iso_code]
        else:
            country_surveillance = pd.DataFrame()
        
        # Get AI data for this country
        country_ai = load_ai_enhanced_data(base_path, iso_code)
        
        # Combine all data
        country_data = pd.concat([country_surveillance, country_ai], ignore_index=True)
        
        if country_data.empty:
            print(f"    No data found for {country_name}")
            continue
        
        # Create timeline plot
        try:
            create_3source_timeline_plot(country_data, country_name, iso_code, output_dir, global_min_date, global_max_date)
            countries_with_data += 1
        except Exception as e:
            print(f"    Error creating plot for {country_name}: {e}")
    
    print(f"✅ Timeline plots generated for {countries_with_data} countries")
    
    # ========================================================================
    # 3. GENERATE WEEK COUNTS DATA
    # ========================================================================
    print("\n📈 STEP 3: Generating timeline week counts data...")
    
    # Get countries with timeline plots
    countries_with_plots = []
    for plot_file in output_dir.glob("*_3sources_timeline.png"):
        # Extract ISO code from filename (format: ISO_Country_Name_3sources_timeline.png)
        iso_code = plot_file.name.split('_')[0]
        countries_with_plots.append(iso_code)
    
    # Filter to countries that have timeline plots
    plot_countries = {iso: mosaic_countries[iso] for iso in countries_with_plots if iso in mosaic_countries}
    
    # Prepare week counts results
    week_counts_results = []
    
    for iso_code, country_info in sorted(plot_countries.items()):
        country_name = country_info.get('name', iso_code)
        print(f"  Processing {country_name} ({iso_code})...")
        
        # Get surveillance data for this country
        if not surveillance_df.empty and 'iso_code' in surveillance_df.columns:
            country_surveillance = surveillance_df[surveillance_df['iso_code'] == iso_code]
        else:
            country_surveillance = pd.DataFrame()
        
        # Get AI data for this country
        country_ai = load_ai_enhanced_data(base_path, iso_code)
        
        # Combine all data
        country_data = pd.concat([country_surveillance, country_ai], ignore_index=True)
        
        # Count weeks by source
        ai_weeks, who_weeks, jhu_weeks = count_weeks_by_source(country_data)
        
        week_counts_results.append({
            'country': country_name,
            'iso_code': iso_code,
            'ai_weeks': ai_weeks,
            'who_weeks': who_weeks,
            'jhu_weeks': jhu_weeks
        })
        
        print(f"    AI: {ai_weeks} weeks | WHO: {who_weeks} weeks | JHU: {jhu_weeks} weeks")
    
    # Create output CSV
    week_counts_file = base_path / "dashboard" / "timeline_week_counts.csv"
    
    with open(week_counts_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['country', 'iso_code', 'ai_weeks', 'who_weeks', 'jhu_weeks']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in week_counts_results:
            writer.writerow(result)
    
    print(f"✅ Timeline week counts CSV created: {week_counts_file}")
    
    # ========================================================================
    # 4. UPDATE DASHBOARD HTML
    # ========================================================================
    print("\n📱 STEP 4: Updating dashboard HTML with embedded data...")
    
    update_dashboard_html(base_path, updated_data, week_counts_results)
    
    # ========================================================================
    # 5. GENERATE SUMMARY STATISTICS
    # ========================================================================
    print("\n" + "=" * 80)
    print("✅ ALL DASHBOARD DATA UPDATED SUCCESSFULLY!")
    print("=" * 80)
    
    # Completion checklist summary
    completed = sum(1 for row in updated_data if row['status'] == 'COMPLETED')
    pending = sum(1 for row in updated_data if row['status'] == 'PENDING')
    not_started = sum(1 for row in updated_data if row['status'] == 'NOT_STARTED')
    
    print(f"📁 Completion Checklist: {csv_file}")
    print(f"📊 Total Countries: {len(updated_data)}")
    print(f"✅ Completed: {completed}")
    print(f"⏳ Pending: {pending}")
    print(f"⭕ Not Started: {not_started}")
    print(f"📈 Progress: {completed/len(updated_data)*100:.1f}% complete")
    
    # Timeline plots summary
    print(f"\n📊 Timeline Plots: {output_dir}")
    print(f"🎨 Countries with plots: {countries_with_data}")
    
    # Week counts summary
    total_ai_weeks = sum(r['ai_weeks'] for r in week_counts_results)
    total_who_weeks = sum(r['who_weeks'] for r in week_counts_results)
    total_jhu_weeks = sum(r['jhu_weeks'] for r in week_counts_results)
    
    print(f"\n📈 Week Counts Data: {week_counts_file}")
    print(f"  Total AI weeks: {total_ai_weeks:,}")
    print(f"  Total WHO weeks: {total_who_weeks:,}")
    print(f"  Total JHU weeks: {total_jhu_weeks:,}")
    print(f"  Countries with AI data: {sum(1 for r in week_counts_results if r['ai_weeks'] > 0)}")
    print(f"  Countries with WHO data: {sum(1 for r in week_counts_results if r['who_weeks'] > 0)}")
    print(f"  Countries with JHU data: {sum(1 for r in week_counts_results if r['jhu_weeks'] > 0)}")
    
    print(f"\n🔄 DASHBOARD UPDATED:")
    print(f"📱 Real-time status based on file analysis")
    print(f"📊 Automatic metrics calculation")
    print(f"🎨 Timeline plots with synchronized date ranges")
    print(f"📈 Week counts data embedded")
    print(f"💾 All data automatically synchronized")
    print("=" * 80)

def main():
    """Main function"""
    # Get the base path (parent directory of the py directory)
    base_path = Path(__file__).parent.parent
    
    try:
        update_all_dashboard_data(base_path)
    except Exception as e:
        print(f"❌ ERROR DURING UPDATE: {e}")
        raise

if __name__ == "__main__":
    main()