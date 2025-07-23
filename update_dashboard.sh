#!/bin/bash

# MOSAIC AI Cholera Data Collection - Dashboard Update Script
# 
# This script provides a simple command for agents to update all dashboard data:
# - Completion checklist (based on file analysis)
# - 3-source timeline coverage plots (with synchronized date ranges)
# - Timeline week counts data (embedded in dashboard)
# - All data source embedding (AI-mined, WHO, and JHU data)
# - Dashboard HTML with all embedded data
#
# Usage: bash update_dashboard.sh
# or: chmod +x update_dashboard.sh && ./update_dashboard.sh

echo "🔄 Updating MOSAIC AI Cholera Data Dashboard..."
echo "================================================"

# Run the unified dashboard data update script
echo "📊 Updating completion status and timeline data..."
python py/update_dashboard_data.py

# Embed all data sources (AI-mined, WHO, JHU)
echo ""
echo "💾 Embedding all data sources into dashboard..."
python py/embed_all_data.py

echo ""
echo "🔄 Committing dashboard updates to GitHub..."

# Add dashboard files to git
git add dashboard/completion_checklist.csv
git add dashboard/timeline_week_counts.csv
git add dashboard/timeline_plots/
git add dashboard/dashboard.html

# Check if there are changes to commit
if git diff --staged --quiet; then
    echo "📝 No dashboard changes to commit"
else
    # Create commit with timestamp
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    git commit -m "Auto-update dashboard data - $TIMESTAMP

Dashboard updated with latest agent progress:
- Completion status refreshed
- Timeline plots regenerated  
- Data sources embedded
- Coverage statistics updated

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

    # Push to GitHub
    echo "🚀 Pushing dashboard updates to GitHub..."
    if git push; then
        echo "✅ Dashboard successfully updated on GitHub!"
        echo "🌐 Live dashboard available at: https://InstituteforDiseaseModeling.github.io/ai-cholera-data-mining/"
    else
        echo "⚠️  Failed to push to GitHub - dashboard updated locally only"
    fi
fi

echo ""
echo "✅ Dashboard update complete!"
echo "📱 Open dashboard/dashboard.html to view the updated dashboard"
echo "================================================"