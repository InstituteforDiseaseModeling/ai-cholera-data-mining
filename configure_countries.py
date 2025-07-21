#!/usr/bin/env python3
"""
MOSAIC AI Cholera Data Collection - Country Setup Script v2.0
Creates directories and customized prompts for 8-phase search protocol
Supports all 54 African countries with enhanced dual-reference system
"""

import os
import json
import shutil
from pathlib import Path

# Country information database - Complete 54 African countries
AFRICAN_COUNTRIES = {
    # North Africa
    "DZA": {
        "name": "Algeria",
        "linguistic_group": "Arabic/Francophone", 
        "primary_language": "Arabic",
        "secondary_languages": "French, English",
        "system_type": "Unitary",
        "regional_cluster": "North Africa",
        "neighbors": ["Libya", "Mali", "Mauritania", "Morocco", "Niger", "Tunisia"],
        "conflict_status": "Stable",
        "surveillance_capacity": "Moderate",
        "total_provinces": "58"
    },
    "EGY": {
        "name": "Egypt",
        "linguistic_group": "Arabic",
        "primary_language": "Arabic", 
        "secondary_languages": "English, French",
        "system_type": "Unitary",
        "regional_cluster": "North Africa",
        "neighbors": ["Libya", "Sudan"],
        "conflict_status": "Stable",
        "surveillance_capacity": "Moderate"
    },
    "LBY": {
        "name": "Libya",
        "linguistic_group": "Arabic",
        "primary_language": "Arabic",
        "secondary_languages": "English, Italian", 
        "system_type": "Post-conflict",
        "regional_cluster": "North Africa",
        "neighbors": ["Algeria", "Chad", "Egypt", "Niger", "Sudan", "Tunisia"],
        "conflict_status": "Post-conflict",
        "surveillance_capacity": "Weak"
    },
    "MAR": {
        "name": "Morocco", 
        "linguistic_group": "Arabic/Francophone",
        "primary_language": "Arabic",
        "secondary_languages": "French, English",
        "system_type": "Unitary",
        "regional_cluster": "North Africa", 
        "neighbors": ["Algeria"],
        "conflict_status": "Stable",
        "surveillance_capacity": "Strong"
    },
    "SDN": {
        "name": "Sudan",
        "linguistic_group": "Arabic",
        "primary_language": "Arabic",
        "secondary_languages": "English, Local languages",
        "system_type": "Federal",
        "regional_cluster": "North Africa/East Africa",
        "neighbors": ["CAR", "Chad", "Egypt", "Eritrea", "Ethiopia", "Libya", "South Sudan"],
        "conflict_status": "Post-conflict", 
        "surveillance_capacity": "Weak"
    },
    "TUN": {
        "name": "Tunisia",
        "linguistic_group": "Arabic/Francophone",
        "primary_language": "Arabic",
        "secondary_languages": "French, English", 
        "system_type": "Unitary",
        "regional_cluster": "North Africa",
        "neighbors": ["Algeria", "Libya"],
        "conflict_status": "Stable",
        "surveillance_capacity": "Moderate"
    },
    
    # West Africa
    "BEN": {
        "name": "Benin",
        "linguistic_group": "Francophone",
        "primary_language": "French",
        "secondary_languages": "Local languages", 
        "system_type": "Unitary",
        "regional_cluster": "West Africa",
        "neighbors": ["Burkina Faso", "Niger", "Nigeria", "Togo"],
        "conflict_status": "Stable",
        "surveillance_capacity": "Moderate"
    },
    "BFA": {
        "name": "Burkina Faso",
        "linguistic_group": "Francophone",
        "primary_language": "French", 
        "secondary_languages": "Local languages",
        "system_type": "Unitary",
        "regional_cluster": "West Africa",
        "neighbors": ["Benin", "Côte d'Ivoire", "Ghana", "Mali", "Niger", "Togo"],
        "conflict_status": "Post-conflict",
        "surveillance_capacity": "Weak"
    },
    "CPV": {
        "name": "Cape Verde",
        "linguistic_group": "Lusophone",
        "primary_language": "Portuguese",
        "secondary_languages": "Cape Verdean Creole",
        "system_type": "Unitary", 
        "regional_cluster": "West Africa/Island",
        "neighbors": [],
        "conflict_status": "Stable",
        "surveillance_capacity": "Moderate"
    },
    "CIV": {
        "name": "Côte d'Ivoire",
        "linguistic_group": "Francophone",
        "primary_language": "French",
        "secondary_languages": "Local languages",
        "system_type": "Unitary",
        "regional_cluster": "West Africa", 
        "neighbors": ["Burkina Faso", "Ghana", "Guinea", "Liberia", "Mali"],
        "conflict_status": "Post-conflict",
        "surveillance_capacity": "Moderate"
    },
    "GMB": {
        "name": "Gambia",
        "linguistic_group": "Anglophone",
        "primary_language": "English",
        "secondary_languages": "Local languages",
        "system_type": "Unitary",
        "regional_cluster": "West Africa",
        "neighbors": ["Senegal"], 
        "conflict_status": "Stable",
        "surveillance_capacity": "Moderate"
    },
    "GHA": {
        "name": "Ghana",
        "linguistic_group": "Anglophone", 
        "primary_language": "English",
        "secondary_languages": "Local languages",
        "system_type": "Unitary",
        "regional_cluster": "West Africa",
        "neighbors": ["Burkina Faso", "Côte d'Ivoire", "Togo"],
        "conflict_status": "Stable",
        "surveillance_capacity": "Strong"
    },
    "GIN": {
        "name": "Guinea",
        "linguistic_group": "Francophone",
        "primary_language": "French",
        "secondary_languages": "Local languages", 
        "system_type": "Unitary",
        "regional_cluster": "West Africa",
        "neighbors": ["Côte d'Ivoire", "Guinea-Bissau", "Liberia", "Mali", "Senegal", "Sierra Leone"],
        "conflict_status": "Stable",
        "surveillance_capacity": "Weak"
    },
    "GNB": {
        "name": "Guinea-Bissau",
        "linguistic_group": "Lusophone",
        "primary_language": "Portuguese",
        "secondary_languages": "Guinea-Bissau Creole, Local languages",
        "system_type": "Unitary",
        "regional_cluster": "West Africa", 
        "neighbors": ["Guinea", "Senegal"],
        "conflict_status": "Post-conflict",
        "surveillance_capacity": "Weak"
    },
    "LBR": {
        "name": "Liberia",
        "linguistic_group": "Anglophone",
        "primary_language": "English",
        "secondary_languages": "Local languages",
        "system_type": "Unitary",
        "regional_cluster": "West Africa",
        "neighbors": ["Côte d'Ivoire", "Guinea", "Sierra Leone"],
        "conflict_status": "Post-conflict",
        "surveillance_capacity": "Weak"
    },
    "MLI": {
        "name": "Mali",
        "linguistic_group": "Francophone",
        "primary_language": "French",
        "secondary_languages": "Local languages",
        "system_type": "Unitary", 
        "regional_cluster": "West Africa",
        "neighbors": ["Algeria", "Burkina Faso", "Côte d'Ivoire", "Guinea", "Mauritania", "Niger", "Senegal"],
        "conflict_status": "Post-conflict",
        "surveillance_capacity": "Weak"
    },
    "MRT": {
        "name": "Mauritania",
        "linguistic_group": "Arabic/Francophone",
        "primary_language": "Arabic",
        "secondary_languages": "French, Local languages",
        "system_type": "Unitary",
        "regional_cluster": "West Africa",
        "neighbors": ["Algeria", "Mali", "Senegal"],
        "conflict_status": "Stable",
        "surveillance_capacity": "Moderate"
    },
    "NER": {
        "name": "Niger", 
        "linguistic_group": "Francophone",
        "primary_language": "French",
        "secondary_languages": "Local languages",
        "system_type": "Unitary",
        "regional_cluster": "West Africa",
        "neighbors": ["Algeria", "Benin", "Burkina Faso", "Chad", "Libya", "Mali", "Nigeria"],
        "conflict_status": "Post-conflict",
        "surveillance_capacity": "Weak"
    },
    "NGA": {
        "name": "Nigeria",
        "linguistic_group": "Anglophone",
        "primary_language": "English",
        "secondary_languages": "Hausa, Yoruba, Igbo, Local languages",
        "system_type": "Federal",
        "regional_cluster": "West Africa",
        "neighbors": ["Benin", "Cameroon", "Chad", "Niger"],
        "conflict_status": "Post-conflict",
        "surveillance_capacity": "Moderate",
        "total_provinces": "36"
    },
    "SEN": {
        "name": "Senegal",
        "linguistic_group": "Francophone",
        "primary_language": "French",
        "secondary_languages": "Wolof, Local languages",
        "system_type": "Unitary",
        "regional_cluster": "West Africa",
        "neighbors": ["Gambia", "Guinea", "Guinea-Bissau", "Mali", "Mauritania"],
        "conflict_status": "Stable",
        "surveillance_capacity": "Moderate"
    },
    "SLE": {
        "name": "Sierra Leone",
        "linguistic_group": "Anglophone",
        "primary_language": "English",
        "secondary_languages": "Krio, Local languages", 
        "system_type": "Unitary",
        "regional_cluster": "West Africa",
        "neighbors": ["Guinea", "Liberia"],
        "conflict_status": "Post-conflict",
        "surveillance_capacity": "Weak"
    },
    "TGO": {
        "name": "Togo",
        "linguistic_group": "Francophone",
        "primary_language": "French",
        "secondary_languages": "Ewe, Kabye, Local languages",
        "system_type": "Unitary", 
        "regional_cluster": "West Africa",
        "neighbors": ["Benin", "Burkina Faso", "Ghana"],
        "conflict_status": "Stable",
        "surveillance_capacity": "Moderate"
    },
    
    # Central Africa
    "CMR": {
        "name": "Cameroon",
        "linguistic_group": "Francophone",
        "primary_language": "French",
        "secondary_languages": "English, Local languages",
        "system_type": "Unitary",
        "regional_cluster": "Central Africa",
        "neighbors": ["CAR", "Chad", "Republic of Congo", "Equatorial Guinea", "Gabon", "Nigeria"],
        "conflict_status": "Post-conflict",
        "surveillance_capacity": "Moderate"
    },
    "CAF": {
        "name": "Central African Republic",
        "linguistic_group": "Francophone", 
        "primary_language": "French",
        "secondary_languages": "Sango, Local languages",
        "system_type": "Unitary",
        "regional_cluster": "Central Africa",
        "neighbors": ["Cameroon", "Chad", "DRC", "Republic of Congo", "South Sudan", "Sudan"],
        "conflict_status": "Post-conflict",
        "surveillance_capacity": "Weak"
    },
    "TCD": {
        "name": "Chad",
        "linguistic_group": "Francophone/Arabic",
        "primary_language": "French",
        "secondary_languages": "Arabic, Local languages",
        "system_type": "Unitary", 
        "regional_cluster": "Central Africa",
        "neighbors": ["Cameroon", "CAR", "Libya", "Niger", "Nigeria", "Sudan"],
        "conflict_status": "Post-conflict",
        "surveillance_capacity": "Weak"
    },
    "COG": {
        "name": "Republic of Congo",
        "linguistic_group": "Francophone",
        "primary_language": "French",
        "secondary_languages": "Lingala, Local languages",
        "system_type": "Unitary",
        "regional_cluster": "Central Africa",
        "neighbors": ["Angola", "Cameroon", "CAR", "DRC", "Gabon"],
        "conflict_status": "Stable", 
        "surveillance_capacity": "Moderate"
    },
    "COD": {
        "name": "Democratic Republic of Congo",
        "linguistic_group": "Francophone",
        "primary_language": "French", 
        "secondary_languages": "Lingala, Kikongo, Tshiluba, Swahili, Local languages",
        "system_type": "Unitary",
        "regional_cluster": "Central Africa", 
        "neighbors": ["Angola", "Burundi", "CAR", "Republic of Congo", "Rwanda", "South Sudan", "Tanzania", "Uganda", "Zambia"],
        "conflict_status": "Post-conflict",
        "surveillance_capacity": "Weak",
        "total_provinces": "26"
    },
    "GNQ": {
        "name": "Equatorial Guinea",
        "linguistic_group": "Francophone/Lusophone",
        "primary_language": "Spanish", 
        "secondary_languages": "French, Portuguese, Local languages",
        "system_type": "Unitary",
        "regional_cluster": "Central Africa",
        "neighbors": ["Cameroon", "Gabon"],
        "conflict_status": "Stable",
        "surveillance_capacity": "Moderate"
    },
    "GAB": {
        "name": "Gabon",
        "linguistic_group": "Francophone",
        "primary_language": "French",
        "secondary_languages": "Local languages",
        "system_type": "Unitary",
        "regional_cluster": "Central Africa",
        "neighbors": ["Cameroon", "Republic of Congo", "Equatorial Guinea"],
        "conflict_status": "Stable",
        "surveillance_capacity": "Moderate"
    },
    
    # East Africa  
    "BDI": {
        "name": "Burundi",
        "linguistic_group": "Francophone",
        "primary_language": "French",
        "secondary_languages": "Kirundi, Swahili",
        "system_type": "Unitary",
        "regional_cluster": "East Africa",
        "neighbors": ["DRC", "Rwanda", "Tanzania"],
        "conflict_status": "Post-conflict",
        "surveillance_capacity": "Weak"
    },
    "COM": {
        "name": "Comoros",
        "linguistic_group": "Francophone/Arabic",
        "primary_language": "Arabic",
        "secondary_languages": "French, Comorian",
        "system_type": "Unitary",
        "regional_cluster": "Indian Ocean",
        "neighbors": [],
        "conflict_status": "Stable",
        "surveillance_capacity": "Weak"
    },
    "DJI": {
        "name": "Djibouti",
        "linguistic_group": "Arabic/Francophone", 
        "primary_language": "Arabic",
        "secondary_languages": "French, Somali, Afar",
        "system_type": "Unitary",
        "regional_cluster": "East Africa",
        "neighbors": ["Eritrea", "Ethiopia", "Somalia"],
        "conflict_status": "Stable",
        "surveillance_capacity": "Moderate"
    },
    "ERI": {
        "name": "Eritrea",
        "linguistic_group": "Arabic/Multilingual",
        "primary_language": "Tigrinya",
        "secondary_languages": "Arabic, English, Italian",
        "system_type": "Unitary",
        "regional_cluster": "East Africa",
        "neighbors": ["Djibouti", "Ethiopia", "Sudan"],
        "conflict_status": "Post-conflict",
        "surveillance_capacity": "Weak"
    },
    "ETH": {
        "name": "Ethiopia",
        "linguistic_group": "Multilingual",
        "primary_language": "Amharic",
        "secondary_languages": "Oromo, Tigrinya, English", 
        "system_type": "Federal",
        "regional_cluster": "East Africa",
        "neighbors": ["Djibouti", "Eritrea", "Kenya", "Somalia", "South Sudan", "Sudan"],
        "conflict_status": "Post-conflict",
        "surveillance_capacity": "Moderate",
        "total_provinces": "12"
    },
    "KEN": {
        "name": "Kenya",
        "linguistic_group": "Anglophone",
        "primary_language": "English",
        "secondary_languages": "Swahili, Local languages",
        "system_type": "Unitary",
        "regional_cluster": "East Africa",
        "neighbors": ["Ethiopia", "Somalia", "South Sudan", "Tanzania", "Uganda"],
        "conflict_status": "Stable",
        "surveillance_capacity": "Strong"
    },
    "MDG": {
        "name": "Madagascar",
        "linguistic_group": "Francophone",
        "primary_language": "Malagasy",
        "secondary_languages": "French, English",
        "system_type": "Unitary",
        "regional_cluster": "Indian Ocean",
        "neighbors": [],
        "conflict_status": "Stable",
        "surveillance_capacity": "Weak"
    },
    "MUS": {
        "name": "Mauritius",
        "linguistic_group": "Anglophone/Francophone",
        "primary_language": "English", 
        "secondary_languages": "French, Mauritian Creole, Hindi",
        "system_type": "Unitary",
        "regional_cluster": "Indian Ocean",
        "neighbors": [],
        "conflict_status": "Stable",
        "surveillance_capacity": "Strong"
    },
    "MOZ": {
        "name": "Mozambique",
        "linguistic_group": "Lusophone",
        "primary_language": "Portuguese",
        "secondary_languages": "Local languages",
        "system_type": "Unitary",
        "regional_cluster": "Southern Africa", 
        "neighbors": ["Malawi", "South Africa", "Eswatini", "Tanzania", "Zambia", "Zimbabwe"],
        "conflict_status": "Post-conflict",
        "surveillance_capacity": "Weak"
    },
    "RWA": {
        "name": "Rwanda",
        "linguistic_group": "Francophone/Anglophone",
        "primary_language": "Kinyarwanda",
        "secondary_languages": "French, English, Swahili",
        "system_type": "Unitary",
        "regional_cluster": "East Africa",
        "neighbors": ["Burundi", "DRC", "Tanzania", "Uganda"],
        "conflict_status": "Post-conflict",
        "surveillance_capacity": "Moderate"
    },
    "SYC": {
        "name": "Seychelles",
        "linguistic_group": "Anglophone/Francophone", 
        "primary_language": "English",
        "secondary_languages": "French, Seychellois Creole",
        "system_type": "Unitary",
        "regional_cluster": "Indian Ocean",
        "neighbors": [],
        "conflict_status": "Stable",
        "surveillance_capacity": "Strong"
    },
    "SOM": {
        "name": "Somalia",
        "linguistic_group": "Arabic/Multilingual",
        "primary_language": "Somali",
        "secondary_languages": "Arabic, English, Italian",
        "system_type": "Post-conflict",
        "regional_cluster": "East Africa",
        "neighbors": ["Djibouti", "Ethiopia", "Kenya"], 
        "conflict_status": "Post-conflict",
        "surveillance_capacity": "Weak"
    },
    "SSD": {
        "name": "South Sudan",
        "linguistic_group": "Anglophone",
        "primary_language": "English",
        "secondary_languages": "Arabic, Local languages",
        "system_type": "Post-conflict",
        "regional_cluster": "East Africa",
        "neighbors": ["CAR", "DRC", "Ethiopia", "Kenya", "Sudan", "Uganda"],
        "conflict_status": "Post-conflict",
        "surveillance_capacity": "Weak"
    },
    "TZA": {
        "name": "Tanzania",
        "linguistic_group": "Anglophone",
        "primary_language": "Swahili",
        "secondary_languages": "English, Local languages",
        "system_type": "Unitary",
        "regional_cluster": "East Africa", 
        "neighbors": ["Burundi", "DRC", "Kenya", "Malawi", "Mozambique", "Rwanda", "Uganda", "Zambia"],
        "conflict_status": "Stable",
        "surveillance_capacity": "Moderate"
    },
    "UGA": {
        "name": "Uganda",
        "linguistic_group": "Anglophone",
        "primary_language": "English",
        "secondary_languages": "Swahili, Local languages",
        "system_type": "Unitary",
        "regional_cluster": "East Africa",
        "neighbors": ["DRC", "Kenya", "Rwanda", "South Sudan", "Tanzania"],
        "conflict_status": "Stable",
        "surveillance_capacity": "Moderate"
    },
    
    # Southern Africa
    "AGO": {
        "name": "Angola",
        "linguistic_group": "Lusophone",
        "primary_language": "Portuguese",
        "secondary_languages": "Local languages",
        "system_type": "Unitary",
        "regional_cluster": "Southern Africa",
        "neighbors": ["DRC", "Republic of Congo", "Namibia", "Zambia"],
        "conflict_status": "Post-conflict",
        "surveillance_capacity": "Moderate",
        "total_provinces": "18"
    },
    "BWA": {
        "name": "Botswana",
        "linguistic_group": "Anglophone",
        "primary_language": "English",
        "secondary_languages": "Setswana, Local languages",
        "system_type": "Unitary",
        "regional_cluster": "Southern Africa",
        "neighbors": ["Namibia", "South Africa", "Zambia", "Zimbabwe"],
        "conflict_status": "Stable",
        "surveillance_capacity": "Moderate"
    },
    "SWZ": {
        "name": "Eswatini",
        "linguistic_group": "Anglophone", 
        "primary_language": "English",
        "secondary_languages": "SiSwati",
        "system_type": "Unitary",
        "regional_cluster": "Southern Africa",
        "neighbors": ["Mozambique", "South Africa"],
        "conflict_status": "Stable",
        "surveillance_capacity": "Moderate"
    },
    "LSO": {
        "name": "Lesotho",
        "linguistic_group": "Anglophone",
        "primary_language": "English",
        "secondary_languages": "Sesotho",
        "system_type": "Unitary",
        "regional_cluster": "Southern Africa",
        "neighbors": ["South Africa"],
        "conflict_status": "Stable", 
        "surveillance_capacity": "Moderate"
    },
    "MWI": {
        "name": "Malawi",
        "linguistic_group": "Anglophone",
        "primary_language": "English",
        "secondary_languages": "Chichewa, Local languages",
        "system_type": "Unitary",
        "regional_cluster": "Southern Africa",
        "neighbors": ["Mozambique", "Tanzania", "Zambia"],
        "conflict_status": "Stable",
        "surveillance_capacity": "Moderate"
    },
    "NAM": {
        "name": "Namibia",
        "linguistic_group": "Anglophone",
        "primary_language": "English",
        "secondary_languages": "Afrikaans, German, Local languages",
        "system_type": "Unitary",
        "regional_cluster": "Southern Africa",
        "neighbors": ["Angola", "Botswana", "South Africa", "Zambia"],
        "conflict_status": "Stable",
        "surveillance_capacity": "Moderate"
    },
    "ZAF": {
        "name": "South Africa",
        "linguistic_group": "Anglophone",
        "primary_language": "English", 
        "secondary_languages": "Afrikaans, Zulu, Xhosa, Other official languages",
        "system_type": "Federal",
        "regional_cluster": "Southern Africa",
        "neighbors": ["Botswana", "Eswatini", "Lesotho", "Mozambique", "Namibia", "Zimbabwe"],
        "conflict_status": "Stable",
        "surveillance_capacity": "Strong",
        "total_provinces": "9"
    },
    "ZMB": {
        "name": "Zambia", 
        "linguistic_group": "Anglophone",
        "primary_language": "English",
        "secondary_languages": "Local languages",
        "system_type": "Unitary",
        "regional_cluster": "Southern Africa",
        "neighbors": ["Angola", "Botswana", "DRC", "Malawi", "Mozambique", "Namibia", "Tanzania", "Zimbabwe"],
        "conflict_status": "Stable",
        "surveillance_capacity": "Moderate"
    },
    "ZWE": {
        "name": "Zimbabwe",
        "linguistic_group": "Anglophone",
        "primary_language": "English",
        "secondary_languages": "Shona, Ndebele, Local languages", 
        "system_type": "Unitary",
        "regional_cluster": "Southern Africa", 
        "neighbors": ["Botswana", "Mozambique", "South Africa", "Zambia"],
        "conflict_status": "Post-conflict",
        "surveillance_capacity": "Weak"
    },
    
    # Additional countries
    "STP": {
        "name": "São Tomé and Príncipe",
        "linguistic_group": "Lusophone",
        "primary_language": "Portuguese",
        "secondary_languages": "Forro, Local languages",
        "system_type": "Unitary",
        "regional_cluster": "Central Africa/Island",
        "neighbors": [],
        "conflict_status": "Stable",
        "surveillance_capacity": "Weak"
    }
}

