#!/usr/bin/env bash
#
# Wait for the in-flight runner to halt (it has a STOP file, so it stops cleanly
# after the current country), swap in the staged configuration, and relaunch.
#
# Usage: bash py/handoff_runner.sh <pid-of-running-runner>
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OLD_PID="${1:?usage: handoff_runner.sh <pid>}"
LOG="logs/handoff_$(date +%Y%m%d-%H%M%S).log"

{
  echo "waiting for runner pid $OLD_PID to exit..."
  while kill -0 "$OLD_PID" 2>/dev/null; do sleep 60; done
  echo "runner exited at $(date '+%Y-%m-%d %H:%M:%S')"

  sleep 10
  pkill -f "claude -p .* --agent workflow-orchestrator" 2>/dev/null && \
    echo "cleaned up a stray orchestrator process"

  if [[ -f run_all_countries.sh.staged ]]; then
    mv run_all_countries.sh.staged run_all_countries.sh
    chmod +x run_all_countries.sh
    echo "swapped in staged runner"
  fi
  rm -f STOP

  # Countries that really did run all seven agents were scored 0/7 by the old
  # broken gate and are sitting in the manifest as incomplete. Promote them
  # before the queue is rebuilt, or the relaunch re-runs work that is already
  # finished - four hours per country.
  python3 py/reconcile_manifest.py --apply || true

  # Refuse to relaunch if anything is already running. The previous handoff
  # produced two runners one second apart; they worked ERI and TGO
  # simultaneously and left two conflicting national rows behind. The runner now
  # enforces this itself via reference/.runner.pid, but checking here too means
  # a duplicate supervisor never even starts a process.
  if pgrep -f "bash run_all_countries.sh" >/dev/null 2>&1; then
    echo "ABORT: a runner is already live; not relaunching."
    exit 0
  fi
  rm -f reference/.runner.pid

  out="logs/full_run_$(date +%Y%m%d-%H%M%S).out"
  echo "relaunching -> $out"
  # caffeinate -i prevents idle sleep for the life of the run. A multi-day
  # unattended job that pauses when the lid closes will not complete.
  if command -v caffeinate >/dev/null; then
    nohup caffeinate -i bash run_all_countries.sh --unattended --publish-progress > "$out" 2>&1 &
  else
    nohup bash run_all_countries.sh --unattended --publish-progress > "$out" 2>&1 &
  fi
  echo "relaunched as pid $!"
} >> "$LOG" 2>&1
