# Migration Guide: Implementing Subagent Architecture

## Overview

This guide provides step-by-step instructions for migrating from the current single-context "pseudo-agent" workflow to the true subagent architecture using Claude Code's `/agents` command.

## Pre-Migration Checklist

- [ ] Review all subagent configuration files
- [ ] Understand the orchestrator workflow  
- [ ] Backup current system (already done via git branch)
- [ ] Select pilot country for testing

## Implementation Steps

### Step 1: Create Specialized Subagents

Use the `/agents` command to create each specialized subagent:

#### 1.1 Create Baseline Data Collector
```
/agents
→ Create new subagent
→ Project-level subagent
→ Name: Baseline Data Collector
→ Description: Systematic priority source coverage and baseline data establishment
→ Tools: WebSearch, WebFetch, Read, Write, Edit, Bash, TodoWrite
→ System Prompt: [Copy from agent1_baseline_collector.md]
```

#### 1.2 Create Geographic Expansion Specialist
```
/agents
→ Create new subagent  
→ Project-level subagent
→ Name: Geographic Expansion Specialist
→ Description: Provincial/district-level data discovery and geographic completeness
→ Tools: WebSearch, WebFetch, Read, Edit, Write
→ System Prompt: [Copy from agent2_geographic_expansion.md]
```

#### 1.3 Create Zero-Transmission Validator
```
/agents
→ Create new subagent
→ Project-level subagent  
→ Name: Zero-Transmission Validator
→ Description: PRIMARY RESPONSIBILITY for cholera-free period documentation
→ Tools: WebSearch, WebFetch, Read, Edit, Write
→ System Prompt: [Copy from agent3_zero_transmission.md]
```

#### 1.4 Create Obscure Source Explorer
```
/agents
→ Create new subagent
→ Project-level subagent
→ Name: Obscure Source Explorer  
→ Description: Alternative source discovery and hard-to-find data mining
→ Tools: WebSearch, WebFetch, Read, Edit, Write
→ System Prompt: [Copy from agent4_obscure_sources.md]
```

#### 1.5 Create Cross-Reference Integrator
```
/agents
→ Create new subagent
→ Project-level subagent
→ Name: Cross-Reference Integrator
→ Description: Source triangulation and data synthesis across references
→ Tools: WebSearch, WebFetch, Read, Edit, Write  
→ System Prompt: [Copy from agent5_cross_reference.md]
```

#### 1.6 Create Quality Auditor
```
/agents
→ Create new subagent
→ Project-level subagent
→ Name: Quality Auditor
→ Description: Data validation, quality control, and final report generation
→ Tools: Read, Edit, Write, Bash, TodoWrite
→ System Prompt: [Copy from agent6_quality_auditor.md]
```

### Step 2: Create Master Orchestrator

#### 2.1 Create Orchestrator Subagent
```
/agents
→ Create new subagent
→ Project-level subagent  
→ Name: Cholera Country Processor
→ Description: Coordinate complete cholera surveillance data enhancement for a single country
→ Tools: Task, Read, Write, Edit, Bash, TodoWrite, LS
→ System Prompt: [Copy from orchestrator_config.md]
```

### Step 3: Test Individual Subagents

Before running the full orchestrator, test each specialized subagent individually:

#### 3.1 Test Baseline Data Collector
```
Task with subagent "Baseline Data Collector":
"Test baseline data collection for a small country like Eswatini (SWZ) - run 2 batches only to validate methodology"
```

#### 3.2 Test Other Agents (Optional)
Test other agents individually if needed to validate their configurations.

### Step 4: Pilot Country Test

#### 4.1 Select Pilot Country
Choose a country that:
- Has existing data for comparison (e.g., Angola - already processed)
- Is manageable size for testing
- Represents typical workflow complexity

**Recommended**: Re-process Angola to compare subagent vs single-context results

#### 4.2 Full Orchestrator Test
```
Task with subagent "Cholera Country Processor":
"Process Angola's cholera data using the complete 6-agent workflow"
```

### Step 5: Results Comparison

#### 5.1 Compare Outputs
- Data quality and completeness
- Processing time and efficiency  
- Context management and clarity
- Error rates and debugging ease

#### 5.2 Validate Improvements
- [ ] Better context management (no context bloat)
- [ ] True specialization per agent
- [ ] Cleaner error isolation
- [ ] Maintained operational convenience

### Step 6: Full Migration (If Successful)

#### 6.1 Update Documentation
- Update main CLAUDE.md with subagent approach references
- Document orchestrator usage instructions
- Create troubleshooting guide

#### 6.2 Production Deployment
- Begin using orchestrator for new countries
- Gradually migrate existing workflows
- Monitor performance and iterate

## Troubleshooting Common Issues

### Subagent Creation Issues
- **Problem**: Tool restrictions not working properly
- **Solution**: Recreate subagent with specific tool selections

### Orchestrator Coordination Issues  
- **Problem**: Task tool not properly invoking subagents
- **Solution**: Check subagent names match exactly, verify Task tool syntax

### Context Management Issues
- **Problem**: Subagents not maintaining context properly
- **Solution**: Review system prompts for context preservation instructions

### Performance Issues
- **Problem**: Slower than single-context approach
- **Solution**: Optimize subagent handoffs, reduce coordination overhead

## Success Criteria

### Technical Success
- [ ] All 7 subagents created successfully
- [ ] Orchestrator can invoke all specialized agents
- [ ] File-based coordination works properly
- [ ] Same data quality as single-context approach

### Operational Success  
- [ ] Single command still processes entire country
- [ ] Processing time comparable or better
- [ ] Error debugging improved
- [ ] Agent specialization clearly visible

### Quality Success
- [ ] Data completeness maintained or improved
- [ ] Validation effectiveness maintained
- [ ] Documentation quality maintained
- [ ] Dashboard integration functional

## Rollback Plan (If Needed)

If subagent approach doesn't work as expected:

1. **Immediate Rollback**: Switch back to main branch
```bash
git checkout main
```

2. **Preserve Learning**: Document lessons learned from subagent testing

3. **Iterate**: Make improvements to subagent design based on testing

4. **Re-attempt**: Try subagent approach again with improved configurations

## Next Steps After Successful Migration

1. **Performance Optimization**: Fine-tune individual agent performance
2. **Parallel Processing**: Explore running compatible agents in parallel
3. **Agent Reuse**: Test using same agents across multiple countries
4. **Advanced Features**: Add agent-specific optimizations and specializations

## Support and Troubleshooting

For issues during migration:
1. Check individual subagent configurations
2. Test Task tool invocation syntax
3. Verify file-based coordination mechanisms
4. Review orchestrator workflow logic
5. Compare results with existing single-context approach

This migration represents a significant architectural improvement that should provide better scalability, maintainability, and specialization while preserving the operational convenience of single-command country processing.