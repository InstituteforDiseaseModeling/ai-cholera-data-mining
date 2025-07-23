#!/usr/bin/env python3
"""
get_iso_codes.py - Extract and format ISO country codes for AI cholera data collection

This script reads the MOSAIC country reference data and generates formatted outputs
that Claude instances can easily load and understand for cholera surveillance work.

Usage:
    python py/get_iso_codes.py
    
Outputs:
    - reference/iso_codes_all.txt: All 54 African countries
    - reference/iso_codes_mosaic.txt: 40 MOSAIC framework countries  
    - reference/iso_codes_high_priority.txt: Countries prioritized for cholera work
    - reference/country_mapping.json: Complete mapping for Claude instances
"""

import pandas as pd
import json
import os
from pathlib import Path

def load_country_data():
    """Load the MOSAIC country reference data."""
    reference_dir = Path(__file__).parent.parent / "reference"
    country_file = reference_dir / "mosaic_country_codes.csv"
    
    if not country_file.exists():
        raise FileNotFoundError(f"Country reference file not found: {country_file}")
    
    df = pd.read_csv(country_file)
    print(f"Loaded {len(df)} countries from reference file")
    return df

def write_iso_list(countries, filename, description):
    """Write a simple list of ISO codes to a text file."""
    reference_dir = Path(__file__).parent.parent / "reference"
    output_file = reference_dir / filename
    
    iso_codes = sorted(countries['iso_code'].tolist())
    
    with open(output_file, 'w') as f:
        f.write(f"# {description}\n")
        f.write(f"# Generated from mosaic_country_codes.csv\n")
        f.write(f"# Total countries: {len(iso_codes)}\n\n")
        
        for iso in iso_codes:
            f.write(f"{iso}\n")
    
    print(f"Written {len(iso_codes)} ISO codes to {filename}")
    return iso_codes

def create_country_mapping(df):
    """Create comprehensive country mapping for Claude instances."""
    mapping = {
        "metadata": {
            "description": "MOSAIC Framework Country Codes for AI Cholera Data Collection",
            "total_countries": len(df),
            "mosaic_countries": len(df[df['mosaic_framework'] == True]),
            "who_afro_countries": len(df[df['who_afro'] == True]),
            "ssa_countries": len(df[df['ssa'] == True]),
            "generation_date": pd.Timestamp.now().isoformat()
        },
        "countries": {},
        "groups": {
            "all_africa": sorted(df['iso_code'].tolist()),
            "mosaic_framework": sorted(df[df['mosaic_framework'] == True]['iso_code'].tolist()),
            "who_afro": sorted(df[df['who_afro'] == True]['iso_code'].tolist()),
            "sub_saharan_africa": sorted(df[df['ssa'] == True]['iso_code'].tolist()),
            "north_africa": sorted(df[df['subregion'] == 'North Africa']['iso_code'].tolist()),
            "west_africa": sorted(df[df['subregion'] == 'West Africa']['iso_code'].tolist()),
            "east_africa": sorted(df[df['subregion'] == 'East Africa']['iso_code'].tolist()),
            "central_africa": sorted(df[df['subregion'] == 'Central Africa']['iso_code'].tolist()),
            "southern_africa": sorted(df[df['subregion'] == 'Southern Africa']['iso_code'].tolist())
        },
        "regional_breakdown": {}
    }
    
    # Add detailed country information
    for _, row in df.iterrows():
        iso = row['iso_code']
        mapping["countries"][iso] = {
            "name": row['country_name'],
            "region": row['region'],
            "subregion": row['subregion'],
            "mosaic_framework": bool(row['mosaic_framework']),
            "who_afro": bool(row['who_afro']),
            "ssa": bool(row['ssa']),
            "ai_cholera_coverage": bool(row['ai_cholera_coverage'])
        }
    
    # Add regional breakdown with counts
    for subregion in df['subregion'].unique():
        region_countries = df[df['subregion'] == subregion]
        mapping["regional_breakdown"][subregion] = {
            "count": len(region_countries),
            "countries": sorted(region_countries['iso_code'].tolist()),
            "mosaic_countries": len(region_countries[region_countries['mosaic_framework'] == True])
        }
    
    return mapping

