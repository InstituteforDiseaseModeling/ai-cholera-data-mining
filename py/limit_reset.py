#!/usr/bin/env python3
"""Seconds to wait before the account spend limit is worth retrying.

The CLI states when the limit resets, in two forms:

    ...your session limit resets 10am (America/Los_Angeles)
    ...your weekly limit resets Sep 21 at 5am (America/Los_Angeles)

Probing on a fixed interval before then is pure waste: each probe starts a
country, is refused in about three seconds, and appends a `blocked_spend_limit`
row to the manifest. Reading the stated time instead means one retry, at the
moment it can succeed.

Prints seconds to wait (0 if no block message is found, meaning retry now).
Exits 0 always - a parsing failure must not stop the run resuming.
"""
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
# "resets [Sep 21 at ]5am" / "...5:30pm"
PAT = re.compile(
    r"limit resets\s+(?:(?P<mon>[A-Za-z]{3})\s+(?P<day>\d{1,2})\s+at\s+)?"
    r"(?P<hour>\d{1,2})(?::(?P<min>\d{2}))?\s*(?P<ampm>am|pm)", re.I)

# The stated time is in the account's timezone; this machine is set to the same
# zone, so no conversion is applied. A buffer avoids retrying a second early.
BUFFER_SECONDS = 120
MAX_WAIT = 8 * 24 * 3600


def newest_block_message():
    logs = sorted(ROOT.glob("logs/run_*/*.log"), key=lambda p: p.stat().st_mtime,
                  reverse=True)
    for p in logs[:40]:
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        if "spend limit" not in text.lower() and "usage limit" not in text.lower():
            continue
        for line in reversed(text.splitlines()):
            if PAT.search(line):
                return line, p
    return None, None


def main():
    line, src = newest_block_message()
    if not line:
        print(0)
        return 0
    m = PAT.search(line)
    now = datetime.now()
    hour = int(m.group("hour")) % 12
    if m.group("ampm").lower() == "pm":
        hour += 12
    minute = int(m.group("min") or 0)

    if m.group("mon"):
        mon = MONTHS.get(m.group("mon").lower())
        day = int(m.group("day"))
        year = now.year
        target = datetime(year, mon, day, hour, minute)
        # A stated month/day in the past means next year's occurrence.
        if target < now - timedelta(days=180):
            target = datetime(year + 1, mon, day, hour, minute)
    else:
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)   # e.g. "10am" stated at 11am means tomorrow

    wait = (target - now).total_seconds() + BUFFER_SECONDS
    wait = max(0, min(wait, MAX_WAIT))
    print(int(wait))
    print(f"# {src.relative_to(ROOT) if src else '?'}: resets {target:%Y-%m-%d %H:%M} "
          f"-> wait {int(wait)//60} min", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
