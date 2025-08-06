#!/usr/bin/env python3
"""
Generate Country-Specific Workflow Prompts

This script takes the template_prompt.txt file and generates
country-specific prompt_{ISO}.txt files with simple Task tool invocations
for each country in the MOSAIC framework.

The orchestrator subagent handles all the complex workflow logic internally,
so these prompt files are just simple one-line commands.

Usage:
    python generate_country_prompt.py [ISO_CODE]
    python generate_country_prompt.py ETH
    python generate_country_prompt.py --all  # Generate for all countries
"""

import json
import os
import sys
import pandas as pd
from pathlib import Path

def load_country_mapping():
    """Load country mapping data"""
    try:
        with open('reference/country_mapping.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: country_mapping.json not found, using defaults")
        return {}

def load_gap_analysis():
    """Load gap analysis data"""
    try:
        return pd.read_csv('reference/agent_quick_reference.csv')
    except FileNotFoundError:
        print("Warning: agent_quick_reference.csv not found, using defaults")
        return pd.DataFrame()

def get_country_parameters(iso_code, country_mapping, gap_analysis):
    """Generate country-specific parameters"""
    
    # Default country data - replace these with actual lookups
    country_data = {
        'ETH': {
            'COUNTRY_NAME': 'Ethiopia',
            'MAJOR_CITIES': ['Addis Ababa', 'Dire Dawa', 'Mek\'ele', 'Gondar', 'Hawassa'],
            'NEIGHBORING_COUNTRIES': ['Sudan', 'South Sudan', 'Kenya', 'Somalia', 'Djibouti', 'Eritrea'],
            'TOTAL_PROVINCES': 11,
            'PRIMARY_LANGUAGE': 'English',
            'SECONDARY_LANGUAGES': ['Amharic'],
            'REGIONAL_CLUSTER': 'East Africa',
            'COUNTRY_HEALTH_MINISTRY': 'moh.gov.et'
        },
        'AGO': {
            'COUNTRY_NAME': 'Angola',
            'MAJOR_CITIES': ['Luanda', 'Huambo', 'Lobito', 'Benguela', 'Kuito'],
            'NEIGHBORING_COUNTRIES': ['Democratic Republic of Congo', 'Zambia', 'Namibia'],
            'TOTAL_PROVINCES': 18,
            'PRIMARY_LANGUAGE': 'Portuguese',
            'SECONDARY_LANGUAGES': ['English'],
            'REGIONAL_CLUSTER': 'Central Africa',
            'COUNTRY_HEALTH_MINISTRY': 'minsa.gov.ao'
        },
        'KEN': {
            'COUNTRY_NAME': 'Kenya',
            'MAJOR_CITIES': ['Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Eldoret'],
            'NEIGHBORING_COUNTRIES': ['Tanzania', 'Uganda', 'South Sudan', 'Ethiopia', 'Somalia'],
            'TOTAL_PROVINCES': 47,
            'PRIMARY_LANGUAGE': 'English',
            'SECONDARY_LANGUAGES': ['Swahili'],
            'REGIONAL_CLUSTER': 'East Africa',
            'COUNTRY_HEALTH_MINISTRY': 'health.go.ke'
        }
    }
    
    # Get base country data
    base_data = country_data.get(iso_code, {
        'COUNTRY_NAME': f'Country_{iso_code}',
        'MAJOR_CITIES': [f'City1_{iso_code}', f'City2_{iso_code}'],
        'NEIGHBORING_COUNTRIES': ['Country1', 'Country2'],
        'TOTAL_PROVINCES': 10,
        'PRIMARY_LANGUAGE': 'English',
        'SECONDARY_LANGUAGES': ['Local'],
        'REGIONAL_CLUSTER': 'Africa',
        'COUNTRY_HEALTH_MINISTRY': f'health.gov.{iso_code.lower()}'
    })
    
    # Get gap analysis data if available
    gap_data = {}
    if not gap_analysis.empty and iso_code in gap_analysis['iso_code'].values:
        country_gap = gap_analysis[gap_analysis['iso_code'] == iso_code].iloc[0]
        gap_data = {
            'BASELINE_COVERAGE_PCT': f"{country_gap.get('coverage_pct', 50.0):.1f}",
            'SEARCH_PRIORITY': country_gap.get('search_priority', 'MEDIUM'),
            'PRIORITY_PERIOD_DESCRIPTION': country_gap.get('priority_periods', '2019-2022 period'),
            'MISSING_RECENT_YEARS': country_gap.get('missing_recent_years', '2019,2020,2021,2022')
        }
    else:
        gap_data = {
            'BASELINE_COVERAGE_PCT': '50.0',
            'SEARCH_PRIORITY': 'MEDIUM',
            'PRIORITY_PERIOD_DESCRIPTION': '2019-2022 period',
            'MISSING_RECENT_YEARS': '2019,2020,2021,2022'
        }
    
    # Process gap data
    missing_years_str = str(gap_data['MISSING_RECENT_YEARS']).replace('nan', '2019,2020,2021,2022')
    missing_years = missing_years_str.split(',')
    priority_gap_years = [year.strip() for year in missing_years if year.strip() and year.strip() != 'nan'][:4]
    if not priority_gap_years:
        priority_gap_years = ['2019', '2020', '2021', '2022']
    
    # Calculate search allocation based on priority
    search_priority = gap_data['SEARCH_PRIORITY']
    if search_priority == 'HIGH':
        gap_allocation, historical_allocation = 80, 20
    elif search_priority == 'MEDIUM':
        gap_allocation, historical_allocation = 60, 40
    else:  # LOW
        gap_allocation, historical_allocation = 40, 60
    
    # Build final parameter dictionary
    parameters = {
        'ISO_CODE': iso_code,
        **base_data,
        **gap_data,
        'PRIORITY_GAP_YEARS': ', '.join(priority_gap_years),
        'PRIORITY_YEAR_1': priority_gap_years[0] if priority_gap_years else '2019',
        'PRIORITY_YEAR_2': priority_gap_years[1] if len(priority_gap_years) > 1 else '2020',
        'PRIORITY_YEAR_3': priority_gap_years[2] if len(priority_gap_years) > 2 else '2021',
        'PRIORITY_YEAR_4': priority_gap_years[3] if len(priority_gap_years) > 3 else '2022',
        'MAJOR_CITY_1': base_data['MAJOR_CITIES'][0] if base_data['MAJOR_CITIES'] else 'MajorCity1',
        'MAJOR_CITY_2': base_data['MAJOR_CITIES'][1] if len(base_data['MAJOR_CITIES']) > 1 else 'MajorCity2',
        'NEIGHBORING_COUNTRY_1': base_data['NEIGHBORING_COUNTRIES'][0] if base_data['NEIGHBORING_COUNTRIES'] else 'Neighbor1',
        'NEIGHBORING_COUNTRY_2': base_data['NEIGHBORING_COUNTRIES'][1] if len(base_data['NEIGHBORING_COUNTRIES']) > 1 else 'Neighbor2',
        'PROVINCE_EXAMPLE': base_data['MAJOR_CITIES'][0] if base_data['MAJOR_CITIES'] else 'Province1',
        'MAJOR_PROVINCE': base_data['MAJOR_CITIES'][0] if base_data['MAJOR_CITIES'] else 'Province1',
        'GAP_SEARCH_ALLOCATION': str(gap_allocation),
        'HISTORICAL_SEARCH_ALLOCATION': str(historical_allocation),
        # Convert lists to comma-separated strings for template
        'MAJOR_CITIES': ', '.join(base_data['MAJOR_CITIES']),
        'NEIGHBORING_COUNTRIES': ', '.join(base_data['NEIGHBORING_COUNTRIES']),
        'SECONDARY_LANGUAGES': ', '.join(base_data['SECONDARY_LANGUAGES'])
    }
    
    return parameters

def substitute_parameters(template_content, parameters):
    """Substitute all parameters in template content"""
    content = template_content
    
    for key, value in parameters.items():
        placeholder = f"{{{key}}}"
        content = content.replace(placeholder, str(value))
    
    return content

def generate_prompt_file(iso_code, output_dir="data"):
    """Generate country-specific prompt file"""
    
    # Load data for country name
    country_mapping = load_country_mapping()
    gap_analysis = load_gap_analysis()
    
    # Get parameters (mainly for country name)
    parameters = get_country_parameters(iso_code, country_mapping, gap_analysis)
    
    # Load template
    try:
        with open('templates/template_prompt.txt', 'r') as f:
            template_content = f.read()
    except FileNotFoundError:
        print("Error: template_prompt.txt not found")
        return False
    
    # Substitute parameters - just need country name and ISO code
    prompt_content = template_content.replace('{COUNTRY_NAME}', parameters['COUNTRY_NAME'])
    prompt_content = prompt_content.replace('{ISO_CODE}', iso_code)
    
    # Create output directory
    country_dir = Path(output_dir) / iso_code
    country_dir.mkdir(parents=True, exist_ok=True)
    
    # Write output file
    output_file = country_dir / f"prompt_{iso_code}.txt"
    with open(output_file, 'w') as f:
        f.write(prompt_content)
    
    print(f"Generated: {output_file}")
    print(f"Country: {parameters['COUNTRY_NAME']} ({iso_code})")
    print(f"Prompt: {prompt_content}")
    print()
    
    return True

def get_mosaic_countries():
    """Get list of MOSAIC framework countries"""
    # These are the 40 MOSAIC framework countries
    return [
        'AGO', 'BDI', 'BEN', 'BFA', 'BWA', 'CAF', 'CIV', 'CMR', 'COD', 'COG',
        'ERI', 'ETH', 'GAB', 'GHA', 'GIN', 'GMB', 'GNB', 'GNQ', 'KEN', 'LBR',
        'MLI', 'MOZ', 'MRT', 'MWI', 'NAM', 'NER', 'NGA', 'RWA', 'SEN', 'SLE',
        'SOM', 'SSD', 'SWZ', 'TCD', 'TGO', 'TZA', 'UGA', 'ZAF', 'ZMB', 'ZWE'
    ]

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python generate_country_prompt.py [ISO_CODE|--all]")
        print("Examples:")
        print("  python generate_country_prompt.py ETH")
        print("  python generate_country_prompt.py --all")
        return
    
    if sys.argv[1] == '--all':
        # Generate for all MOSAIC countries
        countries = get_mosaic_countries()
        print(f"Generating prompt files for {len(countries)} MOSAIC countries...")
        print()
        
        success_count = 0
        for iso_code in countries:
            if generate_prompt_file(iso_code):
                success_count += 1
        
        print(f"Successfully generated {success_count}/{len(countries)} prompt files")
        
    else:
        # Generate for specific country
        iso_code = sys.argv[1].upper()
        if iso_code in get_mosaic_countries():
            generate_prompt_file(iso_code)
        else:
            print(f"Error: {iso_code} is not a MOSAIC framework country")
            print("MOSAIC countries:", ', '.join(get_mosaic_countries()))

if __name__ == '__main__':
    main()