#!/usr/bin/env python3
"""
Test script to verify memory optimization improvements.
"""

import os
import sys
import psutil
import subprocess
import time
from pathlib import Path

def test_memory_settings():
    """Test that memory settings are properly configured."""
    print("=== Testing Memory Configuration ===")
    
    # Check Node.js memory settings
    node_options = os.environ.get('NODE_OPTIONS', 'Not set')
    print(f"NODE_OPTIONS: {node_options}")
    
    # Check system memory
    mem = psutil.virtual_memory()
    print(f"System Memory: {mem.total / (1024**3):.1f} GB total, {mem.available / (1024**3):.1f} GB available")
    print(f"Memory Usage: {mem.percent}%")
    
    # Test Node.js heap
    test_script = """
    const v8 = require('v8');
    const stats = v8.getHeapStatistics();
    console.log('Heap Size Limit:', Math.round(stats.heap_size_limit / 1024 / 1024), 'MB');
    console.log('Total Heap Size:', Math.round(stats.total_heap_size / 1024 / 1024), 'MB');
    console.log('Used Heap Size:', Math.round(stats.used_heap_size / 1024 / 1024), 'MB');
    """
    
    with open('test_heap.js', 'w') as f:
        f.write(test_script)
    
    print("\nNode.js Heap Configuration:")
    result = subprocess.run(['node', 'test_heap.js'], capture_output=True, text=True)
    print(result.stdout)
    
    os.remove('test_heap.js')
    
def test_batch_processing():
    """Test batch processing with memory monitoring."""
    print("\n=== Testing Batch Processing ===")
    
    from execute_agent_optimized import OptimizedAgentExecutor
    
    # Create test executor
    executor = OptimizedAgentExecutor("TEST")
    
    print(f"Batch size: {executor.queries_per_batch}")
    print(f"Max concurrent: {executor.max_concurrent}")
    
    # Test query generation
    queries = executor.generate_optimized_queries(1, 0)
    print(f"Generated {len(queries)} queries for batch")
    
    # Monitor memory during batch simulation
    print("\nSimulating batch processing...")
    initial_mem = psutil.Process().memory_info().rss / 1024 / 1024
    
    # Simulate processing
    for i in range(3):
        print(f"  Batch {i+1}...")
        time.sleep(1)
        current_mem = psutil.Process().memory_info().rss / 1024 / 1024
        print(f"    Memory: {current_mem:.1f} MB (Δ{current_mem - initial_mem:+.1f} MB)")
    
def test_recovery_mechanism():
    """Test checkpoint and recovery functionality."""
    print("\n=== Testing Recovery Mechanisms ===")
    
    from workflow_memory_manager import WorkflowMemoryManager
    
    # Create test manager
    manager = WorkflowMemoryManager("TEST")
    
    # Test checkpoint creation
    checkpoint_file = manager.create_checkpoint(1, 3, {"test": "data"})
    print(f"Created checkpoint: {checkpoint_file}")
    
    # Test checkpoint loading
    loaded = manager.load_checkpoint(1)
    if loaded:
        print(f"Loaded checkpoint: Agent {loaded['agent_num']}, Batch {loaded['batch_num']}")
    
    # Clean up
    checkpoint_file.unlink()
    
def main():
    """Run all tests."""
    print("Memory Optimization Test Suite")
    print("=" * 50)
    
    # Set memory options for testing
    os.environ['NODE_OPTIONS'] = '--max-old-space-size=8192'
    
    try:
        test_memory_settings()
        test_batch_processing()
        test_recovery_mechanism()
        
        print("\n✅ All tests completed successfully!")
        print("\nRecommendations:")
        print("1. Use 'python py/launch_agent_safe.py <ISO_CODE>' for production runs")
        print("2. Monitor logs in data/<ISO_CODE>/agent_launcher.log")
        print("3. Check memory usage in data/<ISO_CODE>/memory_usage.log")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        

if __name__ == "__main__":
    main()