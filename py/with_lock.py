#!/usr/bin/env python3
"""Run a command while holding a named exclusive lock.

Countries run in parallel, each in its own OS process, and each country's own
data lives in its own directory - but a few things are shared: the dashboard
build, the gap-analysis reference files and the git index. Two processes
rebuilding the dashboard at once corrupt each other's output and collide on
.git/index.lock. macOS ships no flock(1), so the lock lives here.

Usage:
    python py/with_lock.py dashboard -- bash update_dashboard.sh
    python py/with_lock.py gaps -- python py/analyze_effective_gaps.py
"""
import fcntl
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(argv):
    if "--" not in argv or len(argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    i = argv.index("--")
    name, cmd = argv[0], argv[i + 1:]
    if not cmd:
        print("no command given", file=sys.stderr)
        return 2

    lock = ROOT / "reference" / f".{name}.lock"
    with open(lock, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        return subprocess.run(cmd, cwd=ROOT).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
