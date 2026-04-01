#!/usr/bin/env python3
"""
Apply <base target="_blank"> to all existing archived email HTML files.
This fixes the issue where links in the viewer don't open in new tabs.
"""

import os
import re
from pathlib import Path
from bs4 import BeautifulSoup

def apply_base_target_to_file(html_path):
    """Inject <base target="_blank"> into an email HTML file."""
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Check if base tag already exists
        existing_base = soup.find('base')
        if existing_base and existing_base.get('target') == '_blank':
            return False  # Already has the fix
        
        # Create or find head
        if not soup.head:
            head_tag = soup.new_tag('head')
            if soup.html:
                soup.html.insert(0, head_tag)
            else:
                soup.insert(0, head_tag)
        
        # Create base tag
        base_tag = soup.new_tag('base', target='_blank')
        
        # Insert at beginning of head
        soup.head.insert(0, base_tag)
        
        # Write back
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        
        return True
    except Exception as e:
        print(f"  ERROR: {html_path}: {e}")
        return False

def main():
    docs_dir = Path('docs')
    if not docs_dir.exists():
        print("ERROR: docs/ directory not found")
        return
    
    # Find all index.html files in email subdirectories (e.g., docs/a3f5bd4d8000/index.html)
    html_files = list(docs_dir.glob('*/index.html'))
    
    if not html_files:
        print("No archived email HTML files found in docs/*/index.html")
        return
    
    print(f"Found {len(html_files)} archived email files to process...")
    
    updated = 0
    skipped = 0
    errors = 0
    
    for html_file in html_files:
        try:
            result = apply_base_target_to_file(html_file)
            if result:
                updated += 1
                print(f"  ✓ {html_file.relative_to(docs_dir)}")
            else:
                skipped += 1
        except Exception as e:
            errors += 1
            print(f"  ✗ {html_file.relative_to(docs_dir)}: {e}")
    
    print(f"\nDone! Updated: {updated}, Skipped (already fixed): {skipped}, Errors: {errors}")

if __name__ == '__main__':
    main()
