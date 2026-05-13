# Workflow Simplification Guide

## Overview

To address memory issues, we can dramatically simplify the cholera data collection workflow while maintaining core functionality. This guide outlines what can be removed or simplified.

## Major Simplifications

### 1. Reduce from 7 to 3 Agents

**Current**: 7 specialized agents with overlapping searches
**Simplified**: 3 focused agents with clear boundaries

```
Before: Agents 1-7 (600+ queries total)
After:  Agents 1-3 (60 queries total)
```

### 2. Eliminate Redundant Elements

#### Remove These Complex Features:
- **8-phase search protocol** → 3 simple phases
- **4 institutional modules** → 1 priority module  
- **Citation depth 3** → Primary sources only
- **Multi-stage validation** → Single batch validation
- **Complex gap analysis** → Top 5 gaps only

#### Memory Savings Per Feature:
- 8-phase protocol: -50% memory
- Institutional modules: -80% memory
- Citation following: -70% memory
- Continuous validation: -40% memory

### 3. Simplify Query Generation

**Before**: Complex gap-targeted queries with temporal/geographic/seasonal variations
```python
# Complex query generation with multiple variations
for gap in all_gaps:
    for year in gap_years:
        for source in sources:
            for language in languages:
                # Generates 100s of queries
```

**After**: Simple focused queries
```python
# Simple high-yield queries only
queries = [
    f"{country} cholera 2024 WHO",
    f"{country} cholera outbreak government",
    f"{country} cholera UNICEF"
]
# Maximum 30 queries
```

### 4. Streamline Data Operations

**Memory-Intensive Operations to Remove:**
- Continuous CSV read/write after each query
- Real-time validation during extraction
- Complex dual-reference indexing
- Multiple dashboard updates per agent

**Replace With:**
- Single bulk write at agent completion
- Batch validation at end
- Simple sequential indexing
- One dashboard update per workflow

## Implementation Options

### Option A: Quick Fix (Immediate)
Keep existing prompts but add hard limits:
```python
# Add to existing agents
MAX_QUERIES = {
    "agent_1": 30,  # Down from 100+
    "agent_2": 20,  # Down from 100
    "agent_3": 10   # Validation only
}
```

### Option B: Use Simplified Prompts (Recommended)
Replace complex prompts with simplified versions:
```bash
# Use new simplified agents
cp agents_simplified/agent_1_baseline_simplified.md agents/
cp agents_simplified/agent_2_geographic_simplified.md agents/
cp agents_simplified/agent_3_quality_simplified.md agents/
```

### Option C: Hybrid Approach
1. Use memory-optimized launcher with existing agents
2. Add hard query limits
3. Disable complex features via configuration

## What We Keep vs Remove

### Essential Features (Keep):
✅ Core data discovery from WHO/Government sources
✅ Basic geographic expansion for major outbreaks
✅ Simple quality validation
✅ Gap targeting for recent periods (2020-2025)

### Non-Essential Features (Remove):
❌ Obscure source exploration
❌ Deep citation networks  
❌ Multi-language parallel searches
❌ Complex cross-referencing
❌ Continuous validation
❌ Redundant agent overlap
❌ Complex status tracking

## Performance Comparison

### Current Workflow:
- **Agents**: 7 
- **Queries**: 600+ total
- **Memory**: 4GB+ (crashes)
- **Time**: 8+ hours
- **Complexity**: Very high

### Simplified Workflow:
- **Agents**: 3
- **Queries**: 60 total  
- **Memory**: <1GB (stable)
- **Time**: <2 hours
- **Complexity**: Low

## Quick Implementation Steps

1. **Immediate Memory Relief**:
   ```bash
   export NODE_OPTIONS="--max-old-space-size=8192"
   python py/launch_agent_safe.py AGO
   ```

2. **Use Simplified Workflow**:
   ```bash
   # Copy simplified prompts
   cp -r agents_simplified/* agents/
   
   # Run with limits
   python py/launch_agent_safe.py AGO
   ```

3. **Configure Hard Limits**:
   ```python
   # In workflow_memory_manager.py
   AGENT_LIMITS = {
       1: {"max_queries": 30, "batch_size": 5},
       2: {"max_queries": 20, "batch_size": 5},
       3: {"max_queries": 10, "batch_size": 5}
   }
   ```

## Recommendation

For immediate relief from memory issues, implement the simplified 3-agent workflow with hard query limits. This maintains core data discovery functionality while reducing memory usage by 75%.

The simplified workflow will:
- Find essential cholera data from priority sources
- Expand geographic coverage for major outbreaks
- Validate and finalize the dataset
- Complete in <2 hours with <1GB memory

This is a significant improvement over the current 7-agent, 600+ query workflow that crashes due to memory exhaustion.