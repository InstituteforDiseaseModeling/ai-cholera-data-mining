#!/usr/bin/env bash
#
# Sequential, resumable, unattended re-run of the 7-agent cholera workflow
# across the 40 MOSAIC framework countries.
#
# ONE OS PROCESS PER COUNTRY. This is the whole point of the design: running all
# 40 inside a single session exhausted memory and crashed. A separate `claude -p`
# per country means the OS reclaims everything on exit, so memory cannot
# accumulate across the run.
#
# Usage:
#   bash run_all_countries.sh --dry-run              # show the plan, run nothing
#   bash run_all_countries.sh --limit 1              # pilot: stalest country only
#   bash run_all_countries.sh --unattended           # full run, permissions lifted
#   bash run_all_countries.sh --unattended --publish-progress
#   bash run_all_countries.sh --from KEN             # resume at a country
#   bash run_all_countries.sh --only ETH,KEN         # specific countries
#   bash run_all_countries.sh --retry-failed         # re-attempt failures only
#
# State lives in reference/run_manifest.csv and survives interruption: a country
# marked `done` is skipped on the next invocation, so Ctrl-C and restart is safe.
# To stop gracefully mid-run, `touch STOP` - the current country finishes and the
# run ends cleanly rather than being killed part-way through a country.
#
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

MANIFEST="reference/run_manifest.csv"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOGDIR="logs/run_${STAMP}"
TIMEOUT_SECS=${TIMEOUT_SECS:-28800}        # 8h per country
MAX_ATTEMPTS=${MAX_ATTEMPTS:-3}            # retries before moving on
PERMISSION_MODE="acceptEdits"
MAX_TURNS=${MAX_TURNS:-600}
DASH_EVERY=${DASH_EVERY:-5}                # full dashboard rebuild cadence
DRY=0; LIMIT=0; FROM=""; ONLY=""; RETRY_FAILED=0; PUBLISH=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)         DRY=1 ;;
    --limit)           LIMIT="$2"; shift ;;
    --from)            FROM="$2"; shift ;;
    --only)            ONLY="$2"; shift ;;
    --retry-failed)    RETRY_FAILED=1 ;;
    --timeout)         TIMEOUT_SECS="$2"; shift ;;
    --permission-mode) PERMISSION_MODE="$2"; shift ;;
    --unattended)      PERMISSION_MODE="bypassPermissions" ;;
    --publish-progress) PUBLISH=1 ;;
    --dash-every)      DASH_EVERY="$2"; shift ;;
    -h|--help)         sed -n '2,32p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

command -v claude >/dev/null || { echo "claude CLI not found" >&2; exit 1; }

# `claude -p` stops waiting for background tasks after 600s and terminates.
# The orchestrator runs its seven agents as background tasks, so with the
# default ceiling a country "completes" in ~16 minutes having run only Agent 1,
# and exits 0 - a silent partial run. 0 means wait indefinitely; the real bound
# is the per-country `timeout` below.
export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0
mkdir -p "$LOGDIR" reference
rm -f STOP

# ---------------------------------------------------------------- preflight --
echo "=== preflight ==="
fail=0
python3 py/build_country_profiles.py --check >/dev/null 2>&1 \
  || { echo "  FAIL country_profiles invalid"; fail=1; }
python3 py/validate_quality.py --quiet >/dev/null 2>&1 \
  || { echo "  FAIL validate_quality does not pass; the per-agent completion gate will block"; fail=1; }
[[ -f templates/template_search_protocol.txt ]] \
  || { echo "  FAIL search protocol missing"; fail=1; }
python3 py/analyze_effective_gaps.py >/dev/null 2>&1 \
  || { echo "  FAIL gap analysis failed"; fail=1; }

# Under bypassPermissions the deny rules protecting the read-only JHU/WHO
# baselines are not enforced, so protect them at the filesystem layer instead.
python3 py/protect_baselines.py lock >/dev/null 2>&1 \
  || { echo "  FAIL could not lock baselines"; fail=1; }

[[ $fail -eq 0 ]] && echo "  ok: profiles, validation gate, protocol, gap analysis, baselines locked" \
                  || { echo "preflight failed; not starting"; exit 1; }

if [[ "$PERMISSION_MODE" == "bypassPermissions" ]]; then
  echo ""
  echo "  !! UNATTENDED MODE: all permission prompts are bypassed."
  echo "     JHU/WHO baselines are chmod a-w and checksummed; drift is reported at the end."
fi