def create_country_directories(base_path):
    """Create data subdirectories for all African countries with enhanced structure"""
    print("Creating country directories with enhanced structure...")
    
    for iso_code, country_info in AFRICAN_COUNTRIES.items():
        country_dir = Path(base_path) / "data" / iso_code
        country_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Created: {country_dir}")
    
    print(f"Created directories for {len(AFRICAN_COUNTRIES)} countries")

def customize_prompt(template_content, iso_code, country_info):
    """Customize the prompt template with country-specific information"""
    
    # Join neighbors list into a comma-separated string
    neighbors_str = ", ".join(country_info["neighbors"]) if country_info["neighbors"] else "None (Island nation)"
    
    # Create substitution mapping for all placeholders
    substitutions = {
        "{COUNTRY_NAME}": country_info["name"],
        "{ISO_CODE}": iso_code,
        "{LINGUISTIC_GROUP}": country_info["linguistic_group"], 
        "{PRIMARY_LANGUAGE}": country_info["primary_language"],
        "{SECONDARY_LANGUAGES}": country_info["secondary_languages"],
        "{SYSTEM_TYPE}": country_info["system_type"],
        "{REGIONAL_CLUSTER}": country_info["regional_cluster"],
        "{NEIGHBOR_LIST}": neighbors_str,
        "{CONFLICT_STATUS}": country_info["conflict_status"],
        "{SURVEILLANCE_CAPACITY}": country_info["surveillance_capacity"],
        "{TOTAL_PROVINCES}": country_info.get("total_provinces", "Unknown")
    }
    
    # Apply substitutions to the template
    customized_content = template_content
    for placeholder, value in substitutions.items():
        customized_content = customized_content.replace(placeholder, value)
    
    return customized_content

