#!/usr/bin/env python3
"""
Memory-optimized workflow management system for cholera data collection.
Implements chunked processing, memory cleanup, and recovery mechanisms.
"""

import os
import sys
import json
import time
import psutil
import gc
import subprocess
from datetime import datetime
from pathlib import Path
import pandas as pd
import logging

class WorkflowMemoryManager:
    """Manages memory-efficient execution of cholera data collection agents."""
    
    def __init__(self, iso_code):
        self.iso_code = iso_code
        self.data_dir = Path(f"./data/{iso_code}")
        self.status_file = self.data_dir / "workflow_status.json"
        self.memory_log = self.data_dir / "memory_usage.log"
        self.checkpoint_dir = self.data_dir / "checkpoints"
        self.checkpoint_dir.mkdir(exist_ok=True)
        
        # Memory thresholds
        self.memory_threshold_mb = 3000  # Trigger cleanup at 3GB
        self.critical_memory_mb = 3500   # Force checkpoint at 3.5GB
        
        # Batch configuration
        self.batch_size = 10  # Reduced from 20 to prevent memory overflow
        self.max_retries = 3
        
        # Setup logging
        self.setup_logging()
        
    def setup_logging(self):
        """Configure memory-aware logging."""
        logging.basicConfig(
            filename=str(self.memory_log),
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def get_memory_usage(self):
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
        
    def check_memory_pressure(self):
        """Check if memory usage is approaching limits."""
        current_mb = self.get_memory_usage()
        self.logger.info(f"Current memory usage: {current_mb:.1f} MB")
        
        if current_mb > self.critical_memory_mb:
            return "critical"
        elif current_mb > self.memory_threshold_mb:
            return "high"
        return "normal"
        
    def force_garbage_collection(self):
        """Force garbage collection and log results."""
        before_mb = self.get_memory_usage()
        gc.collect()
        gc.collect()  # Second pass for circular references
        after_mb = self.get_memory_usage()
        freed_mb = before_mb - after_mb
        self.logger.info(f"Garbage collection freed {freed_mb:.1f} MB")
        return freed_mb
        
    def create_checkpoint(self, agent_num, batch_num, partial_results=None):
        """Create a checkpoint for recovery."""
        checkpoint_data = {
            "iso_code": self.iso_code,
            "agent_num": agent_num,
            "batch_num": batch_num,
            "timestamp": datetime.now().isoformat(),
            "memory_usage_mb": self.get_memory_usage(),
            "partial_results": partial_results or {}
        }
        
        checkpoint_file = self.checkpoint_dir / f"agent_{agent_num}_batch_{batch_num}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        
        self.logger.info(f"Created checkpoint: agent_{agent_num}_batch_{batch_num}")
        return checkpoint_file
        
    def load_checkpoint(self, agent_num):
        """Load the latest checkpoint for an agent."""
        checkpoints = list(self.checkpoint_dir.glob(f"agent_{agent_num}_batch_*.json"))
        if not checkpoints:
            return None
            
        # Get latest checkpoint
        latest = max(checkpoints, key=lambda p: p.stat().st_mtime)
        with open(latest, 'r') as f:
            return json.load(f)
            
    def execute_agent_with_memory_management(self, agent_num, agent_prompt):
        """Execute an agent with memory management and recovery."""
        self.logger.info(f"Starting Agent {agent_num} with memory management")
        
        # Check for existing checkpoint
        checkpoint = self.load_checkpoint(agent_num)
        start_batch = checkpoint['batch_num'] + 1 if checkpoint else 0
        
        # Update workflow status
        self.update_workflow_status(agent_num, "running")
        
        # Determine max batches based on agent
        max_batches = 10 if agent_num == 1 else 5  # Agent 1 needs more batches
        
        completed_batches = 0
        total_queries = 0
        consecutive_low_yield = 0
        
        for batch_num in range(start_batch, max_batches):
            # Check memory before each batch
            memory_status = self.check_memory_pressure()
            
            if memory_status == "critical":
                self.logger.warning(f"Critical memory pressure at batch {batch_num}")
                self.create_checkpoint(agent_num, batch_num)
                self.force_garbage_collection()
                
                # If still critical, restart the process
                if self.check_memory_pressure() == "critical":
                    self.logger.error("Memory still critical after GC, restarting agent")
                    return self.restart_agent_process(agent_num, batch_num)
                    
            elif memory_status == "high":
                self.force_garbage_collection()
                
            # Execute batch with reduced size
            batch_results = self.execute_batch(agent_num, batch_num, self.batch_size)
            
            # Track performance
            total_queries += batch_results['queries_executed']
            yield_rate = batch_results['data_yield_rate']
            
            # Check stopping criteria
            if agent_num == 1 and completed_batches >= 5:
                if yield_rate < 0.05:  # Less than 5% yield
                    consecutive_low_yield += 1
                    if consecutive_low_yield >= 2:
                        self.logger.info(f"Stopping Agent {agent_num}: 2 consecutive low-yield batches")
                        break
                else:
                    consecutive_low_yield = 0
                    
            completed_batches += 1
            
            # Create checkpoint after each successful batch
            self.create_checkpoint(agent_num, batch_num, batch_results)
            
            # Clear batch results from memory
            del batch_results
            gc.collect()
            
        # Update final status
        self.update_workflow_status(agent_num, "completed", {
            "total_queries": total_queries,
            "batches_completed": completed_batches
        })
        
        self.logger.info(f"Agent {agent_num} completed: {total_queries} queries in {completed_batches} batches")
        
    def execute_batch(self, agent_num, batch_num, batch_size):
        """Execute a single batch with memory constraints."""
        # This is a placeholder for the actual batch execution
        # In practice, this would interface with the Task tool
        return {
            "queries_executed": batch_size,
            "data_yield_rate": 0.1 if batch_num < 3 else 0.03,  # Simulate declining yield
            "observations_added": 5 if batch_num < 3 else 1
        }
        
    def restart_agent_process(self, agent_num, from_batch):
        """Restart an agent process from a specific batch."""
        self.logger.info(f"Restarting Agent {agent_num} from batch {from_batch}")
        
        # Create restart command
        restart_script = f"""
import subprocess
import sys

# Increase Node.js memory limit
env = os.environ.copy()
env['NODE_OPTIONS'] = '--max-old-space-size=8192'

# Execute agent with increased memory
subprocess.run([
    sys.executable,
    'py/execute_agent_from_checkpoint.py',
    '{self.iso_code}',
    '{agent_num}',
    '{from_batch}'
], env=env)
"""
        
        restart_file = self.data_dir / f"restart_agent_{agent_num}.py"
        with open(restart_file, 'w') as f:
            f.write(restart_script)
            
        # Execute restart
        subprocess.run([sys.executable, str(restart_file)])
        
    def update_workflow_status(self, agent_num, status, metrics=None):
        """Update workflow status with memory-aware tracking."""
        if not self.status_file.exists():
            return
            
        with open(self.status_file, 'r') as f:
            workflow_status = json.load(f)
            
        workflow_status['agents'][str(agent_num)] = {
            "status": status,
            "last_update": datetime.now().isoformat(),
            "memory_usage_mb": self.get_memory_usage(),
            **(metrics or {})
        }
        
        with open(self.status_file, 'w') as f:
            json.dump(workflow_status, f, indent=2)
            
    def optimize_workflow_execution(self):
        """Main entry point for optimized workflow execution."""
        self.logger.info(f"Starting optimized workflow for {self.iso_code}")
        
        # Set Node.js memory limit
        os.environ['NODE_OPTIONS'] = '--max-old-space-size=8192'
        
        # Execute each agent with memory management
        for agent_num in range(1, 8):
            self.logger.info(f"Preparing Agent {agent_num}")
            
            # Clear memory before each agent
            self.force_garbage_collection()
            
            # Load agent prompt
            agent_prompt = self.load_agent_prompt(agent_num)
            
            # Execute with memory management
            self.execute_agent_with_memory_management(agent_num, agent_prompt)
            
            # Clean up after agent
            self.cleanup_agent_artifacts(agent_num)
            
        self.logger.info("Workflow completed successfully")
        
    def load_agent_prompt(self, agent_num):
        """Load agent prompt from orchestrator file."""
        orchestrator_file = self.data_dir / "search_log_agent_0.txt"
        # In practice, this would parse the orchestrator file for the specific agent prompt
        return f"Agent {agent_num} prompt placeholder"
        
    def cleanup_agent_artifacts(self, agent_num):
        """Clean up temporary files and free memory after agent completion."""
        # Remove old checkpoints
        for checkpoint in self.checkpoint_dir.glob(f"agent_{agent_num}_*.json"):
            if (datetime.now() - datetime.fromtimestamp(checkpoint.stat().st_mtime)).days > 1:
                checkpoint.unlink()
                
        # Force garbage collection
        self.force_garbage_collection()
        

def main():
    """Main entry point for memory-managed workflow execution."""
    if len(sys.argv) < 2:
        print("Usage: python workflow_memory_manager.py <ISO_CODE>")
        sys.exit(1)
        
    iso_code = sys.argv[1].upper()
    manager = WorkflowMemoryManager(iso_code)
    manager.optimize_workflow_execution()
    

if __name__ == "__main__":
    main()