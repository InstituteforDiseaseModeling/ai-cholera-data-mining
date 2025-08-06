#!/usr/bin/env python3
"""
Convert README.md files to HTML sections for dashboard integration.
This script converts markdown to HTML while preserving the structure
and formatting for inclusion in the dashboard.
"""

import re
import os
import sys
from pathlib import Path

def convert_markdown_to_html(markdown_content):
    """Convert markdown content to HTML with appropriate styling."""
    html = markdown_content
    
    # Convert headers
    html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    
    # Convert bold and italic
    html = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', html)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    
    # Convert inline code
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
    
    # Convert code blocks
    def replace_code_block(match):
        lang = match.group(1) or ''
        code = match.group(2)
        return f'<pre><code class="language-{lang}">{code}</code></pre>'
    
    html = re.sub(r'```(\w*)\n(.*?)```', replace_code_block, html, flags=re.DOTALL)
    
    # Convert links and images
    html = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1" style="max-width: 100%;">', html)
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
    
    # Convert lists
    lines = html.split('\n')
    processed_lines = []
    in_ul = False
    in_ol = False
    
    for line in lines:
        # Unordered lists
        if re.match(r'^[-*] ', line):
            if not in_ul:
                processed_lines.append('<ul>')
                in_ul = True
            processed_lines.append('<li>' + line[2:].strip() + '</li>')
        elif in_ul and not re.match(r'^[-*] |^  ', line):
            processed_lines.append('</ul>')
            in_ul = False
            processed_lines.append(line)
        # Ordered lists
        elif re.match(r'^\d+\. ', line):
            if not in_ol:
                processed_lines.append('<ol>')
                in_ol = True
            processed_lines.append('<li>' + re.sub(r'^\d+\. ', '', line).strip() + '</li>')
        elif in_ol and not re.match(r'^\d+\. |^  ', line):
            processed_lines.append('</ol>')
            in_ol = False
            processed_lines.append(line)
        else:
            # Convert paragraphs
            if line.strip() and not line.startswith('<'):
                processed_lines.append(f'<p>{line}</p>')
            else:
                processed_lines.append(line)
    
    # Close any open lists
    if in_ul:
        processed_lines.append('</ul>')
    if in_ol:
        processed_lines.append('</ol>')
    
    html = '\n'.join(processed_lines)
    
    # Clean up empty paragraphs
    html = re.sub(r'<p>\s*</p>', '', html)
    html = re.sub(r'<p>(<h[1-6]>)', r'\1', html)
    html = re.sub(r'(</h[1-6]>)</p>', r'\1', html)
    html = re.sub(r'<p>(<ul>|<ol>|<pre>)', r'\1', html)
    html = re.sub(r'(</ul>|</ol>|</pre>)</p>', r'\1', html)
    
    return html

def generate_readme_sections():
    """Generate HTML sections for both README files."""
    base_dir = Path(__file__).parent.parent
    
    # Convert main README
    main_readme_path = base_dir / 'README.md'
    with open(main_readme_path, 'r', encoding='utf-8') as f:
        main_content = f.read()
    
    # Skip the logo and badges at the top
    main_content = re.sub(r'^<img.*?>\s*\n', '', main_content)
    main_content = re.sub(r'^\[\!\[.*?\]\(.*?\)\]\(.*?\)\s*\n', '', main_content, flags=re.MULTILINE)
    
    main_html = convert_markdown_to_html(main_content)
    
    # Convert agents README
    agents_readme_path = base_dir / 'agents' / 'README.md'
    with open(agents_readme_path, 'r', encoding='utf-8') as f:
        agents_content = f.read()
    
    agents_html = convert_markdown_to_html(agents_content)
    
    # Save the HTML sections
    output_dir = base_dir / 'dashboard' / 'readme_sections'
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / 'main_readme.html', 'w', encoding='utf-8') as f:
        f.write(main_html)
    
    with open(output_dir / 'agents_readme.html', 'w', encoding='utf-8') as f:
        f.write(agents_html)
    
    print(f"Generated HTML sections in {output_dir}")
    print("- main_readme.html")
    print("- agents_readme.html")
    
    # Also create a combined test file
    test_html = f"""
<!-- Main README Content -->
<div class="readme-content">
{main_html}
</div>

<!-- Agents README Content -->
<div class="agents-readme-content">
{agents_html}
</div>
"""
    
    with open(output_dir / 'combined_test.html', 'w', encoding='utf-8') as f:
        f.write(test_html)

if __name__ == "__main__":
    generate_readme_sections()