# Order by staleness, worst first, so the highest-value work lands earliest and
# an aborted run still leaves the most valuable countries done.
ORDER=$(python3 - <<'PY'
import csv
rows = [r for r in csv.DictReader(open('reference/effective_surveillance_recency.csv'))
        if r.get('days_stale')]
rows.sort(key=lambda r: -int(r['days_stale']))
print(' '.join(r['iso_code'] for r in rows))
PY
)
[[ -n "$ONLY" ]] && ORDER=$(echo "$ONLY" | tr ',' ' ' | tr '[:lower:]' '[:upper:]')

# ----------------------------------------------------------------- manifest --
if [[ ! -f "$MANIFEST" ]]; then
  echo "iso,status,started,finished,rows_before,rows_after,sources_before,sources_after,exit_code,log" > "$MANIFEST"
fi
status_of () { awk -F, -v i="$1" '$1==i {s=$2} END {print s}' "$MANIFEST"; }
rowcount () { local f="data/$1/cholera_data_ai.csv"; [[ -f "$f" ]] && echo $(( $(wc -l < "$f") - 1 )) || echo 0; }
srccount () { local f="data/$1/metadata_ai.csv";   [[ -f "$f" ]] && echo $(( $(wc -l < "$f") - 1 )) || echo 0; }

refresh_dashboard () {   # $1 = "light" | "full"
  if [[ "$1" == "full" ]]; then
    # Heavy: weekly series for all 40, heatmaps, barplot, then commit+push.
    if [[ $PUBLISH -eq 1 ]]; then
      bash update_dashboard.sh --publish >> "$LOGDIR/_dashboard.log" 2>&1
    else
      bash update_dashboard.sh >> "$LOGDIR/_dashboard.log" 2>&1
    fi
  else
    # Light: just the progress view (checklist + embedded data). Published too,
    # so the live dashboard reflects every completed country rather than only
    # every DASH_EVERY-th one - the run is unattended and this is the only way
    # to watch it from elsewhere.
    python3 py/update_dashboard_data.py >> "$LOGDIR/_dashboard.log" 2>&1
    if [[ $PUBLISH -eq 1 ]]; then
      {
        git add -A dashboard/ reference/run_manifest.csv 2>/dev/null
        git diff --staged --quiet || {
          git commit -q -m "Run progress: ${2:-country} complete - $(date '+%Y-%m-%d %H:%M:%S')"
          git push -q origin "$(git branch --show-current)"
        }
      } >> "$LOGDIR/_dashboard.log" 2>&1
    fi
  fi
}

