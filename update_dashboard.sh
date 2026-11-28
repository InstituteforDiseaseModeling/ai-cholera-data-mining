#!/bin/bash

# MOSAIC AI Cholera Data Collection - Dashboard Update Script
# 
# This script provides a simple command for agents to update all dashboard data:
# - Completion checklist (based on file analysis)
# - 3-source timeline coverage plots (with synchronized date ranges)
# - Coverage barplot (percentage of months with observations by source)
# - Coverage heatmaps (national and sub-national data visualization)
# - Timeline week counts data (embedded in dashboard)
# - All data source embedding (AI-mined, WHO, and JHU data)
# - Dashboard HTML with all embedded data
# - Figure URLs cache-busted with a content-hash ?v= stamp (all figures are
#   rebuilt on every run; this is the only dashboard refresh path)
#
# Usage: bash update_dashboard.sh
# or: chmod +x update_dashboard.sh && ./update_dashboard.sh

# Enable strict error handling
set -euo pipefail

# ---------------------------------------------------------------- coalescing --
# The runner calls this after EVERY country, serialised by `py/with_lock.py
# dashboard`. A rebuild takes ~7 min; on 2026-11-16 short recency countries
# finished every 2-3 min, so finished countries queued for the lock (38 min
# deep) and held their parallel slots, leaving 3 of 10 slots collecting.
#
# Every queued rebuild after the first is redundant: a rebuild that STARTED
# after this request was queued reads the disk after that country's data was
# written, so it already contains it. So: when invoked under with_lock, take
# the time the lock was requested (the with_lock process's start), and skip if
# a rebuild has started since. Manual invocations (parent is not with_lock) are
# never skipped. A failed rebuild clears its stamp so waiters do not skip it.
DASH_STAMP="reference/.dashboard_rebuild_started"
if ps -o command= -p "$PPID" 2>/dev/null | grep -q "with_lock.py dashboard"; then
    queued_at=$(python3 - "$PPID" <<'PYEOF'
import subprocess, sys, time
et = subprocess.run(["ps", "-o", "etime=", "-p", sys.argv[1]], capture_output=True, text=True).stdout.strip()
days = 0
if "-" in et:
    d, et = et.split("-", 1); days = int(d)
parts = [int(x) for x in et.split(":")]
while len(parts) < 3:
    parts.insert(0, 0)
h, m, s = parts
print(int(time.time() - (days * 86400 + h * 3600 + m * 60 + s)))
PYEOF
)
    last_start=$(cat "$DASH_STAMP" 2>/dev/null || echo 0)
    if [[ "$queued_at" =~ ^[0-9]+$ && "$last_start" =~ ^[0-9]+$ ]] && (( last_start >= queued_at )); then
        echo "coalesced: a rebuild started at $(date -r "$last_start" '+%H:%M:%S'), after this request was queued at $(date -r "$queued_at" '+%H:%M:%S'); it already includes this data - skipping"
        exit 0
    fi
    date +%s > "$DASH_STAMP"
    trap 'rm -f "$DASH_STAMP"' ERR
fi

# Function to check if Python package is available
check_python_package() {
    local package=$1
    if ! python -c "import $package" 2>/dev/null; then
        echo "❌ ERROR: Required Python package '$package' not found"
        echo "   Please install with: pip install $package"
        return 1
    fi
}

# Function to ensure directory exists
ensure_directory() {
    local dir=$1
    if [[ ! -d "$dir" ]]; then
        echo "📁 Creating directory: $dir"
        mkdir -p "$dir"
    fi
}

# Function to check if file exists before git add
safe_git_add() {
    local file=$1
    if [[ -e "$file" ]]; then
        git add "$file"
        echo "✅ Added $file to staging"
    else
        echo "⚠️  Warning: $file does not exist, skipping"
    fi
}

echo "🔄 Updating MOSAIC AI Cholera Data Dashboard..."
echo "================================================"

# Validate Python dependencies
echo "🔍 Checking Python dependencies..."
check_python_package "pandas" || exit 1
check_python_package "matplotlib" || exit 1
# Check for Pillow (PIL) with proper import test
python -c "from PIL import Image" 2>/dev/null || {
    echo "❌ ERROR: Pillow package not found"
    echo "   Please install with: pip install Pillow"
    exit 1
}
check_python_package "numpy" || exit 1
echo "✅ All Python dependencies available"

