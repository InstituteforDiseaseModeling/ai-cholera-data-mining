#!/bin/bash

# MOSAIC AI Cholera Data Collection - Dashboard Update Script
# 
# This script provides a simple command for agents to update all dashboard data:
# - Completion checklist (based on file analysis)
# - 3-source timeline coverage plots (with synchronized date ranges)
# - Timeline week counts data (embedded in dashboard)
# - CSV data embedding (metadata.csv and cholera_data.csv files)
# - Dashboard HTML with all embedded data
#
# Usage: bash update_dashboard.sh
# or: chmod +x update_dashboard.sh && ./update_dashboard.sh

echo "🔄 Updating MOSAIC AI Cholera Data Dashboard..."
echo "================================================"

# Run the unified dashboard data update script
echo "📊 Updating completion status and timeline data..."
python py/update_dashboard_data.py

# Embed CSV data for completed countries
echo ""
echo "💾 Embedding CSV data into dashboard..."
python py/embed_csv_data.py

echo ""
echo "✅ Dashboard update complete!"
echo "📱 Open dashboard/dashboard.html to view the updated dashboard"
echo "================================================"