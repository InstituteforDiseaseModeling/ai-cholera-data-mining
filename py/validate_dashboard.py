#!/usr/bin/env python3
"""Structural checks on dashboard/dashboard.html before it is published.

This exists because the dashboard has now been broken twice by edits to a 10 MB
file that no test covered:

  1. A regex of the form `\\.selector[^{]*\\{[^}]*\\}` intended to strip dead CSS
     matched across the embedded JSON and truncated the file from 10 MB to
     164 KB.
  2. Removing a dead CSS block by line range dropped the closing brace of the
     rule that followed it. The unterminated rule swallowed the rest of the
     stylesheet, and the published page rendered badly corrupted. Every
     individual string in the page was correct; only the structure was wrong.

Both were mechanical and both would have been caught here. Run before publishing.

Country scope is checked explicitly against py/scope.py: the country table and
the embedded source metadata must hold exactly the 40 MOSAIC countries, and the
separate "Pilot countries" section exactly the processed pilot countries
(scope.pilot_isos() with a data/{ISO}/ directory). A rebuild that iterated over
data/* once embedded the Nepal pilot's sources into the 40-country tables.
dashboard/country_status.html is checked the same way when the default
dashboard is validated.

Exit status: 0 all checks pass, 1 a check failed.

Usage:
    python py/validate_dashboard.py [path]
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "dashboard" / "dashboard.html"
STATUS_PAGE = ROOT / "dashboard" / "country_status.html"
PILOT_START = "<!-- PILOT-COUNTRIES:START -->"
PILOT_END = "<!-- PILOT-COUNTRIES:END -->"
sys.path.insert(0, str(ROOT / "py"))
import scope  # noqa: E402

# The page is large because the source metadata is embedded in it (the
# observations are not: they load from data/{ISO}/cholera_data_ai.csv). A result
# far outside this band means an edit removed or added something enormous.
MIN_BYTES = 5_000_000
MAX_BYTES = 40_000_000

REQUIRED = [
    "const completionChecklistCSV",
    "const embeddedMetadata",
    "const embeddedCholeraData",
    # The observations table loads data/{ISO}/cholera_data_ai.csv on demand. The
    # embedded copy must stay an empty stub: from Aug 2025 to Oct 2026 a silently
    # failing re-embed left a 14-month-old snapshot in the table.
    "const embeddedCholeraData = {};",
    "function parseCSVText",
    "function renderCholeraRows",
    "/cholera_data_ai.csv`",
    "<!-- COUNTRY-STATUS:START -->",
    "<!-- COUNTRY-STATUS:END -->",
    PILOT_START,
    PILOT_END,
]


def strip_css_noise(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return re.sub(r'"[^"]*"|\'[^\']*\'', "", css)


def make_ok(fails):
    def ok(name, cond, detail=""):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if detail and not cond else ""))
        if not cond:
            fails.append(name)
    return ok


def embedded_keys(t, decl):
    """Top-level keys of `<decl> = { 'ISO': `...`, ... }`. Template literals are
    skipped (their text is CSV with backslash escapes), so only real keys count."""
    m = re.search(re.escape(decl) + r"\s*=\s*\{", t)
    if not m:
        return []
    keys, depth, in_tpl, i, start = [], 1, False, m.end(), m.end()
    while i < len(t) and depth:
        c = t[i]
        if in_tpl:
            if c == "\\":
                i += 2
                continue
            if c == "`":
                in_tpl = False
                start = i + 1
        elif c == "`":
            km = re.search(r"['\"]?([A-Za-z0-9_]+)['\"]?\s*:\s*$", t[start:i])
            if km:
                keys.append(km.group(1))
            in_tpl = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    return keys


def mosaic_rows(t):
    return re.findall(r'<td class="cs-iso" data-sort="([A-Z]{3})"', t)


def pilot_checks(t, ok, label):
    """The pilot section: exactly the processed pilot countries, badged, kept
    apart from the 40-country table, each with its prefix and its figure."""
    pilots = sorted(i for i in scope.pilot_isos() if (ROOT / "data" / i).is_dir())
    if PILOT_START in t and PILOT_END in t:
        i = t.index(PILOT_START)
        sec = t[i:t.index(PILOT_END, i)]
    else:
        k = t.find('<div class="cs-wrap cs-pilot">')
        sec = t[k:] if k >= 0 else ""
    rows = re.findall(r'<td class="cs-pilot-iso" data-sort="([A-Z]{3})"', t)
    ok(f"{label}: pilot section present", bool(sec))
    ok(f"{label}: pilot rows = processed pilot countries {pilots}", sorted(rows) == pilots,
       f"found {rows}")
    ok(f"{label}: pilot rows only inside the pilot section",
       sec.count('<td class="cs-pilot-iso"') == len(rows))
    ok(f"{label}: pilot section badged PILOT and marked outside the 40",
       "cs-badge-pilot" in sec and "Outside the 40 MOSAIC framework countries" in sec)
    ok(f"{label}: no pilot country in the 40-country table",
       not set(mosaic_rows(t)) & set(scope.pilot_isos()))
    for iso in pilots:
        code = f"{scope.location_prefix(iso)}::{iso}"
        ok(f"{label}: {iso} row shows its location prefix {code}", code in sec)
        fig = ROOT / "figures" / "pilot" / iso / f"cholera_timeseries_{iso}.png"
        if fig.exists():
            ok(f"{label}: {iso} weekly-series figure shown",
               f"../figures/pilot/{iso}/{fig.name}?v=" in sec)


def check(path):
    fails = []
    t = path.read_text()
    ok = make_ok(fails)

    ok(f"size within {MIN_BYTES//1_000_000}-{MAX_BYTES//1_000_000} MB",
       MIN_BYTES < len(t) < MAX_BYTES, f"{len(t):,} bytes")

    for s in REQUIRED:
        ok(f"present: {s[:42]}", s in t)

    # ---- stylesheet brace balance -------------------------------------
    styles = re.findall(r"<style[^>]*>(.*?)</style>", t, re.S)
    ok("has at least one <style> block", bool(styles))
    for i, css in enumerate(styles, 1):
        c = strip_css_noise(css)
        o, cl = c.count("{"), c.count("}")
        detail = f"{{ {o} vs }} {cl}"
        if o != cl:
            # name the rule that never closes, so the fix is obvious
            depth, line, start = 0, 1, 0
            for ch in c:
                if ch == "\n":
                    line += 1
                elif ch == "{":
                    if depth == 0:
                        start = line
                    depth += 1
                elif ch == "}":
                    depth = max(0, depth - 1)
            if depth:
                detail += f"; unclosed rule opens near css line {start}"
        ok(f"style block {i} braces balanced", o == cl, detail)

    # ---- inline script syntax ----------------------------------------
    scripts = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", t, re.S)
    node = shutil.which("node")
    if not node:
        print("  SKIP  inline script syntax (node not installed)")
    else:
        for i, js in enumerate(scripts, 1):
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
                fh.write(js)
                tmp = fh.name
            r = subprocess.run([node, "--check", tmp], capture_output=True, text=True)
            Path(tmp).unlink(missing_ok=True)
            ok(f"script block {i} parses", r.returncode == 0,
               (r.stderr or "").strip().splitlines()[0] if r.stderr else "")

    # ---- element balance ---------------------------------------------
    body = t[t.index("<body>"):] if "<body>" in t else t
    body = re.sub(r"<script\b.*?</script>", " ", body, flags=re.S)
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
    for tag in ("div", "table", "tbody", "thead"):
        o = len(re.findall(rf"<{tag}\b", body))
        c = len(re.findall(rf"</{tag}>", body))
        ok(f"<{tag}> balanced", o == c, f"{o} open / {c} close")

    # ---- JS referencing elements that no longer exist -----------------
    ids_used = set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", t))
    ids_used |= set(re.findall(r"querySelector\(['\"]#([A-Za-z0-9_-]+)", t))
    ids_def = set(re.findall(r'\bid="([^"]+)"', t))
    dead = sorted(i for i in ids_used if i not in ids_def and "${" not in i)
    ok("no JS references to absent element ids", not dead, str(dead))

    # ---- unresolved generated placeholders ---------------------------
    unresolved = re.findall(r"<!--STAT:([a-z0-9_]+)-->\s*(?:unknown|TBD|)\s*<!--/STAT-->", t)
    ok("no unresolved STAT placeholders", not unresolved, str(unresolved))
    ok("country table populated",
       t.count('<td class="cs-iso"') == 40, f'{t.count(chr(60) + "td class=" + chr(34) + "cs-iso" + chr(34))} rows')

    # ---- country scope: the 40 MOSAIC countries and the pilots, apart --
    mosaic = scope.mosaic_isos()
    ok("country table = the 40 MOSAIC countries (scope.mosaic_isos())",
       len(mosaic) == 40 and sorted(mosaic_rows(t)) == mosaic,
       f"{len(mosaic_rows(t))} rows; not MOSAIC: {sorted(set(mosaic_rows(t)) - set(mosaic))}")
    meta_keys = embedded_keys(t, "const embeddedMetadata")
    leaked = sorted(set(meta_keys) - set(mosaic))
    ok("embedded metadata limited to the 40 MOSAIC countries",
       bool(meta_keys) and not leaked, f"non-MOSAIC keys: {leaked}")
    pilot_checks(t, ok, "dashboard")

    # ---- figure URLs cache-busted to the current figure set ----------
    # Pages caches PNGs for 4 h at fixed URLs; without a current ?v= stamp the
    # live page pairs new data with old figures (py/stamp_figure_versions.py).
    sys.path.insert(0, str(ROOT / "py"))
    from stamp_figure_versions import FIG_REF, figure_version, pilot_figure_version, stale_refs
    stale = stale_refs(t, figure_version(), pilot_figure_version())
    ok("figure URLs stamped with current figure version",
       bool(FIG_REF.search(t)) and not stale, f"{len(stale)} stale, e.g. {stale[:1]}")

    return fails


def check_status_page(path):
    """dashboard/country_status.html: same scope rules as the dashboard."""
    fails = []
    t = path.read_text()
    ok = make_ok(fails)
    mosaic = scope.mosaic_isos()
    ok("status page: country table = the 40 MOSAIC countries",
       sorted(mosaic_rows(t)) == mosaic, f"{len(mosaic_rows(t))} rows")
    pilot_checks(t, ok, "status page")
    body = re.sub(r"<script\b.*?</script>", " ", t, flags=re.S)
    for tag in ("div", "table", "tbody", "thead"):
        o = len(re.findall(rf"<{tag}\b", body))
        c = len(re.findall(rf"</{tag}>", body))
        ok(f"status page: <{tag}> balanced", o == c, f"{o} open / {c} close")
    from stamp_figure_versions import figure_version, pilot_figure_version, stale_refs
    stale = stale_refs(t, figure_version(), pilot_figure_version())
    ok("status page: figure URLs stamped", not stale, f"{len(stale)} stale, e.g. {stale[:1]}")
    return fails


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    if not path.exists():
        print(f"not found: {path}")
        return 1
    print(f"Validating {path}")
    fails = check(path)
    if len(sys.argv) <= 1 and STATUS_PAGE.exists():
        print(f"Validating {STATUS_PAGE}")
        fails += check_status_page(STATUS_PAGE)
    print()
    if fails:
        print(f"{len(fails)} check(s) FAILED: {', '.join(fails)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
