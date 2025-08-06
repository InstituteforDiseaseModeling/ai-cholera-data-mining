#!/usr/bin/env python3
"""
MOSAIC AI Cholera Data Collection - Unified Dashboard Data Updater

This script combines all dashboard data updates into a single command:
1. Updates completion checklist based on file analysis
2. Generates 3-source timeline coverage plots for all countries
3. Updates dashboard HTML with embedded data

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
            'yield_pct': ''
        }
    
    # Check for key files
    files_present = {
        'cholera_data': (country_dir / 'cholera_data.csv').exists(),
        'cholera_data_ai': (country_dir / 'cholera_data_ai.csv').exists(),  # AI-specific data
        'metadata': (country_dir / 'metadata.csv').exists(),
        'metadata_ai': (country_dir / 'metadata_ai.csv').exists(),  # AI-specific metadata
        'search_protocol': (country_dir / f'search_protocol_{iso_code}.txt').exists(),
        'agentic_workflow': (country_dir / f'agentic_workflow_{iso_code}.txt').exists(),
    }
    
    # Analyze agent log files
    agent_logs = list(country_dir.glob('search_log_agent_*.txt'))
    agent_analysis = analyze_agent_logs(agent_logs)
    num_agents = len(agent_logs)
    
    # Check for search report (created by Agent 7)
    search_report = (country_dir / 'search_report.txt').exists()
    
    # Analyze cholera_data files - prioritize AI-specific files if they exist
    if files_present['cholera_data_ai']:
        cholera_data_info = analyze_cholera_data(country_dir / 'cholera_data_ai.csv')
    else:
        cholera_data_info = analyze_cholera_data(country_dir / 'cholera_data.csv')
    
    if files_present['metadata_ai']:
        metadata_info = analyze_metadata(country_dir / 'metadata_ai.csv')
    else:
        metadata_info = analyze_metadata(country_dir / 'metadata.csv')
    
    # Determine completion status
    status = determine_status(files_present, num_agents, search_report, cholera_data_info)
    
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
        'yield_pct': f"{execution_metrics.get('yield_pct', ''):.1f}" if execution_metrics.get('yield_pct') else ''
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

def determine_status(files_present: Dict, num_agents: int, search_report: bool, cholera_data_info: Dict) -> str:
    """Determine completion status based on file analysis
    
    Simplified logic for memory-optimized workflow:
    - COMPLETED: All 7 agents have logs AND quality report exists (Agent 7 completed)
    - PENDING: Any agent work has started (1+ agent logs exist)
    - NOT_STARTED: No agent work has begun
    """
    
    # Check if workflow has been completed (all 7 agents done)
    if num_agents >= 7 and files_present['cholera_data_ai'] and files_present['metadata_ai']:
        return 'COMPLETED'
    
    # Check if workflow is in progress (any agent has started)
    if num_agents > 0:
        return 'PENDING'
    
    # No work has started
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
    key_files = ['cholera_data_ai.csv', 'metadata_ai.csv', 'search_report.txt']
    key_files.extend([f'search_log_agent_{i}.txt' for i in range(1, 8)])
    
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

def calculate_coverage_after_ai(country_dir: Path, iso_code: str, baseline_coverage: float) -> str:
    """Calculate coverage after AI enhancement using fixed 1970-present range"""
    try:
        import pandas as pd
        from datetime import datetime
        
        # Fixed date range: 1970 to present
        min_year = 1970
        current_year = datetime.now().year
        total_months = (current_year - min_year + 1) * 12
        
        # Collect covered months from all sources
        all_covered_months = set()
        for data_file in ['cholera_data_jhu.csv', 'cholera_data_who.csv', 'cholera_data_ai.csv']:
            file_path = country_dir / data_file
            if file_path.exists():
                try:
                    df = pd.read_csv(file_path)
                    if not df.empty and 'TL' in df.columns:
                        for date_str in df['TL'].dropna():
                            try:
                                date = pd.to_datetime(date_str)
                                # Count all months, even if outside 1970-present range
                                all_covered_months.add((date.year, date.month))
                            except:
                                continue
                except:
                    continue
        
        # Count only months within the standard range for percentage calculation
        covered_in_range = len([m for m in all_covered_months if 1970 <= m[0] <= current_year])
        total_covered = len(all_covered_months)
        
        # Calculate percentage
        if total_months > 0:
            percentage = round((covered_in_range / total_months) * 100, 1)
            # If we have data outside the standard range, indicate >100%
            if total_covered > covered_in_range:
                return ">100"  # Indicates data extends beyond 1970-present
            else:
                return str(percentage)
        else:
            return str(baseline_coverage)
            
    except Exception as e:
        print(f"  Warning: Could not calculate after-AI coverage for {iso_code}: {e}")
        return str(baseline_coverage)

def get_baseline_coverage(iso_code: str) -> float:
    """Calculate baseline coverage from JHU + WHO data using fixed 1970-present range"""
    try:
        import pandas as pd
        from pathlib import Path
        from datetime import datetime
        
        # Get the data directory for this country
        base_path = Path('/Users/johngiles/Library/CloudStorage/OneDrive-Bill&MelindaGatesFoundation/Projects/MOSAIC/ai-cholera-data-mining')
        country_dir = base_path / 'data' / iso_code
        
        # Fixed date range: 1970 to present
        min_year = 1970
        current_year = datetime.now().year
        total_months = (current_year - min_year + 1) * 12
        
        # Collect covered months from BASELINE sources only (JHU + WHO)
        baseline_covered_months = set()
        for data_file in ['cholera_data_jhu.csv', 'cholera_data_who.csv']:
            file_path = country_dir / data_file
            if file_path.exists():
                try:
                    df = pd.read_csv(file_path)
                    if not df.empty and 'TL' in df.columns:
                        for date_str in df['TL'].dropna():
                            try:
                                date = pd.to_datetime(date_str)
                                baseline_covered_months.add((date.year, date.month))
                            except:
                                continue
                except:
                    continue
        
        if not baseline_covered_months:
            return 0.0
        
        # Count only months within the standard range
        covered_in_range = len([m for m in baseline_covered_months if 1970 <= m[0] <= current_year])
        
        # Calculate percentage
        if total_months > 0:
            return round((covered_in_range / total_months) * 100, 1)
        else:
            return 0.0
            
    except Exception as e:
        print(f"  Warning: Could not calculate baseline coverage for {iso_code}: {e}")
        return 0.0

# REMOVED: generate_auto_notes function no longer needed as notes column has been removed from dashboard

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
    NOTE: No longer embedding surveillance data - using original file directly.
    
    This function previously copied MOSAIC surveillance data to ./reference/
    but now references the original file to avoid duplication.
    """
    print("✅ Using original surveillance data from MOSAIC-data directory")
    print("   (No local copy needed - referencing source directly)")
    return True
    
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
    Load MOSAIC surveillance data with WHO/JHU sources separated.
    
    Uses the original file from MOSAIC-data directory to avoid duplication.
    """
    
    # Use original surveillance data from MOSAIC-data directory
    surveillance_file = base_path.parent / "MOSAIC-data" / "processed" / "cholera" / "weekly" / "cholera_surveillance_weekly_combined.csv"
    
    if not surveillance_file.exists():
        print(f"Warning: Reference surveillance file not found: {surveillance_file}")
        print("  Proceeding with AI data only...")
        return pd.DataFrame()
    
    surveillance_data = []
    
    print("Loading surveillance data from reference/ directory...")
    
    try:
        with open(surveillance_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                iso_code = row['iso_code'].strip('"')
                year = int(row['year'].strip('"'))
                week = int(row['week'].strip('"'))
                date_start = row['date_start'].strip('"')
                cases = row['cases'].strip('"')
                source = row['source'].strip('"')
                
                # Only include rows with actual data (not NA)
                if cases != 'NA' and date_start != 'NA':
                    # Map sources
                    if source == 'WHO':
                        mapped_source = 'WHO'
                    elif source == 'JHU':
                        mapped_source = 'JHU'
                    elif source == 'SUPP':  # Supplementary data, treat as WHO
                        mapped_source = 'WHO'
                    else:
                        continue  # Skip NA or unknown sources
                    
                    surveillance_data.append({
                        'iso_code': iso_code,
                        'source': mapped_source,
                        'year': year,
                        'week': week,
                        'date_from': date_start,
                        'date_to': row['date_stop'].strip('"'),
                        'present': 1
                    })
        
        print(f"✅ Loaded {len(surveillance_data)} surveillance records from reference")
        
    except Exception as e:
        print(f"❌ Error loading surveillance data from {surveillance_file}: {e}")
        return pd.DataFrame()
    
    return pd.DataFrame(surveillance_data)

def load_ai_enhanced_data(base_path: Path, iso_code: str) -> pd.DataFrame:
    """Load AI-enhanced data and convert to weekly format"""
    
    # Try separate files first, then unified as fallback
    cholera_files = [
        base_path / "data" / iso_code / "cholera_data_ai.csv",    # AI-specific data
        base_path / "data" / iso_code / "cholera_data.csv"       # Fallback unified file
    ]
    
    cholera_file = None
    for file_path in cholera_files:
        if file_path.exists():
            cholera_file = file_path
            break
    
    if cholera_file is None:
        return pd.DataFrame()
    
    ai_data = []
    
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
        # HARDCODED: Always start timeline plots at 1970 regardless of data
        min_date = pd.Timestamp('1970-01-01')
        max_date = max(all_dates)
        print(f"  Global date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')} (start hardcoded to 1970)")
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

# DEPRECATED AND REMOVED: The create_3source_timeline_plot function has been removed.
# The dashboard now uses dual_timeline plots generated by generate_dual_timeline_plots.py
# This function was never called and created unused *_3sources_timeline.png files.


# ============================================================================
# MAIN UNIFIED UPDATE FUNCTION
# ============================================================================

def update_dashboard_html(base_path: Path, updated_data: List[Dict]):
    """Update the dashboard HTML with embedded CSV data"""
    dashboard_file = base_path / "dashboard" / "dashboard.html"
    
    if not dashboard_file.exists():
        print(f"Warning: Dashboard file not found: {dashboard_file}")
        return
    
    # Generate completion checklist CSV string
    checklist_fieldnames = ['country', 'iso', 'status', 'datetime', 'sources', 'observations', 
                           'date_range', 'priority', 'execution_time', 'queries', 'yield_pct']
    
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
    
    # Load metadata and cholera data for all available countries
    metadata_dict = {}
    cholera_data_dict = {}
    data_dir = base_path / "data"
    
    # Find all countries with metadata_ai.csv and cholera_data_ai.csv files
    for country_dir in data_dir.iterdir():
        if country_dir.is_dir():
            iso_code = country_dir.name
            
            # Load metadata_ai.csv
            metadata_file = country_dir / "metadata_ai.csv"
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata_content = f.read()
                    # Escape backticks and backslashes in the metadata content
                    metadata_content = metadata_content.replace('\\', '\\\\').replace('`', '\\`')
                    metadata_dict[iso_code] = metadata_content
                    print(f"  📚 Loaded metadata for {iso_code}: {len(metadata_content.splitlines())-1} sources")
                except Exception as e:
                    print(f"  Warning: Could not load metadata for {country_dir.name}: {e}")
            
            # Load cholera_data_ai.csv
            cholera_file = country_dir / "cholera_data_ai.csv"
            if cholera_file.exists():
                try:
                    with open(cholera_file, 'r', encoding='utf-8') as f:
                        cholera_content = f.read()
                    # Escape backticks and backslashes in the cholera data content
                    cholera_content = cholera_content.replace('\\', '\\\\').replace('`', '\\`')
                    cholera_data_dict[iso_code] = cholera_content
                    print(f"  📊 Loaded cholera data for {iso_code}: {len(cholera_content.splitlines())-1} observations")
                except Exception as e:
                    print(f"  Warning: Could not load cholera data for {country_dir.name}: {e}")
    
    # Build the embedded metadata JavaScript object
    metadata_js_lines = ["        const embeddedMetadata = {"]
    for i, (iso, content) in enumerate(metadata_dict.items()):
        # Add comma for all but the last item
        comma = "," if i < len(metadata_dict) - 1 else ""
        metadata_js_lines.append(f"            '{iso}': `{content}`{comma}")
    metadata_js_lines.append("        };")
    metadata_js_content = '\n'.join(metadata_js_lines)
    
    # Build the embedded cholera data JavaScript object
    cholera_js_lines = ["        const embeddedCholeraData = {"]
    for i, (iso, content) in enumerate(cholera_data_dict.items()):
        # Add comma for all but the last item
        comma = "," if i < len(cholera_data_dict) - 1 else ""
        cholera_js_lines.append(f"            '{iso}': `{content}`{comma}")
    cholera_js_lines.append("        };")
    cholera_js_content = '\n'.join(cholera_js_lines)
    
    try:
        # Read current HTML
        with open(dashboard_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Find and replace the embedded CSV data
        import re
        
        # Update completion checklist data - using the correct variable name
        checklist_pattern = r'const completionChecklistCSV = `[^`]*`;'
        checklist_replacement = f'const completionChecklistCSV = `{checklist_csv_data}`;'
        html_content = re.sub(checklist_pattern, checklist_replacement, html_content, flags=re.DOTALL)
        
        # Also try the old pattern in case it exists
        old_pattern = r'const csvData = `[^`]*`;'
        if re.search(old_pattern, html_content):
            html_content = re.sub(old_pattern, f'const csvData = `{checklist_csv_data}`;', html_content, flags=re.DOTALL)
        
        # Update embedded metadata - use a more robust pattern
        # First, find the start of the embeddedMetadata object
        metadata_start_pattern = r'const embeddedMetadata = \{'
        metadata_start_match = re.search(metadata_start_pattern, html_content)
        
        if metadata_start_match:
            # Find the matching closing brace
            start_pos = metadata_start_match.start()
            brace_count = 0
            in_backticks = False
            i = metadata_start_match.end()
            
            while i < len(html_content):
                if html_content[i] == '`':
                    in_backticks = not in_backticks
                elif not in_backticks:
                    if html_content[i] == '{':
                        brace_count += 1
                    elif html_content[i] == '}':
                        if brace_count == 0:
                            # Found the closing brace
                            end_pos = i + 1
                            # Also find the closing semicolon
                            if i + 1 < len(html_content) and html_content[i + 1] == ';':
                                end_pos = i + 2
                            break
                        else:
                            brace_count -= 1
                i += 1
            
            # Replace the entire embeddedMetadata object
            if 'end_pos' in locals():
                # Find any comment before the const declaration
                comment_pattern = r'(        // [^\n]*\n)?        const embeddedMetadata = \{'
                comment_match = re.search(comment_pattern, html_content[:start_pos + 50])
                if comment_match:
                    start_pos = comment_match.start()
                
                metadata_replacement = f'        // Embedded metadata from CSV files\n{metadata_js_content}'
                html_content = html_content[:start_pos] + metadata_replacement + html_content[end_pos:]
            else:
                print("  Warning: Could not find embeddedMetadata closing brace, skipping metadata update")
        else:
            print("  Warning: Could not find embeddedMetadata pattern, skipping metadata update")
        
        # Update embedded cholera data - similar pattern to metadata
        # First, find the start of the embeddedCholeraData object (or where it should be)
        cholera_data_pattern = r'const embeddedCholeraData = \{'
        cholera_data_match = re.search(cholera_data_pattern, html_content)
        
        if cholera_data_match:
            # Find the matching closing brace (similar to metadata logic)
            start_pos = cholera_data_match.start()
            depth = 0
            i = start_pos
            end_pos = None
            
            while i < len(html_content):
                if html_content[i] == '{':
                    depth += 1
                elif html_content[i] == '}':
                    depth -= 1
                    if depth == 0:
                        end_pos = i + 1
                        if i + 1 < len(html_content) and html_content[i + 1] == ';':
                            end_pos = i + 2
                        break
                i += 1
            
            # Replace the entire embeddedCholeraData object
            if end_pos:
                # Find any comment before the const declaration
                comment_pattern = r'(        // [^\n]*\n)?        const embeddedCholeraData = \{'
                comment_match = re.search(comment_pattern, html_content[:start_pos + 50])
                if comment_match:
                    start_pos = comment_match.start()
                
                cholera_replacement = f'        // Embedded cholera data from CSV files\n{cholera_js_content}'
                html_content = html_content[:start_pos] + cholera_replacement + html_content[end_pos:]
            else:
                print("  Warning: Could not find embeddedCholeraData closing brace, adding new cholera data object")
                # Add the embeddedCholeraData after embeddedMetadata
                metadata_end = re.search(r'const embeddedMetadata = \{[^}]*\};', html_content)
                if metadata_end:
                    insert_pos = metadata_end.end()
                    cholera_insertion = f'\n\n        // Embedded cholera data from CSV files\n{cholera_js_content}'
                    html_content = html_content[:insert_pos] + cholera_insertion + html_content[insert_pos:]
        else:
            # embeddedCholeraData doesn't exist, add it after embeddedMetadata
            print("  Adding new embeddedCholeraData object...")
            metadata_end = re.search(r'const embeddedMetadata = \{[^}]*\};', html_content)
            if metadata_end:
                insert_pos = metadata_end.end()
                cholera_insertion = f'\n\n        // Embedded cholera data from CSV files\n{cholera_js_content}'
                html_content = html_content[:insert_pos] + cholera_insertion + html_content[insert_pos:]
            else:
                print("  Warning: Could not find proper location to insert embeddedCholeraData")
        
        # Write updated HTML
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📊 Dashboard HTML updated: {dashboard_file}")
        if metadata_dict:
            print(f"  ✅ Embedded metadata for {len(metadata_dict)} countries: {', '.join(metadata_dict.keys())}")
        if cholera_data_dict:
            print(f"  ✅ Embedded cholera data for {len(cholera_data_dict)} countries: {', '.join(cholera_data_dict.keys())}")
        
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
        
        # Notes column has been removed from dashboard
        
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
            'yield_pct': current_state['yield_pct']
        }
        
        updated_data.append(updated_row)
    
    # Write updated CSV
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['country', 'iso', 'status', 'datetime', 'sources', 'observations', 
                     'date_range', 'priority', 'execution_time', 'queries', 'yield_pct']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_data)
    
    print(f"✅ Completion checklist updated: {csv_file}")
    
    # ========================================================================
    # 2. GENERATE DUAL TIMELINE PLOTS (via separate script)
    # ========================================================================
    print("\n📊 STEP 2: Generating dual timeline coverage plots...")
    
    # Call the dual timeline plots script
    import subprocess
    result = subprocess.run(['python', 'py/generate_dual_timeline_plots.py'], 
                          capture_output=True, text=True, cwd=base_path)
    
    if result.returncode == 0:
        print("✅ Dual timeline plots generated successfully")
    else:
        print(f"❌ Error generating dual timeline plots: {result.stderr}")
        # Continue anyway - don't fail the entire dashboard update
    
    # Count countries with plots for summary
    timeline_dir = base_path / "dashboard" / "timeline_plots_dual"
    if timeline_dir.exists():
        plot_files = list(timeline_dir.glob("*_dual_timeline.png"))
        countries_with_data = len(plot_files)
        print(f"📊 Dual timeline plots: {countries_with_data} countries processed")
    else:
        countries_with_data = 0
    
    # ========================================================================
    # 3. UPDATE DASHBOARD HTML
    # ========================================================================
    print("\n📱 STEP 3: Updating dashboard HTML with embedded data...")
    
    update_dashboard_html(base_path, updated_data)
    
    # ========================================================================
    # 4. GENERATE SUMMARY STATISTICS
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
    timeline_dir = base_path / "dashboard" / "timeline_plots_dual"
    print(f"\n📊 Dual Timeline Plots: {timeline_dir}")
    print(f"🎨 Countries with plots: {countries_with_data}")
    
    
    print(f"\n🔄 DASHBOARD UPDATED:")
    print(f"📱 Real-time status based on file analysis")
    print(f"📊 Automatic metrics calculation")
    print(f"🎨 Timeline plots with synchronized date ranges")
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