#!/usr/bin/env python3
"""
One-time backfill: extract link and pixel data from rendered viewer HTML
and persist to metadata.json so --regen-only can produce correct audit scores.

Usage: python backfill_audit_data.py
Then run: python process_email.py --regen-only
"""
import json
import os
import sys
from bs4 import BeautifulSoup

OUTPUT_FOLDER = 'docs'


def extract_links(soup):
    """Extract link audit data from rendered viewer HTML."""
    links = []
    for card in soup.select('div.link-card-v2[id^="lc-"]'):
        index_el = card.select_one('.card-v2-index')
        domain_el = card.select_one('.card-v2-domain')
        url_el = card.select_one('.card-v2-url-truncated')
        txt_el = card.select_one('.card-v2-text')
        if not url_el:
            continue
        links.append({
            'index': int(index_el.get_text(strip=True)) if index_el else 0,
            'domain': domain_el.get_text(strip=True) if domain_el else '',
            'original_url': url_el.get_text(strip=True),
            'txt': txt_el.get_text(strip=True) if txt_el else '',
            'is_tracking': bool(card.select_one('.tag-tracking')),
            'is_secure': not bool(card.select_one('.tag-unsecure')),
            'is_dev': bool(card.select_one('.tag-dev')),
        })
    return links


def extract_pixels(soup):
    """Extract tracking pixel data from rendered viewer HTML."""
    pixels = []
    for card in soup.select('div.link-card-v2[id^="px-"]'):
        domain_el = card.select_one('.card-v2-domain')
        url_el = card.select_one('.card-v2-url-truncated')
        txt_el = card.select_one('.card-v2-text')
        if not url_el:
            continue
        pixels.append({
            'domain': domain_el.get_text(strip=True) if domain_el else '',
            'url': url_el.get_text(strip=True),
            'status': txt_el.get_text(strip=True) if txt_el else '',
        })
    return pixels


def backfill():
    if not os.path.exists(OUTPUT_FOLDER):
        print(f"Error: {OUTPUT_FOLDER}/ not found.", file=sys.stderr)
        sys.exit(1)

    updated = 0
    skipped = 0
    for entry in sorted(os.listdir(OUTPUT_FOLDER)):
        meta_path = os.path.join(OUTPUT_FOLDER, entry, 'metadata.json')
        viewer_path = os.path.join(OUTPUT_FOLDER, entry, 'index.html')
        if not os.path.exists(meta_path) or not os.path.exists(viewer_path):
            continue

        with open(meta_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        # Skip if already backfilled
        if 'links' in metadata and 'detected_pixels' in metadata:
            skipped += 1
            continue

        with open(viewer_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'lxml')

        links = extract_links(soup)
        pixels = extract_pixels(soup)

        metadata['links'] = links
        metadata['detected_pixels'] = pixels

        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=4)

        print(f"  {entry}: {len(links)} links, {len(pixels)} pixels")
        updated += 1

    print(f"\nDone: {updated} updated, {skipped} already had data.")
    print("Now run: python process_email.py --regen-only")


if __name__ == '__main__':
    backfill()