def customize_workflow(template_content, iso_code, country_info):
    """Customize the workflow template with country-specific information and file references"""
    
    # First apply standard country-specific substitutions
    customized_content = customize_prompt(template_content, iso_code, country_info)
    
    # Apply workflow-specific substitutions
    workflow_substitutions = {
        "./template_search_protocol.txt": f"./search_protocol_{iso_code}.txt",
        "template_search_protocol.txt": f"search_protocol_{iso_code}.txt",
        "prompt_{ISO}.txt": f"prompt_{iso_code}.txt"
    }
    
    # Apply workflow substitutions
    for template_ref, country_ref in workflow_substitutions.items():
        customized_content = customized_content.replace(template_ref, country_ref)
    
    return customized_content

def create_country_prompts(base_path):
    """Create customized prompt files for each country using 8-phase search protocol"""
    print("Creating 8-phase search protocol prompt files...")
    
    # Read the search protocol template file
    template_path = Path(base_path) / "template_search_protocol.txt"
    
    if not template_path.exists():
        raise FileNotFoundError(f"Search protocol template file not found: {template_path}")
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    # Create customized prompts for each country
    for iso_code, country_info in AFRICAN_COUNTRIES.items():
        # Customize the prompt content with country-specific variables
        customized_content = customize_prompt(template_content, iso_code, country_info)
        
        # Create the country-specific search protocol file inside the country's data directory
        country_dir = Path(base_path) / "data" / iso_code
        search_protocol_file = country_dir / f"search_protocol_{iso_code}.txt"
        
        # Write the search protocol file
        with open(search_protocol_file, 'w', encoding='utf-8') as f:
            f.write(customized_content)
        
        print(f"  Created: {search_protocol_file}")
    
    print(f"Created 8-phase search protocols for {len(AFRICAN_COUNTRIES)} countries")

