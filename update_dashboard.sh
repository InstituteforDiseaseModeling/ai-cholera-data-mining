#!/bin/bash

# MOSAIC AI Cholera Data Collection - Dashboard Update Script
# 
# This script provides a simple command for agents to update all dashboard data:
# - Completion checklist (based on file analysis)
# - 3-source timeline coverage plots (with synchronized date ranges)
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
check_python_package "PIL" || exit 1
check_python_package "numpy" || exit 1
echo "✅ All Python dependencies available"

# Ensure required directories exist
echo "📁 Validating directory structure..."
ensure_directory "dashboard"
ensure_directory "dashboard/timeline_plots"
ensure_directory "dashboard/heatmaps"
ensure_directory "py"

# Run the unified dashboard data update script with error handling
echo "📊 Updating completion status and timeline data..."
if ! python py/update_dashboard_data.py; then
    echo "❌ ERROR: Dashboard data update failed"
    exit 1
fi
echo "✅ Dashboard data update completed"

# Generate coverage heatmaps with error handling
echo ""
echo "🗺️ Generating coverage heatmaps..."
if ! python py/generate_coverage_heatmap.py; then
    echo "❌ ERROR: Coverage heatmap generation failed"
    exit 1
fi
echo "✅ Coverage heatmaps generated"

# Embed all data sources (AI-mined, WHO, JHU) with error handling
echo ""
echo "💾 Embedding all data sources into dashboard..."
if ! python py/embed_all_data.py; then
    echo "❌ ERROR: Data embedding failed"
    exit 1
fi
echo "✅ Data embedding completed"

echo ""
echo "🔄 Committing dashboard updates to GitHub..."

# Safely add dashboard files to git (only if they exist)
safe_git_add "dashboard/completion_checklist.csv"
safe_git_add "dashboard/timeline_week_counts.csv"
safe_git_add "dashboard/timeline_plots/"
safe_git_add "dashboard/heatmaps/"
safe_git_add "dashboard/dashboard.html"

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
        echo "🌐 Live dashboard available at: https://InstituteforDiseaseModeling.github.io/ai-cholera-data-mining/"
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