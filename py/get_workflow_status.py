#!/usr/bin/env python3
"""
Compile workflow status from all country directories into a single CSV file.
Reads workflow_status.json files created by the workflow-orchestrator agent.
"""

import json
import pandas as pd
from pathlib import Path
import os
from datetime import datetime

def get_workflow_status():
    """Compile all workflow_status.json files into a single CSV."""
    
    # Get the base directory
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / 'data'
    
    # Load country mapping to get all MOSAIC countries
    with open(base_dir / 'reference' / 'country_mapping.json', 'r') as f:
        country_data = json.load(f)
    
    # Filter for MOSAIC framework countries only
    mosaic_countries = {k: v for k, v in country_data['countries'].items() if v.get('mosaic_framework', False)}
    
    # List to store all status data
    status_data = []
    
    # Process each country
    for iso_code, country_info in mosaic_countries.items():
        country_dir = data_dir / iso_code
        status_file = country_dir / 'workflow_status.json'
        
        # Default status if no file exists
        country_status = {
            'country': country_info['name'],
            'iso': iso_code,
            'workflow_status': 'NOT_STARTED',
            'current_agent': None,
            'agents_completed': [],
            'start_time': None,
            'last_updated': None,
            'total_sources': 0,
            'total_observations': 0,
            'data_quality_score': None,
            'completion_percentage': 0,
            'notes': 'No workflow status file found'
        }
        
        # Check if workflow status file exists
        if status_file.exists():
            try:
                with open(status_file, 'r') as f:
                    workflow_data = json.load(f)
                
                # Handle different workflow status file formats
                
                # Check if it's the new format (with 'status' and 'agents' keys)
                if 'status' in workflow_data and 'agents' in workflow_data:
                    # New format from workflow orchestrator
                    status = workflow_data.get('status', 'IN_PROGRESS').upper()
                    if status == 'COMPLETED':
                        workflow_status = 'COMPLETED'
                    else:
                        workflow_status = 'IN_PROGRESS'
                    
                    # Count completed agents
                    agents_completed = []
                    total_sources = 0
                    total_observations = 0
                    
                    for agent_key, agent_data in workflow_data.get('agents', {}).items():
                        if isinstance(agent_data, dict) and agent_data.get('status') == 'completed':
                            agents_completed.append(agent_data.get('name', agent_key))
                            total_sources += agent_data.get('sources_found', 0)
                            total_observations += agent_data.get('observations_added', 0)
                    
                    # Get current agent info
                    current_agent_info = workflow_data.get('current_agent')
                    if isinstance(current_agent_info, dict):
                        current_agent = current_agent_info.get('agent_name')
                    else:
                        current_agent = current_agent_info
                    
                    # Get timestamps
                    timestamps = workflow_data.get('timestamps', {})
                    start_time = timestamps.get('started', timestamps.get('initialized'))
                    
                    # Get data summary if available
                    data_summary = workflow_data.get('data_summary', {})
                    if data_summary:
                        total_sources = data_summary.get('total_sources', total_sources)
                        total_observations = data_summary.get('total_observations', total_observations)
                    
                    country_status.update({
                        'workflow_status': workflow_status,
                        'current_agent': current_agent,
                        'agents_completed': agents_completed,
                        'start_time': start_time,
                        'last_updated': datetime.now().isoformat(),
                        'total_sources': total_sources,
                        'total_observations': total_observations,
                        'data_quality_score': data_summary.get('quality_status') if data_summary else None,
                        'completion_percentage': round((len(agents_completed) / 6) * 100, 1),
                        'notes': workflow_data.get('notes', '')
                    })
                    
                else:
                    # Old format or custom format
                    country_status.update({
                        'workflow_status': workflow_data.get('workflow_status', 'IN_PROGRESS'),
                        'current_agent': workflow_data.get('current_agent', None),
                        'agents_completed': workflow_data.get('agents_completed', []),
                        'start_time': workflow_data.get('start_time', None),
                        'last_updated': workflow_data.get('last_updated', datetime.now().isoformat()),
                        'total_sources': workflow_data.get('total_sources', 0),
                        'total_observations': workflow_data.get('total_observations', 0),
                        'data_quality_score': workflow_data.get('data_quality_score', None),
                        'completion_percentage': workflow_data.get('completion_percentage', 0),
                        'notes': workflow_data.get('notes', '')
                    })
                    
                    # Calculate completion percentage based on agents completed
                    if 'agents_completed' in workflow_data:
                        completed_count = len(workflow_data['agents_completed'])
                        country_status['completion_percentage'] = round((completed_count / 6) * 100, 1)
                
            except json.JSONDecodeError as e:
                country_status['notes'] = f'Error reading workflow status: {str(e)}'
            except Exception as e:
                country_status['notes'] = f'Unexpected error: {str(e)}'
        
        # Convert agents_completed list to string for CSV
        country_status['agents_completed'] = ', '.join([str(a) for a in country_status['agents_completed']])
        
        status_data.append(country_status)
    
    # Create DataFrame
    df = pd.DataFrame(status_data)
    
    # Sort by status priority (COMPLETED first, then IN_PROGRESS, then NOT_STARTED)
    status_order = {'COMPLETED': 0, 'IN_PROGRESS': 1, 'NOT_STARTED': 2}
    df['status_priority'] = df['workflow_status'].map(status_order).fillna(3)
    df = df.sort_values(['status_priority', 'country']).drop('status_priority', axis=1)
    
    # Save to CSV
    output_file = base_dir / 'dashboard' / 'workflow_status_compiled.csv'
    df.to_csv(output_file, index=False)
    
    # Print summary
    print(f"Workflow Status Summary")
    print(f"=" * 50)
    print(f"Total countries: {len(df)}")
    print(f"Completed: {len(df[df['workflow_status'] == 'COMPLETED'])}")
    print(f"In Progress: {len(df[df['workflow_status'] == 'IN_PROGRESS'])}")
    print(f"Not Started: {len(df[df['workflow_status'] == 'NOT_STARTED'])}")
    print(f"\nOutput saved to: {output_file}")
    
    # Show sample of data
    print(f"\nSample of workflow status data:")
    print(df[['country', 'iso', 'workflow_status', 'current_agent', 'completion_percentage']].head(10))
    
    return df

def create_sample_workflow_status(iso_code='AGO'):
    """Create a sample workflow_status.json file for testing."""
    
    base_dir = Path(__file__).parent.parent
    status_file = base_dir / 'data' / iso_code / 'workflow_status.json'
    
    sample_data = {
        "workflow_status": "IN_PROGRESS",
        "current_agent": "agent_3_zero_transmission",
        "agents_completed": ["agent_1_baseline", "agent_2_geographic"],
        "start_time": "2025-08-04T10:00:00",
        "last_updated": datetime.now().isoformat(),
        "total_sources": 15,
        "total_observations": 42,
        "data_quality_score": 0.85,
        "completion_percentage": 33.3,
        "notes": "Currently validating zero-transmission periods"
    }
    
    # Create directory if it doesn't exist
    status_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Write sample file
    with open(status_file, 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    print(f"Created sample workflow status file at: {status_file}")

if __name__ == "__main__":
    # Optionally create a sample file for testing
    # create_sample_workflow_status('AGO')
    
    # Compile all workflow status files
    get_workflow_status()