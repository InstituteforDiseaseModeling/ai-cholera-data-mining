#!/bin/bash

# MOSAIC AI Cholera Data Collection - Setup Script
# Initializes the complete search pipeline for all 40 MOSAIC framework countries

set -e  # Exit on any error

echo "================================================================================"
echo "MOSAIC AI Cholera Data Collection - Pipeline Setup"
echo "================================================================================"
echo "Initializing search pipeline for 40 MOSAIC framework countries..."
echo ""

# Check if we're in the right directory
if [ ! -f "CLAUDE.md" ]; then
    echo "❌ ERROR: Must run from ai-cholera-data-mining directory"
    echo "Please cd to the directory containing CLAUDE.md"
    exit 1
fi

# Check Python availability
if ! command -v python &> /dev/null; then
    echo "❌ ERROR: Python not found. Please install Python 3.x"
    exit 1
fi

echo "🔍 Checking dependencies..."

# Check for required Python packages
python -c "import pandas, numpy, pathlib, json" 2>/dev/null || {
    echo "❌ ERROR: Missing required Python packages"
    echo "Please install: pip install pandas numpy"
    exit 1
}

# Check for required input files
SURVEILLANCE_DATA="../MOSAIC-data/processed/cholera/weekly/cholera_surveillance_weekly_combined.csv"
if [ ! -f "$SURVEILLANCE_DATA" ]; then
    echo "⚠️  WARNING: Surveillance data file not found at:"
    echo "   $SURVEILLANCE_DATA"
    echo ""
    echo "This file is required for gap analysis. Options:"
    echo "1. Ensure MOSAIC-data repository is at the same level as ai-cholera-data-mining"
    echo "2. Run MOSAIC-pkg processing to generate the surveillance data"
    echo "3. Continue setup without gap analysis (agents will use existing reference files)"
    echo ""
    read -p "Continue setup anyway? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    SKIP_GAP_ANALYSIS=true
fi

echo "✅ Dependencies check complete"
echo ""

# Step 1: Generate ISO codes and country mappings
echo "🗺️  Step 1: Generating country codes and mappings..."
python py/get_iso_codes.py || {
    echo "❌ Country code generation failed"
    exit 1
}
echo "   ✅ Generated: ./reference/iso_codes_mosaic.txt"
echo "   ✅ Generated: ./reference/country_mapping.json"
echo "   ✅ Generated: ./reference/iso_codes_usage.md"
echo ""

# Step 2: JHU Database Integration (NEW)
echo "🏥 Step 2: Integrating JHU cholera database as baseline..."
JHU_DATA_PATH="../jhu_cholera_data/data"
if [ ! -d "$JHU_DATA_PATH" ]; then
    echo "⚠️  WARNING: JHU cholera data not found at:"
    echo "   $JHU_DATA_PATH"
    echo ""
    echo "This data provides the baseline for AI agent searches. Options:"
    echo "1. Ensure jhu_cholera_data repository is available"
    echo "2. Continue setup without JHU baseline (agents start from empty datasets)"
    echo ""
    read -p "Continue setup without JHU baseline? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    SKIP_JHU_INTEGRATION=true
fi

if [ "$SKIP_JHU_INTEGRATION" != true ]; then
    echo "   📁 Checking for existing AI-enhanced results..."
    python py/convert_jhu_to_workflow.py || {
        echo "❌ JHU integration failed. Check JHU data availability and format."
        exit 1
    }
    echo "   ✅ JHU baseline integration complete"
    echo "   ✅ Created cholera_data_jhu.csv and metadata_jhu.csv files"
    echo "   ✅ Applied appropriate confidence weighting for JHU sources"
else
    echo "   ⚠️  Skipping JHU integration - agents will start with empty datasets"
fi
echo ""

# Step 3: WHO Dashboard Integration (NEW)
echo "🏥 Step 3: Integrating WHO dashboard surveillance data..."
WHO_DATA_PATH="../ees-cholera-mapping/data/cholera/who/awd/cholera_country_weekly.csv"
if [ ! -f "$WHO_DATA_PATH" ]; then
    echo "⚠️  WARNING: WHO dashboard data not found at:"
    echo "   $WHO_DATA_PATH"
    echo ""
    echo "This data provides recent surveillance coverage (2023-2025). Options:"
    echo "1. Ensure ees-cholera-mapping repository is available"
    echo "2. Continue setup without WHO dashboard data"
    echo ""
    read -p "Continue setup without WHO data? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    SKIP_WHO_INTEGRATION=true
fi

if [ "$SKIP_WHO_INTEGRATION" != true ]; then
    python py/convert_who_to_workflow.py || {
        echo "❌ WHO integration failed. Check WHO data availability and format."
        exit 1
    }
    echo "   ✅ WHO dashboard integration complete"
    echo "   ✅ Created cholera_data_who.csv and metadata_who.csv files"
    echo "   ✅ Enhanced recent surveillance coverage (2023-2025)"
