#!/usr/bin/env python3
"""Cache-bust the figure URLs in dashboard/dashboard.html.

The dashboard loads its figures from fixed paths under ../figures/dashboard/.
GitHub Pages serves the HTML with max-age=600 but the PNGs with max-age=14400,
so after a deploy a browser shows the new embedded data next to figures up to
four hours old - the figures look as if they were never updated even though the
published files are current.

This appends `?v=<hash>` to every figure reference, where <hash> is a digest of
the contents of every PNG under figures/dashboard/. Any changed figure changes
every URL, so browsers refetch; an unchanged figure set leaves the HTML
byte-identical, so a no-op rebuild produces no diff. Idempotent.

Run after all figures are built and before py/validate_dashboard.py, which
checks that the stamp is present and current.

Usage:
    python py/stamp_figure_versions.py [--check]
"""

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD = ROOT / "dashboard" / "dashboard.html"
FIG_DIR = ROOT / "figures" / "dashboard"

# ../figures/dashboard/<anything up to a quote/space/backtick>[?v=hex]
# Also matches the JS template literals (`...cholera_timeseries_${c.iso}.png`,
# `.../timelines/${filename}`), where the appended query string is equally valid.
FIG_REF = re.compile(r"(\.\./figures/dashboard/[^\"'\s`?]+)(\?v=[0-9a-f]*)?")


def figure_version(fig_dir=FIG_DIR):
    h = hashlib.sha256()
    for p in sorted(fig_dir.rglob("*.png")):
        h.update(p.relative_to(fig_dir).as_posix().encode())
        h.update(b"\0")
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def stamp(html, version):
    return FIG_REF.sub(lambda m: f"{m.group(1)}?v={version}", html)


def stale_refs(html, version):
    """Figure references whose stamp is missing or not the current version."""
    return [m.group(0) for m in FIG_REF.finditer(html) if m.group(2) != f"?v={version}"]


def main():
    check_only = "--check" in sys.argv[1:]
    html = DASHBOARD.read_text(encoding="utf-8")
    version = figure_version()
    refs = FIG_REF.findall(html)
    if not refs:
        print(f"❌ no figure references found in {DASHBOARD}")
        return 1
    stale = stale_refs(html, version)
    if check_only:
        print(f"figure version {version}: {len(refs)} refs, {len(stale)} stale")
        return 1 if stale else 0
    new = stamp(html, version)
    if new != html:
        tmp = DASHBOARD.with_suffix(".html.tmp")
        tmp.write_text(new, encoding="utf-8")
        tmp.replace(DASHBOARD)
    print(f"✅ figure version {version}: stamped {len(refs)} figure references "
          f"({len(stale)} updated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
