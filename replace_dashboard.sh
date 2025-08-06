#!/bin/bash

# Script to replace dashboard.html with dashboard_test.html while preserving embedded data

echo "Starting dashboard replacement process..."

# 1. Backup current dashboard.html
echo "Creating backup of current dashboard.html..."
cp dashboard/dashboard.html dashboard/dashboard_backup_$(date +%Y%m%d_%H%M%S).html

# 2. Extract embedded data from dashboard.html
echo "Extracting embedded data from dashboard.html..."

# Extract countryData array (lines approximately 1985-2548)
sed -n '1985,2548p' dashboard/dashboard.html > temp_countryData.txt

# Extract embeddedMetadata object (lines approximately 2549-2589)
sed -n '2549,2589p' dashboard/dashboard.html > temp_embeddedMetadata.txt

# Extract embeddedCholeraData object (lines approximately 2590-2630)
sed -n '2590,2630p' dashboard/dashboard.html > temp_embeddedCholeraData.txt

# 3. Replace the sample data in dashboard_test.html with real data
echo "Updating dashboard_test.html with real embedded data..."

# First, copy dashboard_test.html to a working file
cp dashboard/dashboard_test.html dashboard/dashboard_new.html

# Note: Manual step needed here to replace the sample data with real data
# This is complex to do automatically due to the structure differences

echo "IMPORTANT: Manual steps required:"
echo "1. Open dashboard/dashboard_new.html"
echo "2. Replace the sample countryData array with content from temp_countryData.txt"
echo "3. Replace the sample embeddedMetadata object with content from temp_embeddedMetadata.txt"
echo "4. Add the embeddedCholeraData object from temp_embeddedCholeraData.txt"
echo "5. Save the file"
echo ""
echo "After manual updates, run:"
echo "  mv dashboard/dashboard_new.html dashboard/dashboard.html"
echo ""
echo "Temporary files created:"
echo "  - temp_countryData.txt"
echo "  - temp_embeddedMetadata.txt" 
echo "  - temp_embeddedCholeraData.txt"
echo "  - dashboard/dashboard_backup_*.html (backup)"