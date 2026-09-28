#!/usr/bin/env bash
#
# Start the unattended multi-country run on dugong, in a detached tmux session.
#
# Several countries run at once (PARALLEL). Each country's data is committed and
# pushed when it ends, in-progress data and a light dashboard rebuild are pushed
# every CHECKPOINT_EVERY heartbeats (10 min each), and the full dashboard is
# rebuilt after every DASH_EVERY completed countries. GitHub Pages redeploys on
# each push via .github/workflows/deploy-dashboard.yml.
#
# Usage (on dugong):
#   bash py/start_dugong_run.sh                 # 4 countries at a time
#   PARALLEL=2 bash py/start_dugong_run.sh
#   tmux attach -t cholera                      # watch; Ctrl-b d to detach
#   touch STOP                                  # halt after in-flight countries finish
#
# Environment is passed into tmux explicitly: if a tmux server is already
# running (other jobs on this machine), a new session inherits the server's
# environment, not this shell's, and exports here would silently not apply.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV="${VENV:-$HOME/.venvs/cholera}"
RUN_PATH="$VENV/bin:$HOME/.local/bin:$PATH"
PARALLEL="${PARALLEL:-4}"
DASH_EVERY="${DASH_EVERY:-1}"
CHECKPOINT_EVERY="${CHECKPOINT_EVERY:-3}"
SESSION="${SESSION:-cholera}"
# limit_reset.py reads the CLI's "resets 2:20pm (America/Los_Angeles)" message
# as local time, so the run must be on the account's timezone. dugong's system
# clock is UTC.
RUN_TZ="${RUN_TZ:-America/Los_Angeles}"

fail () { echo "PREFLIGHT FAILED: $*" >&2; exit 1; }

if tmux has-session -t "$SESSION" 2>/dev/null; then
  fail "tmux session '$SESSION' already exists - attach with: tmux attach -t $SESSION"
fi
pgrep -f "bash run_all_countries.sh" >/dev/null && fail "a runner is already running on this machine"

[[ -x "$VENV/bin/python3" ]] || fail "no Python venv at $VENV"
PATH="$RUN_PATH" python3 -c "import pandas, matplotlib, PIL" 2>/dev/null \
  || fail "venv at $VENV is missing requirements.txt packages"
PATH="$RUN_PATH" command -v claude >/dev/null || fail "claude CLI not on PATH (expected ~/.local/bin/claude)"

echo "checking Claude login ..."
reply="$(cd /tmp && PATH="$RUN_PATH" timeout 120 claude -p "Reply with just: ok" \
  --model claude-opus-5-5 --max-turns 1 2>&1 || true)"
[[ "$reply" == *ok* ]] || fail "claude is not logged in or cannot reach the API: ${reply:0:200}"

echo "checking GitHub push access ..."
git push --dry-run -q origin HEAD >/dev/null 2>&1 \
  || fail "cannot push to origin ($(git remote get-url origin)) - is the deploy key set up?"

echo "updating checkout ..."
git pull -q --ff-only || fail "git pull --ff-only failed - resolve local changes first"
rm -f STOP

tmux new-session -d -s "$SESSION" \
  "env PATH='$RUN_PATH' TZ='$RUN_TZ' PARALLEL='$PARALLEL' DASH_EVERY='$DASH_EVERY' \
   CHECKPOINT_EVERY='$CHECKPOINT_EVERY' bash py/run_supervisor.sh 900; \
   echo 'supervisor exited'; exec bash"

echo "started: tmux session '$SESSION' (parallel=$PARALLEL, dash_every=$DASH_EVERY, checkpoint every $((CHECKPOINT_EVERY*10)) min)"
echo "  watch:  tmux attach -t $SESSION      logs: $ROOT/logs/"
echo "  stop:   touch $ROOT/STOP             (in-flight countries finish first)"