# Ensure required directories exist
echo "📁 Validating directory structure..."
ensure_directory "dashboard"
ensure_directory "figures/dashboard/plots"
ensure_directory "figures/dashboard/heatmaps"
ensure_directory "figures/dashboard/timelines"
ensure_directory "figures/dashboard/timeseries"
ensure_directory "py"

# Figures first. EVERY figure is rebuilt on EVERY run - this script is the only
# dashboard refresh path (the runner and heartbeat call it too), so a data update
# can never publish new embedded data next to stale figures.

# Generate coverage barplot with error handling
echo "📊 Generating coverage barplot..."
if ! python py/generate_coverage_barplot.py; then
    echo "❌ ERROR: Coverage barplot generation failed"
    exit 1
fi
echo "✅ Coverage barplot generated"

# Generate coverage heatmaps with error handling
echo ""
echo "🗺️ Generating coverage heatmaps..."
if ! python py/generate_coverage_heatmap.py; then
    echo "❌ ERROR: Coverage heatmap generation failed"
    exit 1
fi
echo "✅ Coverage heatmaps generated"

# Generate national weekly time series (Fourier disaggregation + composite plots)
echo ""
echo "📈 Building national weekly time series..."
if ! python py/build_weekly_timeseries.py; then
    echo "❌ ERROR: Weekly time series build failed"
    exit 1
fi
echo "✅ Weekly time series built"

# Province (ADM1) weekly series - built from province-or-below reported counts
# only (docs/technical/subnational-weekly-series-plan.md). After the national
# build: its reconciliation file compares against cholera_weekly_{ISO}.csv.
echo ""
echo "🗺️ Building province weekly series..."
if ! python py/build_province_weekly.py; then
    echo "❌ ERROR: Province weekly series build failed"
    exit 1
fi
if ! python py/validate_province_series.py > /dev/null; then
    python py/validate_province_series.py | grep ERROR | head -20 || true
    echo "❌ ERROR: Province series failed validation"
    exit 1
fi
if ! python py/plot_province_series.py > /dev/null; then
    echo "❌ ERROR: Province figures failed"
    exit 1
fi
echo "✅ Province weekly series built, validated and plotted (figures/province/)"

# District (ADM2) weekly series - after the province build (district templates
# fall back to province templates; reconciliation compares against provinces).
# DRC's districts are its health zones. See docs/technical/district-weekly-series-scope.md.
echo ""
echo "🗺️ Building district weekly series..."
if ! python py/build_district_weekly.py; then
    echo "❌ ERROR: District weekly series build failed"
    exit 1
fi
if ! python py/validate_district_series.py > /dev/null; then
    python py/validate_district_series.py | grep ERROR | head -20 || true
    echo "❌ ERROR: District series failed validation"
    exit 1
fi
if ! python py/plot_district_series.py > /dev/null; then
    echo "❌ ERROR: District figures failed"
    exit 1
fi
echo "✅ District weekly series built, validated and plotted (figures/district/)"

# Completion checklist, dual timeline plots (generate_dual_timeline_plots.py)
# and the embedded data blobs in dashboard.html.
echo ""
echo "📊 Updating completion status, timeline plots and embedded data..."
if ! python py/update_dashboard_data.py; then
    echo "❌ ERROR: Dashboard data update failed"
    exit 1
fi
echo "✅ Dashboard data update completed"

# Country run-status table. Must run AFTER update_dashboard_data.py, which
# rewrites the embedded CSV/JSON blobs in dashboard.html; this then re-injects
# the table between the COUNTRY-STATUS markers.
echo ""
echo "📋 Rebuilding country status table..."
if ! python py/generate_country_status_page.py; then
    echo "❌ ERROR: Country status table generation failed"
    exit 1
fi
echo "✅ Country status table updated"

# Cache-bust figure URLs. Pages serves the PNGs with max-age=14400 at fixed
# paths (the HTML gets 600), so without this browsers show the new dashboard
# with figures up to 4 h old. Must run after every figure step above.
echo ""
echo "🔖 Stamping figure URLs with current figure version..."
if ! python py/stamp_figure_versions.py; then
    echo "❌ ERROR: Figure version stamping failed"
    exit 1
