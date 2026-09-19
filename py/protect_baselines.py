#!/usr/bin/env python3
"""
Protect the read-only JHU/WHO baseline files during an unattended run.

CLAUDE.md declares cholera_data_jhu.csv and cholera_data_who.csv read-only to
agents, and .claude/settings.json carries deny rules saying so. Those rules stop
being enforced under --permission-mode bypassPermissions, which is exactly the
mode an unattended run uses. This provides protection that does not depend on
the permission layer at all:

  lock    clear the write bit (chmod a-w) so a stray write fails at the OS level
  verify  compare every baseline against a recorded SHA-256 and report drift
  unlock  restore write permission (needed to refresh baselines deliberately)

The checksum manifest is the part that matters most. chmod stops an accidental
write; the manifest tells you whether one happened anyway, which is the question
you actually want answered after a 40-country run.

Usage:
    python py/protect_baselines.py lock      # record checksums + make read-only
    python py/protect_baselines.py verify    # non-zero exit if anything drifted
    python py/protect_baselines.py unlock    # restore write permission
"""

import hashlib
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
MANIFEST = ROOT / "reference" / "baseline_checksums.json"
BASELINES = ("cholera_data_jhu.csv", "cholera_data_who.csv")


def baseline_files():
    return sorted(p for iso in sorted(os.listdir(DATA))
                  if (DATA / iso).is_dir() and len(iso) == 3 and iso.isupper()
                  for p in ((DATA / iso / b) for b in BASELINES) if p.exists())


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_lock():
    files = baseline_files()
    manifest = {}
    for p in files:
        manifest[str(p.relative_to(ROOT))] = {"sha256": sha(p), "bytes": p.stat().st_size}
        mode = p.stat().st_mode
        p.chmod(mode & ~stat.S_IWUSR & ~stat.S_IWGRP & ~stat.S_IWOTH)
    MANIFEST.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": ("Baselines are chmod a-w and checksummed. Run "
                 "`python py/protect_baselines.py verify` after any unattended "
                 "run to confirm nothing modified them."),
        "files": manifest,
    }, indent=2) + "\n")
    print(f"LOCKED {len(files)} baseline files (chmod a-w)")
    print(f"  checksums -> {MANIFEST.relative_to(ROOT)}")
    return 0


def cmd_verify():
    if not MANIFEST.exists():
        print("no checksum manifest; run `lock` first", file=sys.stderr)
        return 2
    recorded = json.loads(MANIFEST.read_text())["files"]
    drift, missing, added = [], [], []
    seen = set()
    for p in baseline_files():
        rel = str(p.relative_to(ROOT))
        seen.add(rel)
        if rel not in recorded:
            added.append(rel)
            continue
        if sha(p) != recorded[rel]["sha256"]:
            drift.append(rel)
    missing = [r for r in recorded if r not in seen]

    for rel in drift:
        print(f"  MODIFIED  {rel}")
    for rel in missing:
        print(f"  MISSING   {rel}")
    for rel in added:
        print(f"  NEW       {rel}")

    total = len(recorded)
    if not (drift or missing):
        print(f"OK: all {total} baseline files unchanged"
              + (f" ({len(added)} new file(s) added)" if added else ""))
        return 0
    print(f"\nFAIL: {len(drift)} modified, {len(missing)} missing, out of {total}")
    return 1


def cmd_unlock():
    files = baseline_files()
    for p in files:
        p.chmod(p.stat().st_mode | stat.S_IWUSR)
    print(f"UNLOCKED {len(files)} baseline files (owner write restored)")
    return 0


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("lock", "verify", "unlock"):
        print(__doc__)
        return 2
    return {"lock": cmd_lock, "verify": cmd_verify, "unlock": cmd_unlock}[sys.argv[1]]()


if __name__ == "__main__":
    sys.exit(main())