def create_country_info_key(base_path):
    """Create comprehensive country information key with all classifications"""
    print("Creating comprehensive country information key...")
    
    key_file = Path(base_path) / "country_info_key.json"
    
    # Create comprehensive information structure
    country_info_complete = {
        "metadata": {
            "version": "2.0",
            "protocol": "8-Phase Search Protocol",
            "countries_total": len(AFRICAN_COUNTRIES),
            "creation_date": "2025-01-20",
            "description": "Complete country information for MOSAIC AI Cholera Data Collection"
        },
        "countries": AFRICAN_COUNTRIES
    }
    
    with open(key_file, 'w', encoding='utf-8') as f:
        json.dump(country_info_complete, f, indent=2, ensure_ascii=False)
    
    print(f"Created comprehensive country information key: {key_file}")


def create_country_workflows(base_path):
    """Create customized agentic workflow files for each country"""
    print("Creating 6-agent workflow files...")
    
    # Read the agentic workflow template file
    workflow_template_path = Path(base_path) / "template_agentic_workflow.txt"
    
    if not workflow_template_path.exists():
        raise FileNotFoundError(f"Agentic workflow template file not found: {workflow_template_path}")
    
    with open(workflow_template_path, 'r', encoding='utf-8') as f:
        workflow_template_content = f.read()
    
    # Create customized workflow files for each country
    for iso_code, country_info in AFRICAN_COUNTRIES.items():
        # Customize the workflow content with country-specific variables and file references
        customized_workflow = customize_workflow(workflow_template_content, iso_code, country_info)
        
        # Create the country-specific workflow file inside the country's data directory
        country_dir = Path(base_path) / "data" / iso_code
        workflow_file = country_dir / f"agentic_workflow_{iso_code}.txt"
        
        with open(workflow_file, 'w', encoding='utf-8') as f:
            f.write(customized_workflow)
        
        print(f"  Created: {workflow_file}")
    
    print(f"Created 6-agent workflow files for {len(AFRICAN_COUNTRIES)} countries")

