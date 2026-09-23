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
#
# Usage: bash update_dashboard.sh
# or: chmod +x update_dashboard.sh && ./update_dashboard.sh

# Enable strict error handling
set -euo pipefail

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

# Run the unified dashboard data update script with error handling
echo "📊 Updating completion status and timeline data..."
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

# Structural gate. The dashboard has been published broken twice: once
# truncated from 10 MB to 164 KB by a runaway regex, once with an unterminated
# CSS rule that swallowed the rest of the stylesheet. Both times every string in
# the page was correct and only the structure was wrong, so nothing noticed.
echo ""
echo "🔎 Validating dashboard structure..."
if ! python py/validate_dashboard.py; then
    echo "❌ ERROR: dashboard failed structural validation - NOT publishing"
    exit 1
fi

# Generate coverage barplot with error handling
echo ""
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