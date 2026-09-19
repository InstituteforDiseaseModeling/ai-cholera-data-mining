#!/usr/bin/env bash
#
# Publish a liveness heartbeat while the unattended run is in progress.
#
# The main dashboard is only rebuilt when a country finishes, which is roughly
# every four hours. Between completions the published site does not change at
# all, so from outside the machine a healthy run is indistinguishable from a
# dead one. This loop refreshes dashboard/run_status.{json,html} every few
# minutes and pushes them, so the run can be watched remotely.
#
# Started automatically by run_all_countries.sh; also safe to run by hand.
#
# Usage: bash py/run_heartbeat.sh [interval_seconds]
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# One heartbeat at a time, for the same reason the runner takes a lock: the
# handoff between an old and a new runner would otherwise leave two loops
# pushing forever, each resetting the other's shutdown counter.
HBLOCK="reference/.heartbeat.pid"
if [[ -f "$HBLOCK" ]]; then
  other="$(cat "$HBLOCK" 2>/dev/null || true)"
  if [[ -n "$other" ]] && kill -0 "$other" 2>/dev/null \
     && ps -p "$other" -o command= 2>/dev/null | grep -q run_heartbeat.sh; then
    echo "heartbeat already running (pid $other)" >&2
    exit 0
  fi
fi
echo $$ > "$HBLOCK"
trap 'rm -f "$HBLOCK"' EXIT

INTERVAL="${1:-${HEARTBEAT_INTERVAL:-600}}"
PUBLISH="${HEARTBEAT_PUBLISH:-1}"
LOG="logs/heartbeat_$(date +%Y%m%d-%H%M%S).log"
mkdir -p logs

# Stop once the run is over. Two consecutive misses rather than one, so a brief
# gap between countries does not end the heartbeat early.
misses=0
while true; do
  if [[ "$PUBLISH" -eq 1 ]]; then
    python3 py/run_status.py --publish >> "$LOG" 2>&1
  else
    python3 py/run_status.py >> "$LOG" 2>&1
  fi

  if pgrep -f "bash run_all_countries.sh" >/dev/null 2>&1; then
    misses=0
  else
    misses=$((misses+1))
    if (( misses >= 2 )); then
      echo "runner gone - heartbeat stopping at $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG"
      python3 py/run_status.py --publish >> "$LOG" 2>&1   # final, shows NOT RUNNING
      exit 0
    fi
  fi
  sleep "$INTERVAL"
done
