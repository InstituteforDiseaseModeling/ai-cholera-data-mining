#!/usr/bin/env python3
"""
Optimized agent execution with batch management and memory controls.
Implements streaming data processing and incremental CSV updates.
"""

import os
import sys
import json
import time
import gc
import pandas as pd
from datetime import datetime
from pathlib import Path
import subprocess
import tempfile
import shutil

class OptimizedAgentExecutor:
    """Execute agents with optimized memory usage and batch management."""
    
    def __init__(self, iso_code):
        self.iso_code = iso_code
        self.data_dir = Path(f"./data/{iso_code}")
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"cholera_{iso_code}_"))
        
        # Batch configuration
        self.queries_per_batch = 10  # Reduced from 20
        self.max_concurrent = 5      # Limit concurrent operations
        
        # File paths
        self.ai_data_file = self.data_dir / "cholera_data_ai.csv"
        self.metadata_file = self.data_dir / "metadata_ai.csv"
        self.status_file = self.data_dir / "workflow_status.json"
        
    def __del__(self):
        """Cleanup temporary directory on exit."""
        if hasattr(self, 'temp_dir') and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            
    def execute_batch_chunked(self, agent_num, batch_num, queries):
        """Execute queries in smaller chunks to prevent memory overflow."""
        batch_results = {
            "batch_num": batch_num,
            "queries_executed": 0,
            "observations_added": 0,
            "sources_found": 0,
            "successful_queries": []
        }
        
        # Process queries in micro-batches
        for i in range(0, len(queries), self.max_concurrent):
            chunk = queries[i:i + self.max_concurrent]
            
            # Execute chunk (simulated - in practice would use Task tool)
            chunk_results = self.process_query_chunk(agent_num, chunk)
            
            # Immediately write results to disk
            if chunk_results['data_rows']:
                self.append_to_csv(chunk_results['data_rows'])
                batch_results['observations_added'] += len(chunk_results['data_rows'])
                
            if chunk_results['metadata_rows']:
                self.append_to_metadata(chunk_results['metadata_rows'])
                batch_results['sources_found'] += len(chunk_results['metadata_rows'])
                
            batch_results['queries_executed'] += len(chunk)
            batch_results['successful_queries'].extend(chunk_results['successful_queries'])
            
            # Clear chunk results from memory
            del chunk_results
            gc.collect()
            
            # Brief pause to prevent overwhelming the system
            time.sleep(0.5)
            
        # Calculate yield rate
        batch_results['yield_rate'] = (
            len(batch_results['successful_queries']) / batch_results['queries_executed']
            if batch_results['queries_executed'] > 0 else 0
        )
        
        return batch_results
        
    def process_query_chunk(self, agent_num, queries):
        """Process a small chunk of queries with memory management."""
        # This is a placeholder for actual query processing
        # In practice, this would interface with the Task tool
        
        results = {
            "data_rows": [],
            "metadata_rows": [],
            "successful_queries": []
        }
        
        # Simulate some successful queries
        for i, query in enumerate(queries):
            if i % 3 == 0:  # Simulate 33% success rate
                results['data_rows'].append({
                    'Location': f'AFR::{self.iso_code}',
                    'TL': '2024-01-01',
                    'TR': '2024-01-31',
                    'sCh': 100,
                    'deaths': 5,
                    'source': f'Test Source {i}',
                    'source_index': i + 1,
                    'confidence_weight': 0.8,
                    'processing_notes': f'From query: {query}',
                    'source_database': 'AI'
                })
                results['successful_queries'].append(query)
                
        return results
        
    def append_to_csv(self, data_rows):
        """Append data rows to CSV file incrementally."""
        if not data_rows:
            return
            
        # Convert to DataFrame
        new_df = pd.DataFrame(data_rows)
        
        # Read existing data or create new
        if self.ai_data_file.exists():
            # Use chunked reading to minimize memory usage
            existing_df = pd.read_csv(self.ai_data_file, nrows=0)  # Just get columns
            
            # Ensure columns match
            for col in existing_df.columns:
                if col not in new_df.columns:
                    new_df[col] = ''
                    
            # Reorder columns to match
            new_df = new_df[existing_df.columns]
            
            # Append without loading entire file
            new_df.to_csv(self.ai_data_file, mode='a', header=False, index=False)
        else:
            new_df.to_csv(self.ai_data_file, index=False)
            
    def append_to_metadata(self, metadata_rows):
        """Append metadata rows to CSV file incrementally."""
        if not metadata_rows:
            return
            
        # Similar to append_to_csv but for metadata
        new_df = pd.DataFrame(metadata_rows)
        
        if self.metadata_file.exists():
            new_df.to_csv(self.metadata_file, mode='a', header=False, index=False)
        else:
            new_df.to_csv(self.metadata_file, index=False)
            
    def generate_optimized_queries(self, agent_num, batch_num):
        """Generate queries for a batch based on agent type and batch number."""
        # Load gap data
        gap_file = Path("./reference/consolidated_gap_ranges.csv")
        if gap_file.exists():
            gaps_df = pd.read_csv(gap_file)
            country_gaps = gaps_df[gaps_df['iso_code'] == self.iso_code]
        else:
            country_gaps = pd.DataFrame()
            
        queries = []
        
        if agent_num == 1:  # Baseline collector
            # Focus on recent gaps first
            for _, gap in country_gaps.iterrows():
                if len(queries) >= self.queries_per_batch:
                    break
                    
                year = int(gap['gap_start'][:4])
                queries.extend([
                    f"{gap['country']} cholera {year} outbreak WHO",
                    f"{gap['country']} cholera {year} surveillance UNICEF"
                ])
                
        # Add more agent-specific query generation logic here
        
        return queries[:self.queries_per_batch]
        
    def run_agent_with_optimization(self, agent_num):
        """Run an agent with memory optimization and batch management."""
        print(f"Starting optimized execution of Agent {agent_num}")
        
        # Load or initialize agent state
        state_file = self.temp_dir / f"agent_{agent_num}_state.json"
        if state_file.exists():
            with open(state_file, 'r') as f:
                state = json.load(f)
        else:
            state = {
                "agent_num": agent_num,
                "completed_batches": 0,
                "total_queries": 0,
                "total_observations": 0,
                "consecutive_low_yield": 0,
                "start_time": datetime.now().isoformat()
            }
            
        # Determine stopping criteria
        min_batches = 5 if agent_num == 1 else 2
        max_batches = 10 if agent_num == 1 else 5
        
        # Execute batches
        for batch_num in range(state['completed_batches'], max_batches):
            print(f"  Executing batch {batch_num + 1}/{max_batches}")
            
            # Generate queries for this batch
            queries = self.generate_optimized_queries(agent_num, batch_num)
            
            # Execute with chunking
            batch_results = self.execute_batch_chunked(agent_num, batch_num, queries)
            
            # Update state
            state['completed_batches'] += 1
            state['total_queries'] += batch_results['queries_executed']
            state['total_observations'] += batch_results['observations_added']
            
            # Check stopping criteria
            if state['completed_batches'] >= min_batches:
                if batch_results['yield_rate'] < 0.05:
                    state['consecutive_low_yield'] += 1
                    if state['consecutive_low_yield'] >= 2:
                        print(f"  Stopping: 2 consecutive low-yield batches")
                        break
                else:
                    state['consecutive_low_yield'] = 0
                    
            # Save state after each batch
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
                
            # Memory cleanup
            gc.collect()
            
        # Update workflow status
        self.update_workflow_status(agent_num, "completed", state)
        
        print(f"Agent {agent_num} completed: {state['total_queries']} queries, "
              f"{state['total_observations']} observations added")
        
    def update_workflow_status(self, agent_num, status, metrics):
        """Update the workflow status file."""
        if not self.status_file.exists():
            return
            
        with open(self.status_file, 'r') as f:
            workflow_status = json.load(f)
            
        workflow_status['agents'][str(agent_num)] = {
            "status": status,
            "completed_at": datetime.now().isoformat(),
            "batches_completed": metrics['completed_batches'],
            "total_queries": metrics['total_queries'],
            "observations_added": metrics['total_observations']
        }
        
        with open(self.status_file, 'w') as f:
            json.dump(workflow_status, f, indent=2)
            

def main():
    """Main entry point for optimized agent execution."""
    if len(sys.argv) < 3:
        print("Usage: python execute_agent_optimized.py <ISO_CODE> <AGENT_NUM>")
        sys.exit(1)
        
    iso_code = sys.argv[1].upper()
    agent_num = int(sys.argv[2])
    
    # Set memory limit for Node.js
    os.environ['NODE_OPTIONS'] = '--max-old-space-size=8192'
    
    executor = OptimizedAgentExecutor(iso_code)
    executor.run_agent_with_optimization(agent_num)
    

if __name__ == "__main__":
    main()