# ------------------------------------------------------------------- select --
QUEUE=(); started=0
for iso in $ORDER; do
  st="$(status_of "$iso")"
  if [[ "$RETRY_FAILED" -eq 1 ]]; then
    [[ "$st" == "failed" || "$st" == "timeout" ]] || continue
  else
    [[ "$st" == "done" ]] && continue
  fi
  if [[ -n "$FROM" && $started -eq 0 ]]; then
    [[ "$iso" == "$FROM" ]] && started=1 || continue
  fi
  QUEUE+=("$iso")
  [[ "$LIMIT" -gt 0 && ${#QUEUE[@]} -ge "$LIMIT" ]] && break
done

echo ""
echo "=== plan ==="
echo "  countries queued : ${#QUEUE[@]}  ->  ${QUEUE[*]:-none}"
echo "  per-country cap  : $((TIMEOUT_SECS/60)) min, $MAX_TURNS turns"
echo "  permission mode  : $PERMISSION_MODE"
echo "  dashboard        : refreshed after every country; full rebuild every $DASH_EVERY"
echo "                     publish to GitHub Pages: $([[ $PUBLISH -eq 1 ]] && echo yes || echo no)"
echo "  logs             : $LOGDIR/"
echo "  manifest         : $MANIFEST   (touch STOP to halt gracefully)"

[[ ${#QUEUE[@]} -eq 0 ]] && { echo "nothing to do"; exit 0; }
[[ $DRY -eq 1 ]] && { echo ""; echo "(dry run - nothing executed)"; exit 0; }

# -------------------------------------------------------------------- execute --
run_start=$(date +%s); n=0
for iso in "${QUEUE[@]}"; do
  if [[ -f STOP ]]; then
    echo ""; echo "STOP file present - halting after $n countries."; rm -f STOP; break
  fi
  n=$((n+1))
  rb=$(rowcount "$iso"); sb=$(srccount "$iso")
  log="$LOGDIR/${iso}.log"
  t0=$(date +%s); started_at="$(date '+%Y-%m-%d %H:%M:%S')"
  echo ""
  echo "--- [$n/${#QUEUE[@]}] $iso  (rows=$rb sources=$sb)  $(date '+%H:%M:%S') ---"

  # Retry loop. An orchestrator that dies part-way leaves its work on disk and
  # records it in workflow_state.json, so a retry resumes rather than restarting
  # from zero. The aim is that every country completes, however many passes it
  # takes.
  attempt=0; st="unrun"
  while (( attempt < MAX_ATTEMPTS )); do
    attempt=$((attempt+1))
    [[ $attempt -gt 1 ]] && echo "    retry $attempt/$MAX_ATTEMPTS ($st) $(date '+%H:%M:%S')"

    timeout "$TIMEOUT_SECS" claude -p "$iso" \
        --agent workflow-orchestrator \
        --permission-mode "$PERMISSION_MODE" \
        --max-turns "$MAX_TURNS" \
        >> "$log" 2>&1 </dev/null
    code=$?

    case $code in
      0)   st="done" ;;
      124) st="timeout" ;;
      *)   st="failed" ;;
    esac
    agents_ran=$(find "data/$iso" -name 'search_log_agent_*.txt' -newermt "@$t0" 2>/dev/null | wc -l | tr -d ' ')
    [[ "$st" == "done" && "$agents_ran" -ge 7 ]] && break
    [[ -f STOP ]] && break
  done

  t1=$(date +%s); ra=$(rowcount "$iso"); sa=$(srccount "$iso")
  # A clean exit is not evidence the workflow ran. Classify on how many of the
  # seven agent logs were actually written during this country's run window.
  if [[ "$st" == "done" ]]; then
    if [[ "$agents_ran" -lt 7 ]]; then
      st="incomplete_${agents_ran}of7"
    elif [[ "$ra" -eq "$rb" && "$sa" -eq "$sb" ]]; then
      st="done_noyield"
    fi
  fi

  printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
    "$iso" "$st" "$started_at" "$(date '+%Y-%m-%d %H:%M:%S')" \
    "$rb" "$ra" "$sb" "$sa" "$code" "$log" >> "$MANIFEST"

  echo "    $st  attempts ${attempt}  agents ${agents_ran}/7  rows ${rb}->${ra} (+$((ra-rb)))  sources ${sb}->${sa} (+$((sa-sb)))  $(( (t1-t0)/60 ))min"
  python3 py/validate_quality.py "$iso" --quiet >/dev/null 2>&1 \
    || echo "    WARNING: $iso does not pass validation after its run"

  # Progress is monitored through the dashboard, so refresh it every country.
  # The full rebuild (weekly series, heatmaps, barplot) is heavier, so it runs
  # on a cadence rather than every time.
  if (( n % DASH_EVERY == 0 )); then refresh_dashboard full "$iso"; else refresh_dashboard light "$iso"; fi
  echo "    dashboard refreshed ($( (( n % DASH_EVERY == 0 )) && echo full || echo light))"
done

# --------------------------------------------------------------------- wrap --
echo ""
echo "=== run complete in $(( ($(date +%s)-run_start)/60 )) min ==="
refresh_dashboard full
python3 py/analyze_effective_gaps.py 2>&1 | tail -5
echo ""
echo "--- baseline integrity ---"
python3 py/protect_baselines.py verify
echo ""
awk -F, 'NR>1 {c[$2]++} END {for (k in c) printf "  %-18s %d\n", k, c[k]}' "$MANIFEST"
echo ""
python3 - <<'PYEOF'
import csv, json
mosaic = {k for k, v in json.load(open('reference/country_mapping.json'))['countries'].items()
          if v.get('mosaic_framework')}
last = {}
for r in csv.DictReader(open('reference/run_manifest.csv')):
    last[r['iso']] = r['status']
incomplete = sorted(i for i in mosaic if last.get(i) != 'done')
if incomplete:
    print(f"NOT YET COMPLETE ({len(incomplete)}/40): {' '.join(incomplete)}")
    print("Re-run `bash run_all_countries.sh --unattended --publish-progress` to continue;")
    print("countries already marked done are skipped.")
else:
    print("ALL 40 COUNTRIES COMPLETE.")
PYEOF
echo ""
python3 py/validate_quality.py --quiet 2>&1 | sed -n '2,4p'
[[ $PUBLISH -eq 1 ]] && echo "" && echo "Dashboard published to GitHub Pages." \
                     || { echo ""; echo "Dashboard updated locally only. To publish: bash update_dashboard.sh --publish"; }
