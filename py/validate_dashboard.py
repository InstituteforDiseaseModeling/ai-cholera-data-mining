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

# The page is ~10 MB because the source data is embedded in it. A result far
# outside this band means an edit removed something enormous.
MIN_BYTES = 5_000_000
MAX_BYTES = 40_000_000

REQUIRED = [
    "const completionChecklistCSV",
    "const embeddedMetadata",
    "const embeddedCholeraData",
    "<!-- COUNTRY-STATUS:START -->",
    "<!-- COUNTRY-STATUS:END -->",
]


def strip_css_noise(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return re.sub(r'"[^"]*"|\'[^\']*\'', "", css)


def check(path):
    fails = []
    t = path.read_text()

    def ok(name, cond, detail=""):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  {detail}" if detail and not cond else ""))
        if not cond:
            fails.append(name)

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

    return fails


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    if not path.exists():
        print(f"not found: {path}")
        return 1
    print(f"Validating {path}")
    fails = check(path)
    print()
    if fails:
        print(f"{len(fails)} check(s) FAILED: {', '.join(fails)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
