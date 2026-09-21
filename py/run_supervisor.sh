#!/usr/bin/env bash
#
# Keep the 40-country run going across account spend-limit resets.
#
# The weekly spend limit was reached on 2026-09-20 with 36 countries still to
# do. Nothing is wrong with those countries and nothing needs fixing - the run
# simply cannot proceed until the limit resets, which happens on a weekly
# cycle. This supervisor notices when a run has stopped, and restarts it. If
# the limit is still exhausted the runner detects that within seconds and halts
# again, so a wasted probe costs almost nothing.
#
# Exits by itself once all 40 countries are marked done.
#
# Usage: nohup bash py/run_supervisor.sh [interval_seconds] &
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

INTERVAL="${1:-1800}"
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
  echo "supervisor started $(date '+%Y-%m-%d %H:%M:%S'), probing every $((INTERVAL/60)) min"
  while true; do
    left="$(remaining)"
    if [[ "$left" == "0" ]]; then
      echo "$(date '+%Y-%m-%d %H:%M:%S')  all 40 countries done - supervisor exiting"
      exit 0
    fi

    if pgrep -f "bash run_all_countries.sh" >/dev/null 2>&1; then
      echo "$(date '+%Y-%m-%d %H:%M:%S')  runner alive, $left country(ies) left"
    else
      out="logs/full_run_$(date +%Y%m%d-%H%M%S).out"
      echo "$(date '+%Y-%m-%d %H:%M:%S')  no runner, $left left - launching -> $out"
      rm -f STOP reference/.runner.pid
      if command -v caffeinate >/dev/null; then
        nohup caffeinate -i bash run_all_countries.sh --unattended --publish-progress \
          --parallel "${PARALLEL:-4}" > "$out" 2>&1 &
      else
        nohup bash run_all_countries.sh --unattended --publish-progress \
          --parallel "${PARALLEL:-4}" > "$out" 2>&1 &
      fi
      echo "    launched as pid $!"
    fi
    sleep "$INTERVAL"
  done
} >> "$LOG" 2>&1