else
    echo "   ⚠️  Skipping WHO integration - missing recent surveillance data"
fi
echo ""

# Step 4: Combine all data sources
echo "🔄 Step 4: Combining all data sources into integrated baseline..."
python py/combine_all_sources.py || {
    echo "❌ Data source combination failed"
    exit 1
}
echo "   ✅ Combined JHU, WHO, and AI sources into cholera_data.csv"
echo "   ✅ Created unified metadata.csv with dual-reference indexing"
echo ""

# Step 5: Generate integrated baseline gap analysis
echo "📊 Step 5: Generating integrated baseline gap analysis..."
if [ "$SKIP_GAP_ANALYSIS" = true ]; then
    echo "   ⚠️  Skipping gap analysis (surveillance data not available)"
    echo "   Agents will use existing reference files if available"
else
    python py/analyze_integrated_coverage_gaps.py || {
        echo "❌ Integrated gap analysis failed. Check that baseline data exists and is properly formatted."
        exit 1
    }
    echo "   ✅ Generated: ./reference/agent_quick_reference.csv"
    echo "   ✅ Generated: ./reference/observed_time_periods.csv"  
    echo "   ✅ Generated: ./reference/priority_data_gaps.csv"
fi
echo ""

# Step 6: Set up country directories and workflows
echo "📁 Step 6: Setting up country directories and workflows..."
python py/configure_countries.py || {
    echo "❌ Country setup failed"
    exit 1
}
echo "   ✅ Created 40 country directories"
echo "   ✅ Generated 40 search protocol files"
echo "   ✅ Generated 40 agentic workflow files"  
echo "   ✅ Generated comprehensive country information key"
echo "   ✅ Generated execution checklist"
echo ""

# Verification
echo "🔍 Verifying setup..."

EXPECTED_DIRS=$(find data -maxdepth 1 -type d | grep -E '/[A-Z]{3}$' | wc -l)
EXPECTED_PROTOCOLS=$(find data -name "search_protocol_*.txt" | wc -l)  
EXPECTED_WORKFLOWS=$(find data -name "agentic_workflow_*.txt" | wc -l)

if [ "$EXPECTED_DIRS" -eq 40 ] && [ "$EXPECTED_PROTOCOLS" -eq 40 ] && [ "$EXPECTED_WORKFLOWS" -eq 40 ]; then
    echo "✅ Verification passed: All country files created successfully"
else
    echo "⚠️  Verification warning: Expected 40 directories, protocols, and workflows"
    echo "   Found: $EXPECTED_DIRS directories, $EXPECTED_PROTOCOLS protocols, $EXPECTED_WORKFLOWS workflows"
fi

# Check reference files
if [ -f "reference/country_info_key.json" ] && [ -f "reference/priority_sources.txt" ]; then
    echo "✅ Reference files properly organized"
else
    echo "⚠️  Some reference files may be missing"
fi

echo ""
echo "================================================================================"
echo "🎉 MOSAIC AI Cholera Data Collection - Setup Complete!"
echo "================================================================================"
echo ""
echo "📋 Setup Summary:"
echo "   • 40 MOSAIC framework countries configured"
echo "   • JHU cholera database integrated as baseline$([ "$SKIP_JHU_INTEGRATION" = true ] && echo " (skipped)" || echo "")"
echo "   • WHO dashboard data integrated$([ "$SKIP_WHO_INTEGRATION" = true ] && echo " (skipped)" || echo " (2023-2025 coverage)")"
echo "   • All data sources combined into integrated baseline files"
echo "   • Gap analysis data prepared$([ "$SKIP_GAP_ANALYSIS" = true ] && echo " (skipped)" || echo "")"
echo "   • Country-specific search protocols generated"
echo "   • 6-agent workflow files created"
echo "   • Reference files organized in ./reference/"
echo ""
echo "🚀 Ready to Execute:"
echo "   1. Review CLAUDE.md for complete methodology"
echo "   2. Use data/{ISO_CODE}/search_protocol_{ISO_CODE}.txt for individual countries"  
echo "   3. Use data/{ISO_CODE}/agentic_workflow_{ISO_CODE}.txt for full 6-agent pipeline"
echo "   4. Track progress with country_checklist.txt"
echo ""
echo "💡 Next Steps:"
echo "   • Countries now have dual-source baseline data (JHU + WHO dashboard)"
echo "   • Select a country to process (suggest starting with HIGH priority countries)" 
echo "   • Follow the 6-agent workflow to fill remaining gaps beyond baseline coverage"
echo "   • Use reference/agent_quick_reference.csv to identify post-integration data gaps"
echo "   • Run dashboard updates to visualize comprehensive baseline coverage"
echo ""
echo "✨ Pipeline ready for AI-enhanced cholera surveillance data collection!"
echo "================================================================================"