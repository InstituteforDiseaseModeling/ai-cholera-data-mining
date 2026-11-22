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

Pilot-country figures (figures/pilot/{ISO}/, shown in the dashboard's separate
"Pilot countries" section) carry their own stamp, a digest of figures/pilot/
only, so rebuilding a pilot never changes the 40 countries' figure URLs.
Both dashboard/dashboard.html and dashboard/country_status.html are stamped.

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
STATUS_PAGE = ROOT / "dashboard" / "country_status.html"
FIG_DIR = ROOT / "figures" / "dashboard"
PILOT_FIG_DIR = ROOT / "figures" / "pilot"

# ../figures/dashboard/<anything up to a quote/space/backtick>[?v=hex]
# Also matches the JS template literals (`...cholera_timeseries_${c.iso}.png`,
# `.../timelines/${filename}`), where the appended query string is equally valid.
FIG_REF = re.compile(r"(\.\./figures/dashboard/[^\"'\s`?]+)(\?v=[0-9a-f]*)?")
PILOT_FIG_REF = re.compile(r"(\.\./figures/pilot/[^\"'\s`?]+)(\?v=[0-9a-f]*)?")


def figure_version(fig_dir=FIG_DIR):
    h = hashlib.sha256()
    for p in sorted(fig_dir.rglob("*.png")):
        h.update(p.relative_to(fig_dir).as_posix().encode())
        h.update(b"\0")
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def pilot_figure_version():
    return figure_version(PILOT_FIG_DIR)


def stamp(html, version, pilot_version=None):
    html = FIG_REF.sub(lambda m: f"{m.group(1)}?v={version}", html)
    if pilot_version is not None:
        html = PILOT_FIG_REF.sub(lambda m: f"{m.group(1)}?v={pilot_version}", html)
    return html


def stale_refs(html, version, pilot_version=None):
    """Figure references whose stamp is missing or not the current version.
    Pilot-figure references are checked only when pilot_version is given."""
    out = [m.group(0) for m in FIG_REF.finditer(html) if m.group(2) != f"?v={version}"]
    if pilot_version is not None:
        out += [m.group(0) for m in PILOT_FIG_REF.finditer(html)
                if m.group(2) != f"?v={pilot_version}"]
    return out


def main():
    check_only = "--check" in sys.argv[1:]
    html = DASHBOARD.read_text(encoding="utf-8")
    version, pversion = figure_version(), pilot_figure_version()
    refs = FIG_REF.findall(html)
    if not refs:
        print(f"❌ no figure references found in {DASHBOARD}")
        return 1
    rc = 0
    for page in (DASHBOARD, STATUS_PAGE):
        if not page.exists():
            continue
        text = page.read_text(encoding="utf-8")
        n_refs = len(FIG_REF.findall(text)) + len(PILOT_FIG_REF.findall(text))
        stale = stale_refs(text, version, pversion)
        if check_only:
            print(f"{page.name}: figure version {version} / pilot {pversion}: "
                  f"{n_refs} refs, {len(stale)} stale")
            rc = rc or (1 if stale else 0)
            continue
        new = stamp(text, version, pversion)
        if new != text:
            tmp = page.with_suffix(".html.tmp")
            tmp.write_text(new, encoding="utf-8")
            tmp.replace(page)
        print(f"✅ {page.name}: figure version {version} / pilot {pversion}: stamped "
              f"{n_refs} figure references ({len(stale)} updated)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
