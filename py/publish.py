#!/usr/bin/env python3
"""Serialised git add/commit/push for the unattended run.

Two things publish to GitHub Pages during a run: the per-country dashboard
refresh in run_all_countries.sh, and the liveness heartbeat. Left to themselves
they race - one pushes, the other's push is rejected as non-fast-forward, and
its output disappears into a log nobody reads. macOS ships no flock(1), so the
lock lives here in Python instead of in the shell.

Usage:
    python py/publish.py -m "message" dashboard/ reference/run_manifest.csv
"""
import argparse
import fcntl
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "reference" / ".git_publish.lock"


def git(*args, check=False):
    return subprocess.run(["git", *args], cwd=ROOT, check=check,
                          capture_output=True, text=True)


def publish(paths, message, push=True):
    existing = [p for p in paths if (ROOT / p).exists()]
    if not existing:
        return "nothing to add"

    with open(LOCK, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)          # blocks until the other one is done
        git("add", "--", *existing)
        if git("diff", "--staged", "--quiet").returncode == 0:
            return "no changes"
        if git("commit", "-q", "-m", message).returncode != 0:
            return "commit failed"
        if not push:
            return "committed (not pushed)"
        branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "main"
        r = git("push", "-q", "origin", branch)
        if r.returncode == 0:
            return "pushed"
        # Serialisation makes this unlikely, but a push from elsewhere (a
        # human, another clone) still leaves us behind. Rebase only our own
        # commits; never touch the working tree, which agents are writing to.
        git("fetch", "-q", "origin", branch)
        r2 = git("rebase", "-q", f"origin/{branch}")
        if r2.returncode != 0:
            git("rebase", "--abort")
            return f"push rejected, rebase failed: {r.stderr.strip()[:120]}"
        r3 = git("push", "-q", "origin", branch)
        return "pushed after rebase" if r3.returncode == 0 \
            else f"push failed: {r3.stderr.strip()[:120]}"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("-m", "--message", required=True)
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()
    print(publish(a.paths, a.message, push=not a.no_push))
    return 0


if __name__ == "__main__":
    sys.exit(main())