def write_claude_instructions():
    """Write instructions for Claude instances on how to use the ISO code files."""
    reference_dir = Path(__file__).parent.parent / "reference"
    instructions_file = reference_dir / "iso_codes_usage.md"
    
    content = """# ISO Country Codes for AI Cholera Data Collection

## Overview
This directory contains ISO country codes and mapping data for the MOSAIC cholera surveillance framework.

## Files Generated
- `iso_codes_all.txt`: All 54 African countries (complete coverage)
- `iso_codes_mosaic.txt`: 40 MOSAIC framework countries (core modeling countries)
- `iso_codes_high_priority.txt`: High-priority countries for cholera data enhancement
- `country_mapping.json`: Complete country metadata and groupings

## Usage for Claude Instances

### Quick Reference
```python
import json

# Load complete country mapping
with open('./reference/country_mapping.json', 'r') as f:
    countries = json.load(f)

# Get MOSAIC framework countries
mosaic_countries = countries['groups']['mosaic_framework']

# Get country details
country_info = countries['countries']['AGO']  # Angola example
print(f"{country_info['name']} is in {country_info['subregion']}")
```

### Available Groupings
- `all_africa`: All 54 African countries
- `mosaic_framework`: 40 countries in MOSAIC modeling framework
- `who_afro`: 47 WHO African Regional Office countries
- `sub_saharan_africa`: 48 Sub-Saharan African countries
- `north_africa`, `west_africa`, `east_africa`, `central_africa`, `southern_africa`: Regional subdivisions

### Country Selection Examples

**High Cholera Burden Countries (Priority):**
- Nigeria (NGA), Democratic Republic of Congo (COD), Somalia (SOM), Ethiopia (ETH)
- Zimbabwe (ZWE), Zambia (ZMB), Kenya (KEN), Tanzania (TZA)

**MOSAIC Framework Countries:**
All 40 countries with `mosaic_framework: true` in the mapping

**For Agent Workflows:**
Use the appropriate grouping based on the analysis scope:
- Full Africa analysis: `all_africa`
- MOSAIC modeling work: `mosaic_framework` 
- WHO surveillance focus: `who_afro`
- Development context: `sub_saharan_africa`

## Data Integrity
All ISO codes follow ISO 3166-1 alpha-3 standard and match the authoritative MOSAIC-pkg framework definitions.
"""
    
    with open(instructions_file, 'w') as f:
        f.write(content)
    
    print(f"Written usage instructions to iso_codes_usage.md")

def main():
    """Main execution function."""
    print("Loading MOSAIC country reference data...")
    df = load_country_data()
    
    # Create reference directory if it doesn't exist
    reference_dir = Path(__file__).parent.parent / "reference"
    reference_dir.mkdir(exist_ok=True)
    
    # Generate ISO code lists
    print("\nGenerating ISO code lists...")
    
    # All African countries
    all_countries = write_iso_list(
        df, 
        "iso_codes_all.txt", 
        "All 54 African Countries - Complete AI Cholera Data Coverage"
    )
    
    # MOSAIC framework countries
    mosaic_countries = write_iso_list(
        df[df['mosaic_framework'] == True],
        "iso_codes_mosaic.txt",
        "40 MOSAIC Framework Countries - Core Modeling Countries"
    )
    
    # High priority cholera countries (WHO AFRO + high burden)
    high_priority = df[df['who_afro'] == True]
    high_priority_countries = write_iso_list(
        high_priority,
        "iso_codes_high_priority.txt",
        "47 WHO AFRO Countries - High Priority for Cholera Surveillance"
    )
    
    # Create comprehensive mapping
    print("\nGenerating comprehensive country mapping...")
    mapping = create_country_mapping(df)
    
    mapping_file = reference_dir / "country_mapping.json"
    with open(mapping_file, 'w') as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
    
    print(f"Written comprehensive mapping to country_mapping.json")
    
    # Create usage instructions
    print("\nGenerating usage instructions...")
    write_claude_instructions()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total African countries: {len(all_countries)}")
    print(f"MOSAIC framework countries: {len(mosaic_countries)}")
    print(f"WHO AFRO countries: {len(high_priority_countries)}")
    print("\nRegional breakdown:")
    
    for subregion in df['subregion'].unique():
        count = len(df[df['subregion'] == subregion])
        mosaic_count = len(df[(df['subregion'] == subregion) & (df['mosaic_framework'] == True)])
        print(f"  {subregion}: {count} countries ({mosaic_count} in MOSAIC)")
    
    print(f"\nFiles generated in ./reference/:")
    print("  - iso_codes_all.txt")
    print("  - iso_codes_mosaic.txt") 
    print("  - iso_codes_high_priority.txt")
    print("  - country_mapping.json")
    print("  - iso_codes_usage.md")
    
    print("\nReady for AI cholera data collection workflows!")

if __name__ == "__main__":
    main()