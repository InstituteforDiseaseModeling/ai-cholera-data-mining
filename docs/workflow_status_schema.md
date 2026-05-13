# Workflow Status JSON Schema Documentation

## Overview

The `workflow_status.json` file serves as the single source of truth for tracking cholera data collection workflow progress. This file must be maintained by the workflow orchestrator throughout the entire data collection process.

## File Location

Each country's workflow status file is located at:
```
./data/{ISO_CODE}/workflow_status.json
```

## Schema Definition

### Root Object

```json
{
  "country": "string",           // ISO code (e.g., "AGO")
  "iso_code": "string",          // ISO code (duplicate for compatibility)
  "status": "string",            // Current workflow status
  "workflow_version": "string",  // Version of the workflow (e.g., "1.0")
  "timestamps": {},              // Object containing all relevant timestamps
  "agents": {},                  // Object containing agent-specific data
  "current_agent": null|number,  // Currently running agent (1-6) or null
  "data_summary": {},            // Summary of collected data
  "notes": "string",             // Human-readable status/notes
  "errors": [],                  // Array of error messages
  "autonomous_mode": boolean     // Whether running in autonomous mode
}
```

### Status Values

The `status` field must be one of:
- `"initialized"` - Workflow created but not started
- `"in_progress"` - Workflow actively running
- `"completed"` - All agents successfully completed
- `"error"` - Workflow encountered a critical error

### Timestamps Object

```json
"timestamps": {
  "initialized": "ISO 8601 datetime",     // When workflow was initialized
  "started": "ISO 8601 datetime",         // When first agent started
  "agent_1_start": "ISO 8601 datetime",   // Agent 1 start time
  "agent_1_end": "ISO 8601 datetime",     // Agent 1 end time
  "agent_2_start": "ISO 8601 datetime",   // Agent 2 start time
  "agent_2_end": "ISO 8601 datetime",     // Agent 2 end time
  // ... continue for agents 3-6
  "completed": "ISO 8601 datetime"        // When workflow completed
}
```

### Agents Object

Each agent (1-6) should have an entry:

```json
"agents": {
  "1": {
    "status": "string",              // "pending"|"running"|"completed"|"error"
    "queries": number,               // Total queries executed
    "observations_added": number,    // Data rows added to cholera_data_ai.csv
    "sources_found": number,         // Sources added to metadata_ai.csv
    "duration_minutes": number,      // Execution time in minutes
    "error": "string|null"          // Error message if failed
  },
  // ... continue for agents 2-6
}
```

### Data Summary Object

Updated after workflow completion:

```json
"data_summary": {
  "total_sources": number,      // Count from metadata_ai.csv
  "total_observations": number, // Count from cholera_data_ai.csv
  "date_range": "string",       // e.g., "1970-2025"
  "has_search_report": boolean, // Whether search_report.txt exists
  "last_updated": "ISO 8601"    // When summary was last updated
}
```

## Update Requirements

### Workflow Orchestrator Responsibilities

1. **On Initialization**:
   - Create workflow_status.json with "initialized" status
   - Set timestamps.initialized
   - Initialize empty agents object

2. **On Workflow Start**:
   - Update status to "in_progress"
   - Set timestamps.started

3. **Before Each Agent**:
   - Update current_agent to agent number
   - Set timestamps.agent_N_start
   - Update agents[N].status to "running"

4. **After Each Agent**:
   - Set timestamps.agent_N_end
   - Update agents[N] with metrics
   - Update agents[N].status to "completed" or "error"
   - Set current_agent to null

5. **On Workflow Completion**:
   - Update status to "completed"
   - Set timestamps.completed
   - Update data_summary
   - Set appropriate notes

6. **On Error**:
   - Update status to "error"
   - Add error to errors array
   - Update relevant agent status

## Example Files

### Initial State (After Initialization)

```json
{
  "country": "AGO",
  "iso_code": "AGO",
  "status": "initialized",
  "workflow_version": "1.0",
  "timestamps": {
    "initialized": "2025-08-04T10:45:00.000000"
  },
  "agents": {},
  "current_agent": null,
  "data_summary": {},
  "notes": "",
  "errors": [],
  "autonomous_mode": true
}
```

