#!/usr/bin/env python3
"""
Update dashboard HTML with README content.
This script integrates README content into the dashboard and creates an update script.
"""

import re
import os
import sys
from pathlib import Path

# First, run the conversion script
os.system('python py/convert_readme_to_html.py')

# Read the generated HTML sections
base_dir = Path(__file__).parent.parent
readme_dir = base_dir / 'dashboard' / 'readme_sections'

with open(readme_dir / 'main_readme.html', 'r', encoding='utf-8') as f:
    main_readme_html = f.read()

with open(readme_dir / 'agents_readme.html', 'r', encoding='utf-8') as f:
    agents_readme_html = f.read()

# Clean up the HTML to remove duplicate content that's already in the dashboard
# Remove the abstract section from main README since it's in the banner
main_readme_html = re.sub(r'<h3><strong>Abstract</strong></h3>.*?(?=<h3>)', '', main_readme_html, flags=re.DOTALL)

# Read the test dashboard
with open(base_dir / 'dashboard' / 'dashboard_test.html', 'r', encoding='utf-8') as f:
    dashboard_content = f.read()

# Add styles for README content
readme_styles = """
        /* README Content Styles */
        .readme-content {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .readme-content h1 {
            font-size: 2.2rem;
            color: #0167af;
            margin: 2rem 0 1rem;
            border-bottom: 3px solid #e0e0e0;
            padding-bottom: 0.5rem;
        }
        
        .readme-content h2 {
            font-size: 1.8rem;
            color: #0167af;
            margin: 2rem 0 1rem;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 0.5rem;
        }
        
        .readme-content h3 {
            font-size: 1.5rem;
            color: #333;
            margin: 1.5rem 0 0.8rem;
        }
        
        .readme-content h4 {
            font-size: 1.2rem;
            color: #495057;
            margin: 1.2rem 0 0.6rem;
        }
        
        .readme-content p {
            line-height: 1.8;
            margin-bottom: 1rem;
        }
        
        .readme-content ul, .readme-content ol {
            margin: 1rem 0 1rem 2rem;
            line-height: 1.8;
        }
        
        .readme-content li {
            margin-bottom: 0.5rem;
        }
        
        .readme-content code {
            background: #f0f4f8;
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9em;
        }
        
        .readme-content pre {
            background: #f8f9fa;
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            padding: 1rem;
            overflow-x: auto;
            margin: 1rem 0;
        }
        
        .readme-content pre code {
            background: none;
            padding: 0;
        }
        
        .readme-content blockquote {
            border-left: 4px solid #0167af;
            padding-left: 1rem;
            margin: 1rem 0;
            color: #666;
        }
        
        .readme-content table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }
        
        .readme-content th, .readme-content td {
            border: 1px solid #dee2e6;
            padding: 0.75rem;
            text-align: left;
        }
        
        .readme-content th {
            background: #f8f9fa;
            font-weight: 600;
        }
        
        .readme-content hr {
            border: none;
            border-top: 2px solid #e0e0e0;
            margin: 2rem 0;
        }
"""

# Insert the styles before the closing style tag
dashboard_content = dashboard_content.replace('    </style>', readme_styles + '    </style>')

# Add the Agents tab button after About & Methods
tab_button_replacement = '''            <button class="tab-button active" onclick="showTab('about-methods')">
                <i class="fas fa-info-circle"></i> About & Methods
            </button>
            <button class="tab-button" onclick="showTab('agents')">
                <i class="fas fa-robot"></i> Agents
            </button>'''

dashboard_content = dashboard_content.replace(
    '''            <button class="tab-button active" onclick="showTab('about-methods')">
                <i class="fas fa-info-circle"></i> About & Methods
            </button>''',
    tab_button_replacement
)

# Replace the About & Methods content with the README content
about_methods_content = f'''        <!-- About & Methods Tab -->
        <div id="about-methods" class="tab-content active">
            <div class="readme-content">
                {main_readme_html}
            </div>
        </div>'''

# Find and replace the existing About & Methods section
pattern = r'<!-- About & Methods Tab -->.*?</div>\s*</div>'
dashboard_content = re.sub(pattern, about_methods_content, dashboard_content, flags=re.DOTALL)

# Add the new Agents tab after the About & Methods tab
agents_tab_content = f'''

        <!-- Agents Tab -->
        <div id="agents" class="tab-content">
            <div class="readme-content">
                {agents_readme_html}
            </div>
        </div>'''

# Insert after the About & Methods tab
dashboard_content = dashboard_content.replace(
    '</div>\n\n        <!-- Other tabs',
    '</div>' + agents_tab_content + '\n\n        <!-- Other tabs'
)

# Save the updated dashboard
output_path = base_dir / 'dashboard' / 'dashboard_with_readme.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(dashboard_content)

print(f"Created updated dashboard: {output_path}")

# Create an update script for future use
update_script = '''#!/bin/bash
# Script to update dashboard with latest README content

echo "Updating dashboard with latest README content..."

# Convert README files to HTML
python py/convert_readme_to_html.py

# Update dashboard with README content
python py/update_dashboard_with_readme.py

echo "Dashboard updated successfully!"
echo "View the updated dashboard at: dashboard/dashboard_with_readme.html"
'''

update_script_path = base_dir / 'update_dashboard_readme.sh'
with open(update_script_path, 'w') as f:
    f.write(update_script)

os.chmod(update_script_path, 0o755)
print(f"Created update script: {update_script_path}")