# Discovery Saturation and Stopping Criteria

## Data Observation Yield Methodology

### Core Concept
Stop searching when consecutive batches show declining yield of new data observations, indicating discovery saturation.

### Yield Calculation
```
Batch Yield = (Queries resulting in CSV additions / 20) × 100%
```

**Critical**: Count ONLY queries that produce actual cholera_data_ai.csv entries with quantitative data (cases, deaths, CFRs).

## Unified Parameters for Agents 1-6

| Agent | Stop When | Max Batches | Max Queries |
|-------|-----------|-------------|-------------|
| 1-6 | 3 consecutive <5% | 10 | 200 |
| 7 | Quality complete | N/A | N/A |

## No Exceptions Policy

- Apply stopping criteria uniformly across all agents
- No quality-based exceptions or overrides
- Consistent application ensures reproducibility

## Implementation Process

### 1. Track Success per Batch
```
Batch 1: 8/20 queries → CSV additions = 40% yield
Batch 2: 6/20 queries → CSV additions = 30% yield
Batch 3: 3/20 queries → CSV additions = 15% yield
Batch 4: 1/20 queries → CSV additions = 5% yield
Batch 5: 0/20 queries → CSV additions = 0% yield
Batch 6: 1/20 queries → CSV additions = 5% yield
STOP: 3 consecutive batches <5%
```

### 2. Document in Search Logs
```
=== BATCH 4 RESULTS ===
Queries executed: 20
Successful queries (CSV additions): 1
Data observation yield: 5%
Cumulative queries: 80
Status: Below threshold, monitoring...
```

### 3. Apply Stopping Decision
```
=== STOPPING CRITERIA MET ===
Batches 4 and 5 both yielded <10%
No quality exception applicable
Total queries executed: 100
Search phase complete
```

## Special Considerations

### All Agents (1-6)
- Unified threshold (5%) for consistency
- Stop after 3 consecutive low-yield batches
- Maximum 10 batches (200 queries) ensures thorough coverage
- No minimum batch requirements

### Agent 4 (Obscure Sources)
- May have naturally lower yields
- Consider source uniqueness not just quantity
- Historical sources often sparse but valuable

## Common Patterns

### High-Yield Start
- Batches 1-3: 30-50% yield
- Batches 4-5: 10-20% yield
- Batches 6-7: <10% yield → Stop

### Steady Decline
- Consistent 5-10% decrease per batch
- Natural saturation curve
- Stop when threshold crossed

### Plateau Pattern
- Consistent 15-20% yield
- Sudden drop to <5%
- Indicates exhausted source type

## Quality Validation

Before stopping, verify:
- Priority gaps addressed
- Geographic coverage adequate
- Temporal span appropriate
- Source diversity achieved
- Zero-transmission documented