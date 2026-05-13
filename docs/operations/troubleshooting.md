# Troubleshooting Guide

## Common Issues and Solutions

### Search-Related Problems

#### Low Data Yield
**Problem**: Batches consistently yielding <5% despite many queries

**Solutions**:
1. Verify gap analysis files are loaded correctly
2. Check if targeting correct time periods
3. Expand to regional/cross-border searches
4. Try alternative language searches
5. Use more specific date ranges

#### No Sources Found
**Problem**: Queries return no relevant results

**Solutions**:
1. Broaden search terms (remove constraints)
2. Check neighboring country reports
3. Search for regional surveillance
4. Try decade-level searches
5. Use Internet Archive for historical

#### Broken Links
**Problem**: Many discovered sources have dead links

**Solutions**:
1. Use Internet Archive Wayback Machine
2. Search for PDF filename directly
3. Check institutional repositories
4. Contact authors/organizations
5. Look for updated versions

### Data Quality Issues

#### Validation Failures
**Problem**: Data failing quality control checks

**Solutions**:
1. Review epidemiological ranges
2. Check date logic (TL < TR)
3. Verify CFR calculations
4. Confirm geographic codes
5. Fix mathematical inconsistencies

#### Conflicting Sources
**Problem**: Different sources report different numbers

**Solutions**:
1. Apply source hierarchy (WHO > local)
2. Check reporting periods match
3. Verify geographic coverage same
4. Use most recent/final reports
5. Document uncertainty ranges

#### Duplicate Data
**Problem**: Same outbreak reported multiple times

**Solutions**:
1. Check exact date ranges
2. Compare geographic specificity
3. Identify primary source
4. Keep most detailed version
5. Document in processing notes

### Technical Problems

#### Dashboard Not Updating
**Problem**: Running update script shows no changes

**Solutions**:
1. Verify files saved in correct location
2. Check file naming conventions
3. Ensure CSV format correct
4. Look for Python script errors
5. Try manual script execution

#### File Format Errors
**Problem**: CSV files not parsing correctly

**Solutions**:
1. Check column count matches spec
2. Verify date format (YYYY-MM-DD)
3. Ensure proper quote escaping
4. Remove special characters
5. Validate against templates

#### Permission Errors
**Problem**: Cannot write to data directories

**Solutions**:
1. Check directory exists
2. Verify path is correct
3. Ensure proper permissions
4. Create directory if missing
5. Use absolute paths

### Workflow Issues

#### Agent Completion Unclear
**Problem**: Not sure if agent finished properly

**Solutions**:
1. Check search log for completion message
2. Verify stopping criteria documented
3. Count total queries executed
4. Review data observation yield
5. Run dashboard update

#### Gap Targeting Confusion
**Problem**: Unclear which gaps to prioritize

**Solutions**:
1. Load agent-specific gap file
2. Sort by priority_score
3. Focus on CRITICAL tier first
4. Check gap duration
5. Review geographic level

### Quick Diagnostic Commands

```bash
# Check file counts
ls -la data/{ISO}/ | wc -l

# Verify CSV structure
head -n 5 data/{ISO}/cholera_data_ai.csv

# Count data rows
wc -l data/{ISO}/cholera_data_ai.csv

# Check search log size
wc -l data/{ISO}/search_log_agent_*.txt

# Validate references
grep -c "source_index" data/{ISO}/cholera_data_ai.csv
```

## When to Seek Help

Contact support if:
1. Systematic errors across multiple countries
2. Dashboard system failures
3. Reference file generation problems
4. Unexplained data loss
5. Workflow automation failures

## Prevention Best Practices

1. **Regular Saves**: Save work frequently
2. **Validation Early**: Check data while searching
3. **Document Everything**: Note all decisions
4. **Follow Templates**: Use standard formats
5. **Test Small**: Verify with one country first