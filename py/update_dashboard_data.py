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
    agent_logs = sorted(country_dir.glob('search_log_agent_*.txt'))
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
        # str(None) would render the literal text "None" in the dashboard.
        'execution_time': ('' if execution_metrics.get('total_time') is None
                           else str(execution_metrics['total_time'])),
        'queries': ('' if execution_metrics.get('total_queries') is None
                    else str(execution_metrics['total_queries'])),
        # None means "could not be determined from the logs" and renders blank;
        # 0.0 is a real measured yield and must not be blanked by a truthiness test.
        'yield_pct': ('' if execution_metrics.get('yield_pct') is None
                      else f"{execution_metrics['yield_pct']:.1f}")
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

# Structured batch-log fields emitted by templates/template_search_protocol.txt.
_RE_SUCCESSFUL = re.compile(r'Successful queries\s*:\s*(\d+)\s*/\s*(\d+)', re.I)
_RE_QUERIES = re.compile(r'^\s*Queries\s*:\s*(\d+)\s*$', re.I | re.M)
_RE_ROWS = re.compile(r'^\s*Rows added\s*:\s*(\d+)', re.I | re.M)


def calculate_execution_metrics(agent_logs: List[Path]) -> Dict:
    """Calculate execution metrics from agent log files.

    Yield is defined in CLAUDE.md as the fraction of QUERIES that produced at
    least one new row - a value that cannot exceed 100%.

    The previous implementation divided a regex count of the words
    "added|new row|cholera_data.csv" by a regex count of "WebSearch|WebFetch",
    which are unrelated quantities. It reported yields up to 2400% and was the
    reason the "3 consecutive batches below 5%" stopping rule never actually
    gated anything.

    We now read the structured `Successful queries: k/20` fields that the search
    protocol requires. When a log predates that format and the value cannot be
    determined honestly, yield is returned as None and rendered blank, rather
    than fabricating a number.
    """
    total_queries = 0
    successful_queries = 0
    rows_added = 0
    have_structured = False

    for log_file in agent_logs:
        try:
            content = log_file.read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            print(f"Warning: Could not analyze log file {log_file}: {e}")
            continue

        for k, n in _RE_SUCCESSFUL.findall(content):
            k, n = int(k), int(n)
            if n <= 0 or k > n:
                continue  # malformed batch record; ignore rather than propagate
            successful_queries += k
            total_queries += n
            have_structured = True

        if not have_structured:
            # Fall back to counting explicit per-batch query totals only.
            for n in _RE_QUERIES.findall(content):
                total_queries += int(n)

        for n in _RE_ROWS.findall(content):
            rows_added += int(n)

    yield_pct = None
    if have_structured and total_queries > 0:
        yield_pct = min(100.0, successful_queries / total_queries * 100)

    estimated_minutes = int(total_queries * 0.3)  # ~18s per query

    # None, not 0, when nothing could be parsed. A dashboard cell reading "0
    # queries" claims the agent did no work; blank correctly says the log did
    # not record it. Legacy free-text logs predate the structured batch format.
    return {
        'total_queries': total_queries if total_queries else None,
        'total_time': estimated_minutes if total_queries else None,
        'yield_pct': yield_pct,
        'data_observations': rows_added,
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

def js_object_span(html: str, decl: str):
    """(start, end) of `<decl> = { ... };` in html, or None. Braces inside
    template literals (the embedded CSV text, with backslash escapes) are
    skipped. Counting every brace is how the observations embed failed silently
    from Aug 2025: processing_notes contain "{", the closing brace was never
    found, and a stale snapshot stayed in the page."""
    import re
    m = re.search(re.escape(decl) + r"\s*=\s*\{", html)
    if not m:
        return None
    depth, in_tpl, i = 1, False, m.end()
    while i < len(html):
        c = html[i]
        if in_tpl:
            if c == "\\":
                i += 2
                continue
            if c == "`":
                in_tpl = False
        elif c == "`":
            in_tpl = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                if html[end:end + 1] == ";":
                    end += 1
                return m.start(), end
        i += 1
    return None


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
    
    # Metadata is embedded: the sources table and the observations' source links
    # use it. The observations are NOT embedded: all 40 cholera_data_ai.csv files
    # are ~94 MB, past GitHub's 100 MB file limit as an embed, so the
    # observations table fetches data/{ISO}/cholera_data_ai.csv on demand (the
    # Pages deploy publishes the whole repo with the page). embeddedCholeraData
    # stays as an empty stub.
    metadata_dict = {}
    data_dir = base_path / "data"
    for country_dir in sorted(data_dir.iterdir()):
        metadata_file = country_dir / "metadata_ai.csv"
        if not (country_dir.is_dir() and metadata_file.exists()):
            continue
        try:
            metadata_content = metadata_file.read_text(encoding="utf-8")
        except Exception as e:
            print(f"  Warning: Could not load metadata for {country_dir.name}: {e}")
            continue
        # Escape for a JS template literal: backslashes, backticks, ${ interpolation
        metadata_dict[country_dir.name] = (metadata_content.replace('\\', '\\\\').replace('`', '\\`')
                                           .replace('${', '\\${'))
        print(f"  📚 Loaded metadata for {country_dir.name}: {len(metadata_content.splitlines())-1} sources")

    items = list(metadata_dict.items())
    metadata_js_lines = ["const embeddedMetadata = {"]
    for i, (iso, content) in enumerate(items):
        comma = "," if i < len(items) - 1 else ""
        metadata_js_lines.append(f"            '{iso}': `{content}`{comma}")
    metadata_js_lines.append("        };")
    metadata_js_content = '\n'.join(metadata_js_lines)
    cholera_stub = "const embeddedCholeraData = {};"

    try:
        html_content = dashboard_file.read_text(encoding="utf-8")
        import re

        # Completion checklist (a function replacement: the CSV may hold backslashes)
        checklist_pattern = r'const completionChecklistCSV = `[^`]*`;'
        html_content = re.sub(checklist_pattern, lambda m: f'const completionChecklistCSV = `{checklist_csv_data}`;',
                              html_content, flags=re.DOTALL)
        old_pattern = r'const csvData = `[^`]*`;'
        if re.search(old_pattern, html_content):
            html_content = re.sub(old_pattern, lambda m: f'const csvData = `{checklist_csv_data}`;',
                                  html_content, flags=re.DOTALL)

        # A missing block is fatal (SystemExit is not caught below): a warning
        # here let a stale table ship for 14 months.
        span = js_object_span(html_content, "const embeddedMetadata")
        if not span:
            raise SystemExit("update_dashboard_html: 'const embeddedMetadata = {...};' not found in dashboard.html")
        html_content = html_content[:span[0]] + metadata_js_content + html_content[span[1]:]

        span = js_object_span(html_content, "const embeddedCholeraData")
        if span:
            html_content = html_content[:span[0]] + cholera_stub + html_content[span[1]:]
        else:
            mspan = js_object_span(html_content, "const embeddedMetadata")
            html_content = html_content[:mspan[1]] + "\n        " + cholera_stub + html_content[mspan[1]:]
        html_content = html_content.replace(
            "// Embedded cholera data from CSV files",
            "// Observations load on demand from data/{ISO}/cholera_data_ai.csv (not embedded: ~94 MB)")

        dashboard_file.write_text(html_content, encoding="utf-8")
        print(f"📊 Dashboard HTML updated: {dashboard_file}")
        print(f"  ✅ Embedded metadata for {len(metadata_dict)} countries; observations load on demand "
              f"from data/{{ISO}}/cholera_data_ai.csv")

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