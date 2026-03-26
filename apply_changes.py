import datetime
import json
import logging
import os
import re
from email.header import decode_header

from src.parser import EmailParser
from src.generator import generate_viewer, generate_index, copy_assets

logger = logging.getLogger(__name__)

DOCS_DIR = "docs"

def apply_changes():
    logger.info("Starting update of existing archives...")
    
    all_metadata = []
    
    # Iterate over all subdirectories
    for item in os.listdir(DOCS_DIR):
        folder_path = os.path.join(DOCS_DIR, item)
        if not os.path.isdir(folder_path) or item == "assets":
            continue
            
        meta_path = os.path.join(folder_path, "metadata.json")
        viewer_path = os.path.join(folder_path, "index.html")
        
        if not os.path.exists(meta_path) or not os.path.exists(viewer_path):
            continue
            
        logger.info("Processing %s...", item)
        
        # 1. Load Metadata
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except Exception as e:
            logger.error("Error loading metadata for %s: %s", item, e)
            continue
            
        # 2. Extract HTML from Viewer
        with open(viewer_path, 'r', encoding='utf-8') as f:
            viewer_content = f.read()
            
        # Custom extraction based on markers
        start_marker = "const content = "
        end_marker = "const frame = document.getElementById('emailFrame');"
        
        start_pos = viewer_content.find(start_marker)
        end_pos = viewer_content.find(end_marker)
        
        if start_pos == -1 or end_pos == -1:
            logger.warning("Could not extract content markers from %s — skipping re-render.", item)
            all_metadata.append(metadata)
            continue
             
        # Extract everything between
        raw_segment = viewer_content[start_pos + len(start_marker):end_pos]
        # Cleanup whitespace and trailing semicolon
        raw_json = raw_segment.strip()
        if raw_json.endswith(';'):
            raw_json = raw_json[:-1]
            
        try:
            html_content = json.loads(raw_json)
        except Exception as e:
            logger.error("Error parsing HTML JSON in %s: %s", item, e)
            all_metadata.append(metadata)
            continue
            
        # 3. Re-Parse
        parser = EmailParser(html_content, folder_path)
        parser.clean_and_process() # Aggressive cleaning
        crm = parser.detect_crm()
        parser.download_images_parallel()
        
        # 4. Update Metadata
        metadata['preheader'] = parser.preheader
        metadata['crm'] = crm
        metadata['audit'] = parser.audit
        metadata['links'] = parser.links
        metadata['detected_pixels'] = parser.detected_pixels
        
        # Decode sender if it's MIMED
        sender = metadata.get('sender', 'Unknown')
        if "=?" in sender:
            try:
                decoded_list = decode_header(sender)
                new_sender = ""
                for part, encoding in decoded_list:
                    if isinstance(part, bytes):
                        new_sender += part.decode(encoding or "utf-8", errors="ignore")
                    else:
                        new_sender += str(part)
                metadata['sender'] = new_sender.strip()
                logger.info("Decoded sender for %s: %s", item, metadata['sender'])
            except Exception as e:
                logger.warning("Error decoding sender for %s: %s", item, e)

        # Note: We can't re-decode sender here easily because we don't have the MIME msg,
        # but the next import will behave correctly.
        
        # Save updated metadata
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=4)
            
        # 5. Re-Generate Viewer
        generate_viewer(
            metadata, 
            parser.get_html(), 
            parser.links, 
            viewer_path,
            detected_pixels=parser.detected_pixels
        )
        
        all_metadata.append(metadata)
        
    # 6. Re-Generate Index
    logger.info("Regenerating Homepage...")
    
    # Calculate Stats
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(DOCS_DIR):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    
    size_mb = f"{total_size / (1024*1024):.1f} MB"
    last_updated = datetime.datetime.now().strftime("%d %b %Y, %H:%M")
    
    stats = {
        'last_updated': last_updated,
        'archive_size': size_mb,
        'count': len(all_metadata)
    }
    
    generate_index(all_metadata, os.path.join(DOCS_DIR, "index.html"), stats)
    copy_assets(DOCS_DIR)
    
    logger.info("Done! All archives updated.")

if __name__ == "__main__":
    apply_changes()
