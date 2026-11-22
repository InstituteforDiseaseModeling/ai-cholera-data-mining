"""Dashboard pilot section: kept apart from the 40-country table, badged, its
figure stamped separately, and the embedded-metadata leak check."""
import sys
from pathlib import Path

PY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PY))

import generate_country_status_page as gcsp  # noqa: E402
import stamp_figure_versions as sfv  # noqa: E402
import validate_dashboard as vd  # noqa: E402


def _pilot_row(**kw):
    r = {"iso": "NPL", "name": "Nepal", "state": "Complete", "cls": "ok",
         "qual": "refreshed this cycle", "qcls": "ok", "flags": ["now"] * 7, "n_agents": 7,
         "last_run": "2026-11-22 12:00", "delta": 387, "obs": 387, "sources": 290,
         "span": "1958-2026", "presence": 13, "subregion": "South Asia", "prefix": "SEAR",
         "coverage": {"percent_coverage": "87.0", "months_with_data": "594", "total_months": "683",
                      "gap_periods": "2", "months_ai_only": "105"},
         "weeks": (86, 1348, 72), "report": True,
         "figure": "../figures/pilot/NPL/cholera_timeseries_NPL.png"}
    r.update(kw)
    return r


def test_pilot_fragment_is_badged_and_never_uses_the_mosaic_row_class():
    html = gcsp.pilot_fragment([_pilot_row()], "0123456789ab")
    assert '<td class="cs-pilot-iso" data-sort="NPL">' in html
    assert '<td class="cs-iso"' not in html          # the 40-row count stays 40
    assert "cs-badge-pilot" in html and "PILOT" in html
    assert "Outside the 40 MOSAIC framework countries" in html
    assert "SEAR::NPL" in html
    assert "../figures/pilot/NPL/cholera_timeseries_NPL.png?v=0123456789ab" in html
    assert "../data/NPL/search_report.txt" in html


def test_pilot_fragment_without_pilots_says_so():
    html = gcsp.pilot_fragment([], "0123456789ab")
    assert "No pilot country has been processed" in html
    assert "cs-pilot-iso" not in html


def test_pilot_and_dashboard_figures_carry_separate_stamps():
    html = ('<img src="../figures/dashboard/plots/a.png?v=000000000000">'
            '<img src="../figures/pilot/NPL/b.png">')
    out = sfv.stamp(html, "aaaaaaaaaaaa", "bbbbbbbbbbbb")
    assert "../figures/dashboard/plots/a.png?v=aaaaaaaaaaaa" in out
    assert "../figures/pilot/NPL/b.png?v=bbbbbbbbbbbb" in out
    assert sfv.stale_refs(out, "aaaaaaaaaaaa", "bbbbbbbbbbbb") == []
    # a pilot rebuild (new pilot stamp) leaves the 40 countries' URLs unchanged
    out2 = sfv.stamp(out, "aaaaaaaaaaaa", "cccccccccccc")
    assert "../figures/dashboard/plots/a.png?v=aaaaaaaaaaaa" in out2


def test_embedded_keys_ignore_text_inside_template_literals():
    html = ("const embeddedMetadata = {\n"
            "            'AGO': `Index,Source\n1,'XYZ': \\`not a key\\` {brace`,\n"
            "            'NPL': `Index,Source`\n        };\nconst other = {};")
    assert vd.embedded_keys(html, "const embeddedMetadata") == ["AGO", "NPL"]