### In Progress State (Agent 2 Running)

```json
{
  "country": "AGO",
  "iso_code": "AGO",
  "status": "in_progress",
  "workflow_version": "1.0",
  "timestamps": {
    "initialized": "2025-08-04T10:45:00.000000",
    "started": "2025-08-04T10:46:00.000000",
    "agent_1_start": "2025-08-04T10:46:00.000000",
    "agent_1_end": "2025-08-04T11:06:00.000000",
    "agent_2_start": "2025-08-04T11:06:00.000000"
  },
  "agents": {
    "1": {
      "status": "completed",
      "queries": 120,
      "observations_added": 15,
      "sources_found": 8,
      "duration_minutes": 20
    },
    "2": {
      "status": "running",
      "queries": 0,
      "observations_added": 0,
      "sources_found": 0,
      "duration_minutes": 0
    }
  },
  "current_agent": 2,
  "data_summary": {},
  "notes": "Agent 2 geographic expansion in progress",
  "errors": [],
  "autonomous_mode": true
}
```

### Completed State

```json
{
  "country": "AGO",
  "iso_code": "AGO",
  "status": "completed",
  "workflow_version": "1.0",
  "timestamps": {
    "initialized": "2025-08-04T10:45:00.000000",
    "started": "2025-08-04T10:46:00.000000",
    "agent_1_start": "2025-08-04T10:46:00.000000",
    "agent_1_end": "2025-08-04T11:06:00.000000",
    "agent_2_start": "2025-08-04T11:06:00.000000",
    "agent_2_end": "2025-08-04T11:21:00.000000",
    "agent_3_start": "2025-08-04T11:21:00.000000",
    "agent_3_end": "2025-08-04T11:36:00.000000",
    "agent_4_start": "2025-08-04T11:36:00.000000",
    "agent_4_end": "2025-08-04T11:51:00.000000",
    "agent_5_start": "2025-08-04T11:51:00.000000",
    "agent_5_end": "2025-08-04T12:06:00.000000",
    "agent_6_start": "2025-08-04T12:06:00.000000",
    "agent_6_end": "2025-08-04T12:15:00.000000",
    "completed": "2025-08-04T12:15:00.000000"
  },
  "agents": {
    "1": {
      "status": "completed",
      "queries": 120,
      "observations_added": 15,
      "sources_found": 8,
      "duration_minutes": 20
    },
    "2": {
      "status": "completed",
      "queries": 60,
      "observations_added": 5,
      "sources_found": 3,
      "duration_minutes": 15
    },
    "3": {
      "status": "completed",
      "queries": 40,
      "observations_added": 0,
      "sources_found": 2,
      "duration_minutes": 15
    },
    "4": {
      "status": "completed",
      "queries": 80,
      "observations_added": 8,
      "sources_found": 10,
      "duration_minutes": 15
    },
    "5": {
      "status": "completed",
      "queries": 50,
      "observations_added": 6,
      "sources_found": 9,
      "duration_minutes": 15
    },
    "6": {
      "status": "completed",
      "queries": 0,
      "observations_added": 0,
      "sources_found": 0,
      "duration_minutes": 9
    }
  },
  "current_agent": null,
  "data_summary": {
    "total_sources": 32,
    "total_observations": 34,
    "date_range": "1970-2025",
    "has_search_report": true,
    "last_updated": "2025-08-04T12:15:00.000000"
  },
  "notes": "Workflow complete with quality audit",
  "errors": [],
  "autonomous_mode": true
}
```

## Integration with Dashboard

The dashboard update script (`update_dashboard_data.py`) will:

1. Check for workflow_status.json first
2. If found, use it as the primary data source
3. Fall back to legacy file analysis only if workflow_status.json is missing

This ensures accurate progress tracking without false positives from initialized log files.

## Best Practices

1. **Atomic Updates**: Write the entire JSON file at once to prevent corruption
2. **Error Handling**: Always update status to "error" if agent fails
3. **Timestamp Format**: Use ISO 8601 format for all timestamps
4. **Backwards Compatibility**: Include both "country" and "iso_code" fields
5. **Regular Updates**: Update after each significant milestone, not just at agent boundaries