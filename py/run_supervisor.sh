#!/usr/bin/env bash
#
# Keep the 40-country run going across account spend-limit resets.
#
# Sequential by default, and deliberately so. Parallelism cannot raise
# throughput when the binding constraint is spend per window rather than wall
# clock: four countries at once consumed a whole session budget in 70 minutes
# and then sat idle for nearly four hours, leaving four countries a quarter
# done instead of one finished. A session window is worth roughly 280
# country-minutes and a country needs about 300, so one window is about one
# country. Running one at a time paces the work to the rate the budget refills,
# and if the limit is raised enough that a window never runs out, sequential
# simply runs continuously and loses nothing.
#
# Exits by itself once all 40 countries are marked done.
#
# Usage: nohup bash py/run_supervisor.sh [interval_seconds] &
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

INTERVAL="${1:-900}"          # how often to check on a live run
PARALLEL="${PARALLEL:-1}"
LOG="logs/supervisor_$(date +%Y%m%d-%H%M%S).log"
mkdir -p logs

remaining () {
  python3 - <<'PY'
import csv, json
mosaic = {k for k, v in json.load(open('reference/country_mapping.json'))['countries'].items()
          if v.get('mosaic_framework')}
last = {}
try:
    for r in csv.DictReader(open('reference/run_manifest.csv')):
        last[r['iso']] = r['status']
except FileNotFoundError:
    pass
print(len([i for i in mosaic if last.get(i) != 'done']))
PY
}

{
  echo "supervisor started $(date '+%Y-%m-%d %H:%M:%S'), parallel=$PARALLEL"
  while true; do
    left="$(remaining)"
    if [[ "$left" == "0" ]]; then
      echo "$(date '+%Y-%m-%d %H:%M:%S')  all 40 countries done - supervisor exiting"
      exit 0
    fi

    if pgrep -f "bash run_all_countries.sh" >/dev/null 2>&1; then
      echo "$(date '+%Y-%m-%d %H:%M:%S')  runner alive, $left country(ies) left"
      sleep "$INTERVAL"
      continue
    fi

    # Do not probe a limit that has not reset. Each probe starts a country, is
    # refused in about three seconds, and appends a blocked_spend_limit row to
    # the manifest; ten of those per window is noise, not information. The CLI
    # states when the limit resets, so wait for that moment and retry once.
    wait_s="$(python3 py/limit_reset.py 2>/dev/null | head -1)"
    if [[ "${wait_s:-0}" =~ ^[0-9]+$ ]] && (( wait_s > 0 )); then
      echo "$(date '+%Y-%m-%d %H:%M:%S')  spend limit in force; sleeping $((wait_s/60)) min until it resets"
      sleep "$wait_s"
      continue
    fi

    out="logs/full_run_$(date +%Y%m%d-%H%M%S).out"
    echo "$(date '+%Y-%m-%d %H:%M:%S')  no runner, $left left - launching (parallel=$PARALLEL) -> $out"
    rm -f STOP reference/.runner.pid
    # -dims, not just -i. `caffeinate -i` blocks only *user idle* sleep, and on
    # 2026-09-21 the machine took a 'Maintenance Sleep' anyway at 10:29 while on
    # battery and stayed down until the lid was opened at 11:16. Four countries
    # lost their network mid-run, reported "Agent 2 was interrupted before it
    # started", and exited after one agent each.
    #
    # Note -s is honoured only on AC power. On battery this machine is set to
    # `sleep 10`, so nothing here can keep it awake: the laptop has to be
    # plugged in for an unattended run. run_status.py reports the power source
    # so that is visible remotely.
    if command -v caffeinate >/dev/null; then
      nohup caffeinate -dims bash run_all_countries.sh --unattended --publish-progress \
        --parallel "$PARALLEL" > "$out" 2>&1 &
    else
      nohup bash run_all_countries.sh --unattended --publish-progress \
        --parallel "$PARALLEL" > "$out" 2>&1 &
    fi
    echo "    launched as pid $!"
    sleep "$INTERVAL"
  done
} >> "$LOG" 2>&1
