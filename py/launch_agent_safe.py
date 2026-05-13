#!/usr/bin/env python3
"""
Safe agent launcher with memory protection and recovery capabilities.
Wraps agent execution with proper Node.js memory settings and monitoring.
"""

import os
import sys
import subprocess
import json
import psutil
import time
from datetime import datetime
from pathlib import Path

class SafeAgentLauncher:
    """Launch agents with memory protection and automatic recovery."""
    
    def __init__(self, iso_code):
        self.iso_code = iso_code
        self.data_dir = Path(f"./data/{iso_code}")
        self.log_file = self.data_dir / "agent_launcher.log"
        
        # Memory settings
        self.node_memory_mb = 8192  # 8GB for Node.js
        self.python_memory_check_interval = 30  # Check every 30 seconds
        self.max_memory_percent = 80  # Restart if using >80% of system memory
        
    def log(self, message):
        """Log message with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        print(log_entry.strip())
        with open(self.log_file, 'a') as f:
            f.write(log_entry)
            
    def get_system_memory_usage(self):
        """Get system memory usage percentage."""
        return psutil.virtual_memory().percent
        
    def create_agent_launcher_script(self, agent_num):
        """Create a launcher script with proper memory settings."""
        launcher_script = self.data_dir / f"launch_agent_{agent_num}.sh"
        
        script_content = f"""#!/bin/bash
# Agent {agent_num} launcher with memory optimization

# Set Node.js memory limit
export NODE_OPTIONS="--max-old-space-size={self.node_memory_mb}"

# Set Python optimizations
export PYTHONOPTIMIZE=1
export PYTHONHASHSEED=0

# Log start
echo "Starting Agent {agent_num} for {self.iso_code} with {self.node_memory_mb}MB Node.js heap"
echo "Time: $(date)"

# Execute the agent using the Task tool with memory management
# This would be replaced with actual Task tool invocation
python -u py/execute_agent_optimized.py {self.iso_code} {agent_num}

# Log completion
echo "Agent {agent_num} completed at $(date)"
"""
        
        with open(launcher_script, 'w') as f:
            f.write(script_content)
            
        # Make executable
        os.chmod(launcher_script, 0o755)
        
        return launcher_script
        
    def monitor_agent_process(self, process, agent_num):
        """Monitor an agent process for memory issues."""
        self.log(f"Monitoring Agent {agent_num} process (PID: {process.pid})")
        
        while process.poll() is None:
            # Check system memory
            mem_usage = self.get_system_memory_usage()
            
            if mem_usage > self.max_memory_percent:
                self.log(f"WARNING: System memory usage at {mem_usage}% - may need intervention")
                
                # Create checkpoint
                self.create_emergency_checkpoint(agent_num)
                
                # Try garbage collection first
                try:
                    process.send_signal(subprocess.signal.SIGUSR1)  # Custom signal for GC
                    time.sleep(5)
                except:
                    pass
                    
                # If still high, consider terminating
                if self.get_system_memory_usage() > 90:
                    self.log(f"CRITICAL: Terminating Agent {agent_num} due to memory pressure")
                    process.terminate()
                    time.sleep(5)
                    if process.poll() is None:
                        process.kill()
                    return "memory_exceeded"
                    
            time.sleep(self.python_memory_check_interval)
            
        return_code = process.returncode
        if return_code == 0:
            return "success"
        else:
            return f"error_code_{return_code}"
            
    def create_emergency_checkpoint(self, agent_num):
        """Create an emergency checkpoint when memory is critical."""
        checkpoint_data = {
            "agent_num": agent_num,
            "timestamp": datetime.now().isoformat(),
            "reason": "memory_pressure",
            "system_memory_percent": self.get_system_memory_usage()
        }
        
        checkpoint_file = self.data_dir / f"emergency_checkpoint_agent_{agent_num}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
            
        self.log(f"Created emergency checkpoint for Agent {agent_num}")
        
    def launch_agent_with_recovery(self, agent_num, max_retries=3):
        """Launch an agent with automatic recovery on failure."""
        for attempt in range(max_retries):
            self.log(f"Launching Agent {agent_num} (attempt {attempt + 1}/{max_retries})")
            
            # Create launcher script
            launcher_script = self.create_agent_launcher_script(agent_num)
            
            # Set environment
            env = os.environ.copy()
            env['NODE_OPTIONS'] = f'--max-old-space-size={self.node_memory_mb}'
            
            # Launch process
            process = subprocess.Popen(
                ['bash', str(launcher_script)],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Monitor process
            result = self.monitor_agent_process(process, agent_num)
            
            if result == "success":
                self.log(f"Agent {agent_num} completed successfully")
                return True
            elif result == "memory_exceeded":
                self.log(f"Agent {agent_num} exceeded memory limits")
                
                # Increase memory for next attempt
                self.node_memory_mb = min(self.node_memory_mb + 2048, 16384)
                self.log(f"Increasing Node.js heap to {self.node_memory_mb}MB for retry")
                
                # Wait before retry
                time.sleep(30)
            else:
                self.log(f"Agent {agent_num} failed with: {result}")
                
                # Check if we should retry
                if attempt < max_retries - 1:
                    time.sleep(10)
                    
        self.log(f"Agent {agent_num} failed after {max_retries} attempts")
        return False
        
    def launch_workflow(self):
        """Launch the complete workflow with memory management."""
        self.log(f"Starting workflow for {self.iso_code}")
        
        # Initialize workflow
        subprocess.run([
            sys.executable, 
            'py/initialize_workflow_files.py', 
            self.iso_code
        ])
        
        subprocess.run([
            sys.executable,
            'py/initialize_country.py',
            self.iso_code
        ])
        
        # Launch each agent
        for agent_num in range(1, 8):
            self.log(f"=== Starting Agent {agent_num} ===")
            
            success = self.launch_agent_with_recovery(agent_num)
            
            if not success:
                self.log(f"Workflow stopped at Agent {agent_num} due to failures")
                return False
                
            # Clean up between agents
            self.cleanup_between_agents()
            
            # Update dashboard
            subprocess.run(['bash', 'update_dashboard.sh'])
            
        self.log("Workflow completed successfully")
        return True
        
    def cleanup_between_agents(self):
        """Clean up resources between agent runs."""
        # Force garbage collection in Python
        import gc
        gc.collect()
        
        # Clear system caches (if we have permission)
        try:
            if sys.platform == "darwin":  # macOS
                subprocess.run(['purge'], capture_output=True)
            elif sys.platform == "linux":
                subprocess.run(['sync'], capture_output=True)
                subprocess.run(['echo', '3', '>', '/proc/sys/vm/drop_caches'], 
                             shell=True, capture_output=True)
        except:
            pass
            
        self.log("Cleaned up resources between agents")
        

def main():
    """Main entry point for safe agent launcher."""
    if len(sys.argv) < 2:
        print("Usage: python launch_agent_safe.py <ISO_CODE> [AGENT_NUM]")
        print("  <ISO_CODE>: Country code (e.g., AGO)")
        print("  [AGENT_NUM]: Optional specific agent number (1-7)")
        sys.exit(1)
        
    iso_code = sys.argv[1].upper()
    launcher = SafeAgentLauncher(iso_code)
    
    if len(sys.argv) > 2:
        # Launch specific agent
        agent_num = int(sys.argv[2])
        success = launcher.launch_agent_with_recovery(agent_num)
        sys.exit(0 if success else 1)
    else:
        # Launch complete workflow
        success = launcher.launch_workflow()
        sys.exit(0 if success else 1)
        

if __name__ == "__main__":
    main()