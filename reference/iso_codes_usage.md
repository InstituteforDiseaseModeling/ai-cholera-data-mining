# ISO Country Codes for AI Cholera Data Collection

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
