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
#   bash run_all_countries.sh --dry-run            # show the plan, run nothing
#   bash run_all_countries.sh --limit 1            # pilot: stalest country only
#   bash run_all_countries.sh                      # full re-run, all 40
#   bash run_all_countries.sh --from KEN           # resume at a country
#   bash run_all_countries.sh --only ETH,KEN       # specific countries
#   bash run_all_countries.sh --retry-failed       # re-attempt failures only
#
# State lives in reference/run_manifest.csv and survives interruption: a country
# marked `done` is skipped on the next invocation, so Ctrl-C and restart is safe.
#
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

MANIFEST="reference/run_manifest.csv"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOGDIR="logs/run_${STAMP}"
TIMEOUT_SECS=${TIMEOUT_SECS:-14400}        # 4h per country
PERMISSION_MODE="acceptEdits"
MAX_TURNS=${MAX_TURNS:-600}
DRY=0; LIMIT=0; FROM=""; ONLY=""; RETRY_FAILED=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)        DRY=1 ;;
    --limit)          LIMIT="$2"; shift ;;
    --from)           FROM="$2"; shift ;;
    --only)           ONLY="$2"; shift ;;
    --retry-failed)   RETRY_FAILED=1 ;;
    --timeout)        TIMEOUT_SECS="$2"; shift ;;
    --permission-mode) PERMISSION_MODE="$2"; shift ;;
    -h|--help)        sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

command -v claude >/dev/null || { echo "claude CLI not found" >&2; exit 1; }
mkdir -p "$LOGDIR" reference

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
[[ $fail -eq 0 ]] && echo "  ok: profiles, validation gate, protocol, gap analysis" \
                  || { echo "preflight failed; not starting"; exit 1; }

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

if [[ -n "$ONLY" ]]; then
  ORDER=$(echo "$ONLY" | tr ',' ' ' | tr '[:lower:]' '[:upper:]')
fi

# ----------------------------------------------------------------- manifest --
if [[ ! -f "$MANIFEST" ]]; then
  echo "iso,status,started,finished,rows_before,rows_after,sources_before,sources_after,exit_code,log" > "$MANIFEST"
fi

status_of () { awk -F, -v i="$1" '$1==i {s=$2} END {print s}' "$MANIFEST"; }
rowcount () { local f="data/$1/cholera_data_ai.csv"; [[ -f "$f" ]] && echo $(( $(wc -l < "$f") - 1 )) || echo 0; }
srccount () { local f="data/$1/metadata_ai.csv";   [[ -f "$f" ]] && echo $(( $(wc -l < "$f") - 1 )) || echo 0; }

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
echo "  logs             : $LOGDIR/"
echo "  manifest         : $MANIFEST"

if [[ ${#QUEUE[@]} -eq 0 ]]; then echo "nothing to do"; exit 0; fi
if [[ $DRY -eq 1 ]]; then echo ""; echo "(dry run - nothing executed)"; exit 0; fi

# -------------------------------------------------------------------- execute --
run_start=$(date +%s)
for iso in "${QUEUE[@]}"; do
  rb=$(rowcount "$iso"); sb=$(srccount "$iso")
  log="$LOGDIR/${iso}.log"
  t0=$(date +%s); started_at="$(date '+%Y-%m-%d %H:%M:%S')"
  echo ""
  echo "--- $iso  (rows=$rb sources=$sb)  $(date '+%H:%M:%S') ---"

  timeout "$TIMEOUT_SECS" claude -p "$iso" \
      --agent workflow-orchestrator \
      --permission-mode "$PERMISSION_MODE" \
      --max-turns "$MAX_TURNS" \
      > "$log" 2>&1 </dev/null
  code=$?

  t1=$(date +%s); ra=$(rowcount "$iso"); sa=$(srccount "$iso")
  case $code in
    0)   st="done" ;;
    124) st="timeout" ;;
    *)   st="failed" ;;
  esac
  # A clean exit that added nothing is still suspicious; surface it rather than
  # recording a silent success.
  [[ "$st" == "done" && "$ra" -eq "$rb" && "$sa" -eq "$sb" ]] && st="done_noyield"

  printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
    "$iso" "$st" "$started_at" "$(date '+%Y-%m-%d %H:%M:%S')" \
    "$rb" "$ra" "$sb" "$sa" "$code" "$log" >> "$MANIFEST"

  echo "    $st  rows ${rb}->${ra} (+$((ra-rb)))  sources ${sb}->${sa} (+$((sa-sb)))  $(( (t1-t0)/60 ))min"
  python3 py/validate_quality.py "$iso" --quiet >/dev/null 2>&1 \
    || echo "    WARNING: $iso does not pass validation after its run"
done

# --------------------------------------------------------------------- wrap --
echo ""
echo "=== run complete in $(( ($(date +%s)-run_start)/60 )) min ==="
python3 py/analyze_effective_gaps.py 2>&1 | tail -5
echo ""
awk -F, 'NR>1 {c[$2]++} END {for (k in c) printf "  %-14s %d\n", k, c[k]}' "$MANIFEST"
echo ""
echo "Dashboard was NOT published. To publish: bash update_dashboard.sh --publish"