def create_execution_checklist(base_path):
    """Create execution checklist template for tracking country completion"""
    print("Creating execution checklist template...")
    
    checklist_content = """# MOSAIC AI Cholera Data Collection - Execution Checklist

## 8-Phase Search Protocol Tracking

**Protocol Version**: 2.0  
**Total Countries**: 54 African countries  
**Completion Target**: 100% comprehensive discovery  

## Completion Status Tracking

Format: ☐ COUNTRY_NAME (ISO_CODE) - Status: [PENDING/IN_PROGRESS/COMPLETED] - Date: YYYY-MM-DD

### North Africa (6 countries)
☐ Algeria (DZA) - Status: PENDING - Date: ____-__-__
☐ Egypt (EGY) - Status: PENDING - Date: ____-__-__  
☐ Libya (LBY) - Status: PENDING - Date: ____-__-__
☐ Morocco (MAR) - Status: PENDING - Date: ____-__-__
☐ Sudan (SDN) - Status: PENDING - Date: ____-__-__
☐ Tunisia (TUN) - Status: PENDING - Date: ____-__-__

### West Africa (16 countries)
☐ Benin (BEN) - Status: PENDING - Date: ____-__-__
☐ Burkina Faso (BFA) - Status: PENDING - Date: ____-__-__
☐ Cape Verde (CPV) - Status: PENDING - Date: ____-__-__
☐ Côte d'Ivoire (CIV) - Status: PENDING - Date: ____-__-__
☐ Gambia (GMB) - Status: PENDING - Date: ____-__-__
☐ Ghana (GHA) - Status: PENDING - Date: ____-__-__
☐ Guinea (GIN) - Status: PENDING - Date: ____-__-__
☐ Guinea-Bissau (GNB) - Status: PENDING - Date: ____-__-__
☐ Liberia (LBR) - Status: PENDING - Date: ____-__-__
☐ Mali (MLI) - Status: PENDING - Date: ____-__-__
☐ Mauritania (MRT) - Status: PENDING - Date: ____-__-__
☐ Niger (NER) - Status: PENDING - Date: ____-__-__
☐ Nigeria (NGA) - Status: PENDING - Date: ____-__-__
☐ Senegal (SEN) - Status: PENDING - Date: ____-__-__
☐ Sierra Leone (SLE) - Status: PENDING - Date: ____-__-__
☐ Togo (TGO) - Status: PENDING - Date: ____-__-__

### Central Africa (7 countries)
☐ Cameroon (CMR) - Status: PENDING - Date: ____-__-__
☐ Central African Republic (CAF) - Status: PENDING - Date: ____-__-__
☐ Chad (TCD) - Status: PENDING - Date: ____-__-__
☐ Republic of Congo (COG) - Status: PENDING - Date: ____-__-__
☐ Democratic Republic of Congo (COD) - Status: PENDING - Date: ____-__-__
☐ Equatorial Guinea (GNQ) - Status: PENDING - Date: ____-__-__
☐ Gabon (GAB) - Status: PENDING - Date: ____-__-__

### East Africa (13 countries)
☐ Burundi (BDI) - Status: PENDING - Date: ____-__-__
☐ Comoros (COM) - Status: PENDING - Date: ____-__-__
☐ Djibouti (DJI) - Status: PENDING - Date: ____-__-__
☐ Eritrea (ERI) - Status: PENDING - Date: ____-__-__
☐ Ethiopia (ETH) - Status: PENDING - Date: ____-__-__
☐ Kenya (KEN) - Status: PENDING - Date: ____-__-__
☐ Madagascar (MDG) - Status: PENDING - Date: ____-__-__
☐ Mauritius (MUS) - Status: PENDING - Date: ____-__-__
☐ Rwanda (RWA) - Status: PENDING - Date: ____-__-__
☐ Seychelles (SYC) - Status: PENDING - Date: ____-__-__
☐ Somalia (SOM) - Status: PENDING - Date: ____-__-__
☐ South Sudan (SSD) - Status: PENDING - Date: ____-__-__
☐ Tanzania (TZA) - Status: PENDING - Date: ____-__-__
☐ Uganda (UGA) - Status: PENDING - Date: ____-__-__

### Southern Africa (11 countries)
☐ Angola (AGO) - Status: PENDING - Date: ____-__-__
☐ Botswana (BWA) - Status: PENDING - Date: ____-__-__
☐ Eswatini (SWZ) - Status: PENDING - Date: ____-__-__
☐ Lesotho (LSO) - Status: PENDING - Date: ____-__-__
☐ Malawi (MWI) - Status: PENDING - Date: ____-__-__
☐ Mozambique (MOZ) - Status: PENDING - Date: ____-__-__
☐ Namibia (NAM) - Status: PENDING - Date: ____-__-__
☐ South Africa (ZAF) - Status: PENDING - Date: ____-__-__
☐ Zambia (ZMB) - Status: PENDING - Date: ____-__-__
☐ Zimbabwe (ZWE) - Status: PENDING - Date: ____-__-__

### Island Nations (1 country)
☐ São Tomé and Príncipe (STP) - Status: PENDING - Date: ____-__-__

## Summary Statistics
- **Total Countries**: 54
- **Completed**: __/54 (_%%)
- **In Progress**: __/54 (_%%)
- **Pending**: __/54 (_%%)

---
**Last Updated**: ____-__-__ by: ____________
"""
    
    checklist_file = Path(base_path) / "country_checklist.txt"
    with open(checklist_file, 'w', encoding='utf-8') as f:
        f.write(checklist_content)
    
    print(f"Created execution checklist: {checklist_file}")

