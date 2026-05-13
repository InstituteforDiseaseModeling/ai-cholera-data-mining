#!/usr/bin/env python3
"""
Lightweight inter-agent workflow state management.

Agents write a workflow_state.json to data/{ISO_CODE}/ after completing
their work. The next agent reads it to understand what was already covered,
which gaps are filled, and how many batches were used.

Usage (writing):
    from py.workflow_state import write_agent_state, read_workflow_state

    write_agent_state("ETH", agent_num=1, batches_completed=7,
                      batch_yields=[0.25, 0.15, 0.08, 0.04, 0.03, 0.02, 0.01],
                      rows_added=34, sources_discovered=22,
                      stopping_reason="3 consecutive batches below 5% yield")

Usage (reading):
    state = read_workflow_state("ETH")
    if state:
        print(f"Agent 1 added {state['agents'][0]['rows_added']} rows")
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def _state_path(iso_code: str) -> Path:
    base = Path(__file__).parent.parent / "data" / iso_code
    base.mkdir(parents=True, exist_ok=True)
    return base / "workflow_state.json"


def read_workflow_state(iso_code: str) -> dict:
    """Return the current workflow state dict, or empty structure if not found."""
    path = _state_path(iso_code)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"iso_code": iso_code, "agents": [], "gaps_addressed": []}


def write_agent_state(
    iso_code: str,
    agent_num: int,
    batches_completed: int,
    batch_yields: list,
    rows_added: int,
    sources_discovered: int,
    stopping_reason: str = "",
    gaps_filled: list = None,
    gaps_validated_absent: list = None,
    gaps_remaining: list = None,
):
    """Append this agent's completion summary to workflow_state.json."""
    state = read_workflow_state(iso_code)

    entry = {
        "agent_num": agent_num,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "batches_completed": batches_completed,
        "batch_yields": batch_yields,
        "rows_added": rows_added,
        "sources_discovered": sources_discovered,
        "stopping_reason": stopping_reason,
        "gaps_filled": gaps_filled or [],
        "gaps_validated_absent": gaps_validated_absent or [],
        "gaps_remaining": gaps_remaining or [],
    }

    # Replace existing entry for this agent if re-running
    state["agents"] = [a for a in state["agents"] if a["agent_num"] != agent_num]
    state["agents"].append(entry)
    state["agents"].sort(key=lambda a: a["agent_num"])

    path = _state_path(iso_code)
    with open(path, "w") as f:
        json.dump(state, f, indent=2)

    return path


def validate_csv(iso_code: str) -> tuple[bool, str]:
    """
    Parse cholera_data_ai.csv and metadata_ai.csv for the given country.
    Returns (ok, error_message). Called by orchestrator before launching
    each subsequent agent to catch corruption early.
    """
    import pandas as pd

    data_dir = Path(__file__).parent.parent / "data" / iso_code
    errors = []

    for filename, required_cols in [
        (
            "cholera_data_ai.csv",
            ["Index", "Location", "TL", "TR", "source_index", "source", "source_database"],
        ),
        (
            "metadata_ai.csv",
            ["Index", "Source", "URL", "source_database"],
        ),
    ]:
        path = data_dir / filename
        if not path.exists():
            continue  # File may not exist yet for early agents
        try:
            df = pd.read_csv(path)
        except Exception as e:
            errors.append(f"{filename}: parse error — {e}")
            continue

        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            errors.append(f"{filename}: missing columns {missing}")

        # Dual-reference integrity check
        if filename == "cholera_data_ai.csv" and "source_index" in df.columns:
            nulls = df["source_index"].isna().sum()
            if nulls:
                errors.append(f"{filename}: {nulls} rows with null source_index")

    if errors:
        return False, "; ".join(errors)
    return True, ""


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        ok, msg = validate_csv(sys.argv[1])
        print("OK" if ok else f"FAIL: {msg}")
        sys.exit(0 if ok else 1)