fi

# Structural gate. The dashboard has been published broken twice: once
# truncated from 10 MB to 164 KB by a runaway regex, once with an unterminated
# CSS rule that swallowed the rest of the stylesheet. Both times every string in
# the page was correct and only the structure was wrong, so nothing noticed.
# Also fails if any figure URL lacks the current version stamp.
echo ""
echo "🔎 Validating dashboard structure..."
if ! python py/validate_dashboard.py; then
    echo "❌ ERROR: dashboard failed structural validation - NOT publishing"
    exit 1
fi

# Embed all data sources (AI-mined, WHO, JHU) with error handling
# TEMPORARILY DISABLED: embed_all_data.py is corrupting the dashboard structure
# echo ""
# echo "💾 Embedding all data sources into dashboard..."
# if ! python py/embed_all_data.py; then
#     echo "❌ ERROR: Data embedding failed"
#     exit 1
# fi
# echo "✅ Data embedding completed"

echo ""

# Publishing is OPT-IN.
#
# This script is the one CLAUDE.md tells every agent to run, and it used to
# commit and `git push` unconditionally - publishing to the public GitHub Pages
# dashboard as a side effect of a routine data refresh. During an unattended
# 40-country run that means dozens of automatic publications, and because the
# staged set is only dashboard/, figures/dashboard/ and cholera_weekly_*.csv, it
# would push derived outputs while the source CSVs they were built from stayed
# uncommitted - an externally visible, internally inconsistent state.
#
# Local regeneration is always safe and always runs. To publish:
#     bash update_dashboard.sh --publish
PUBLISH=0
for arg in "$@"; do
    case "$arg" in
        --publish) PUBLISH=1 ;;
    esac
done

if [[ "$PUBLISH" -ne 1 ]]; then
    echo "✅ Dashboard regenerated locally."
    echo "   Not committed or pushed. Re-run with --publish to publish to GitHub Pages."
    exit 0
fi

echo "🔄 Committing dashboard updates to GitHub..."

# Safely add dashboard files to git (only if they exist)
safe_git_add "dashboard/completion_checklist.csv"
safe_git_add "dashboard/dashboard.html"
# Regenerated above by generate_country_status_page.py. It was missing from this
# list, so the standalone page was rebuilt on every run and published only when
# someone happened to `git add -A` by hand - the live copy had drifted hours
# behind the dashboard it links to. (run_status.html is published separately, by
# the heartbeat in py/run_status.py.)
safe_git_add "dashboard/country_status.html"
# Figures are now in ./figures/dashboard/ and tracked separately
safe_git_add "figures/dashboard/"
# Stage weekly CSVs (generated per-country by build_weekly_timeseries.py)
find data -name "cholera_weekly_*.csv" -exec git add {} \; 2>/dev/null || true

# Check if there are changes to commit
if git diff --staged --quiet; then
    echo "📝 No dashboard changes to commit"
else
    # Create commit with safe single-line message
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Use safe commit message (single line with escaped content)
    COMMIT_MSG="Auto-update dashboard data - ${TIMESTAMP} - Generated with Claude Code"
    
    echo "📝 Committing changes with message: $COMMIT_MSG"
    if ! git commit -m "$COMMIT_MSG"; then
        echo "❌ ERROR: Git commit failed"
        exit 1
    fi
    echo "✅ Changes committed successfully"

    # Push to GitHub with error handling
    echo "🚀 Pushing dashboard updates to GitHub..."
    if git push; then
        echo "✅ Dashboard successfully updated on GitHub!"
        echo "🌐 Live dashboard available at: https://docs.idmod.org/ai-cholera-data-mining/"
    else
        echo "❌ ERROR: Failed to push to GitHub"
        echo "   Dashboard updated locally, but remote push failed"
        echo "   Check your git configuration and network connection"
        exit 1
    fi
fi

echo ""
echo "✅ Dashboard update complete!"
echo "📱 Open dashboard/dashboard.html to view the updated dashboard"
echo "================================================"