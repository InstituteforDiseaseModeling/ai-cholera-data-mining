#!/usr/bin/env bash
#
# Full dashboard rebuild (weekly series, heatmaps, timeline plots) after every
# completed country, for a runner that is ALREADY live with a coarser
# --dash-every. The runner reads DASH_EVERY once at startup, so changing it
# means restarting every in-flight country; this watcher avoids that.
#
# It watches the runner's $LOGDIR/.completed and, when a country is appended,
# runs the same locked rebuild + publish the runner uses. Counts that are a
# multiple of the runner's own cadence are skipped (the runner rebuilds those).
# Exits when the runner exits. New runners default to --dash-every 1 and do not
# need this.
#
# Usage: nohup bash py/rebuild_on_completion.sh <runner_pid> <logdir> [runner_dash_every] &
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RUNNER_PID="$1"; LOGDIR="$2"; RUNNER_EVERY="${3:-5}"
DONE_FILE="$LOGDIR/.completed"
LOG="$LOGDIR/_rebuild_watch.log"

count () { [[ -f "$DONE_FILE" ]] && wc -l < "$DONE_FILE" | tr -d ' ' || echo 0; }

seen="$(count)"
echo "$(date '+%F %T') watching $DONE_FILE (runner $RUNNER_PID, starting at $seen)" >> "$LOG"
while kill -0 "$RUNNER_PID" 2>/dev/null; do
  now="$(count)"
  while (( seen < now )); do
    seen=$((seen+1))
    iso="$(sed -n "${seen}p" "$DONE_FILE")"
    if (( seen % RUNNER_EVERY == 0 )); then
      echo "$(date '+%F %T') $iso (#$seen): runner does this rebuild itself" >> "$LOG"
      continue
    fi
    echo "$(date '+%F %T') $iso (#$seen): full rebuild" >> "$LOG"
    python3 py/with_lock.py dashboard -- bash update_dashboard.sh >> "$LOG" 2>&1
    python3 py/publish.py dashboard/ figures/dashboard/ data/ reference/ \
      -m "Auto-update dashboard data - $(date '+%Y-%m-%d %H:%M:%S') (after $iso)" >> "$LOG" 2>&1
    echo "$(date '+%F %T') $iso (#$seen): rebuild + publish exit $?" >> "$LOG"
  done
  sleep 60
done
echo "$(date '+%F %T') runner exited; watcher done" >> "$LOG"