def main():
    """Main function to set up all countries with 8-phase search protocol"""
    # Get the base path (directory containing this script)
    base_path = Path(__file__).parent
    
    print("=" * 80)
    print("MOSAIC AI CHOLERA DATA COLLECTION - 8-PHASE SEARCH SETUP v2.0")
    print("=" * 80)
    print(f"Setting up comprehensive data collection for {len(AFRICAN_COUNTRIES)} African countries")
    print(f"Base directory: {base_path}")
    print(f"Protocol: 8-Phase Search Protocol (Systematic Methodology)")
    print("-" * 80)
    
    try:
        # Step 1: Create country directories with enhanced structure
        create_country_directories(base_path)
        print()
        
        # Step 2: Create customized 8-phase search prompt files
        create_country_prompts(base_path)
        print()
        
        # Step 3: Create comprehensive country information key
        create_country_info_key(base_path)
        print()
        
        # Step 4: Create customized agentic workflow files
        create_country_workflows(base_path)
        print()
        
        # Step 5: Create execution checklist
        create_execution_checklist(base_path)
        print()
        
        print("=" * 80)
        print("✅ 8-PHASE SEARCH SETUP COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print(f"📁 Created {len(AFRICAN_COUNTRIES)} country directories")
        print(f"📄 Created {len(AFRICAN_COUNTRIES)} search protocol files")
        print(f"🤖 Created {len(AFRICAN_COUNTRIES)} 6-agent workflow files")
        print(f"🔑 Created comprehensive country information key")
        print(f"📋 Created execution checklist template")
        
        print("\n🚀 IMPLEMENTATION READY:")
        print("1. 📚 Follow CLAUDE.md for complete 8-phase methodology")
        print("2. 🎯 Use search_protocol_{ISO_CODE}.txt files for Agent 1 (baseline search)")
        print("3. 🤖 Use agentic_workflow_{ISO_CODE}.txt for complete 6-agent workflow")
        print("4. 📋 Track progress using country_checklist.txt")
        print("5. 🔍 Reference country_info_key.json for detailed country information")
        
        print("\n⚡ 8-PHASE SEARCH FEATURES ENABLED:")
        print("- 8-Phase Systematic Methodology")
        print("- Discovery Saturation Criteria (< 1 new source per 15 queries)")
        print("- Multi-Language Search Capability")
        print("- Cross-Border Intelligence")
        print("- Institutional Modules (WHO GHO, UNICEF, MSF, Academic)")
        print("- 6 Comprehensive Quality Gates")
        print("- Enhanced Dual-Reference System")
        print("- 4-Tier Reliability Classification")
        
        print(f"\n🎯 SUCCESS TARGET: Complete discovery of all available cholera surveillance data")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ ERROR DURING SETUP: {e}")
        raise

if __name__ == "__main__":
    main()