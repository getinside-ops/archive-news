
import html
import json
import logging
import os
import shutil
import sys
from datetime import datetime
from email.utils import parsedate_to_datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.imap_client import EmailFetcher
from src.parser import EmailParser
from src.generator import generate_viewer, generate_index

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# CONFIG
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD")
TARGET_LABEL = os.environ.get("GMAIL_LABEL", "Github/archive-newsletters")
OUTPUT_FOLDER = "docs"
BATCH_SIZE = 9999
FORCE_UPDATE = os.environ.get("FORCE_UPDATE", "false").lower() == "true"


def process_emails():
    if not GMAIL_USER or not GMAIL_PASSWORD:
        logger.error("Missing credentials: set GMAIL_USER and GMAIL_PASSWORD env vars.")
        sys.exit(1)

    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    # 1. Connect
    fetcher = EmailFetcher(GMAIL_USER, GMAIL_PASSWORD, TARGET_LABEL)
    try:
        fetcher.connect()
        ids = fetcher.search_all()
        ids.reverse() # Process newest first
        logger.info("Found %d emails.", len(ids))
        
        # 2. Sync / Phase 1
        email_map = fetcher.fetch_headers(ids)
        
        # 3. Process
        all_metadata = []
        failure_count = 0

        for f_id, num in list(email_map.items())[:BATCH_SIZE]:
            folder_path = os.path.join(OUTPUT_FOLDER, f_id)
            meta_path = os.path.join(folder_path, "metadata.json")

            if os.path.exists(meta_path) and not FORCE_UPDATE:
                logger.info("Skipping %s (already archived).", f_id)
                with open(meta_path, 'r', encoding='utf-8') as f:
                    all_metadata.append(json.load(f))
                continue

            try:
                logger.info("Processing %s...", f_id)
                os.makedirs(folder_path, exist_ok=True)

                msg = fetcher.fetch_full_message(num)

                # Extract HTML and attachments
                html_payload = None
                text_payload = None
                attachments = {} # {cid: bytes}

                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        cdisp = str(part.get('Content-Disposition'))
                        cid = part.get('Content-ID')

                        if ctype.lower() == "text/html":
                            html_payload = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace')
                        elif ctype.lower() == "text/plain" and 'attachment' not in cdisp:
                             text_payload = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace')
                        elif cid:
                            # It's an inline attachment (like an image with CID)
                            clean_cid = cid.strip("<>")
                            attachments[clean_cid] = part.get_payload(decode=True)
                        elif 'attachment' in cdisp:
                            # It's a regular attachment
                            filename = part.get_filename()
                            if filename:
                                attachments[filename] = part.get_payload(decode=True)
                else:
                    ctype = msg.get_content_type()
                    if ctype == "text/html":
                        html_payload = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='replace')
                    elif ctype == "text/plain":
                        text_payload = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='replace')

                # Fallback to text/plain if no HTML
                if not html_payload and text_payload:
                    logger.warning("%s has no HTML body — converting text/plain.", f_id)
                    html_payload = f"<html><body><pre style='white-space: pre-wrap; font-family: monospace;'>{html.escape(text_payload)}</pre></body></html>"

                if not html_payload:
                    logger.warning("Skipping %s: no content found.", f_id)
                    continue

                # Extract Headers for CRM detection
                headers_dict = {k: v for k, v in msg.items()}

                # PARSE
                parser = EmailParser(html_payload, folder_path, headers=headers_dict, attachments=attachments)
                parser.detect_crm()  # Detect CRM using headers + content
                parser.clean_and_process()
                parser.resolve_redirects_parallel()
                parser.download_images_parallel()

                # Extract Date from headers
                date_str = msg.get('Date')
                if date_str:
                    try:
                        dt = parsedate_to_datetime(date_str)
                        date_rec = dt.strftime('%d/%m/%Y à %H:%M')
                        date_iso = dt.isoformat()
                    except Exception:
                        date_rec = date_str
                        date_iso = datetime.now().isoformat()
                else:
                    date_rec = datetime.now().strftime('%d/%m/%Y à %H:%M')
                    date_iso = datetime.now().isoformat()

                # Metadata structure
                metadata = {
                    'id': f_id,
                    'subject': fetcher.get_decoded_subject(msg),
                    'date_rec': date_rec,
                    'date_iso': date_iso,
                    'sender': EmailFetcher.get_decoded_sender(msg),
                    'date_arch': datetime.now().strftime('%d/%m/%Y à %H:%M'),
                    'preheader': parser.preheader,
                    'reading_time': parser.reading_time,
                    'audit': parser.audit,
                    'crm': parser.detected_crm
                }

                # Subject Length Audit
                subj_len = len(metadata['subject'])
                if subj_len < 10: metadata['audit']['subject_check'] = "Too Short"
                elif subj_len > 60: metadata['audit']['subject_check'] = "Too Long"
                else: metadata['audit']['subject_check'] = "Good"

                # Save metadata for index
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=4)

                all_metadata.append(metadata)

                generate_viewer(
                    metadata,
                    parser.get_html(),
                    parser.links,
                    os.path.join(folder_path, "index.html"),
                    detected_pixels=parser.detected_pixels
                )

            except Exception as e:
                logger.error("Error processing %s: %s. Skipping.", f_id, e)
                failure_count += 1
            
        # 4. Generate Main Index
        # Sort by date ISO (descending)
        all_metadata.sort(key=lambda x: x.get('date_iso', ''), reverse=True)
        logger.info("Generating index...")
        
        # Calculate Stats
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(OUTPUT_FOLDER):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        
        size_mb = f"{total_size / (1024*1024):.1f} MB"
        last_updated = datetime.now().strftime("%d %b %Y, %H:%M")
        
        stats = {
            'last_updated': last_updated,
            'archive_size': size_mb,
            'count': len(all_metadata)
        }

        generate_index(all_metadata, os.path.join(OUTPUT_FOLDER, "index.html"), stats)
        
        logger.info("Done!")

        # 5. Copy Assets
        from src.generator import copy_assets
        copy_assets(OUTPUT_FOLDER)
        logger.info("Assets copied.")

        if failure_count > 0:
            logger.warning("%d email(s) failed to process.", failure_count)
            sys.exit(1)

    finally:
        fetcher.close()

def _extract_email_html_from_viewer(viewer_path):
    """Extract the email HTML content from an existing viewer index.html."""
    import re
    with open(viewer_path, 'r', encoding='utf-8') as f:
        text = f.read()
    m = re.search(r'const content = ("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')', text, re.DOTALL)
    if not m:
        return None
    return json.loads(m.group(1))


def regen_only():
    """Re-render all viewer pages from existing index.html + metadata.json, no IMAP needed."""
    if not os.path.exists(OUTPUT_FOLDER):
        logger.error("docs/ folder not found.")
        sys.exit(1)

    from src.generator import generate_viewer, generate_index, copy_assets

    all_metadata = []
    for entry in sorted(os.listdir(OUTPUT_FOLDER)):
        meta_path = os.path.join(OUTPUT_FOLDER, entry, "metadata.json")
        viewer_path = os.path.join(OUTPUT_FOLDER, entry, "index.html")
        if not os.path.exists(meta_path):
            continue
        with open(meta_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        all_metadata.append(metadata)

        if os.path.exists(viewer_path):
            html_content = _extract_email_html_from_viewer(viewer_path)
            if html_content:
                links = metadata.get('audit', {}).get('links', [])
                detected_pixels = metadata.get('audit', {}).get('pixels', [])
                generate_viewer(metadata, html_content, links, viewer_path, detected_pixels=detected_pixels)
                logger.info("Re-rendered %s", entry)
            else:
                logger.warning("Could not extract email HTML from %s — skipping", entry)
        else:
            logger.warning("No index.html for %s — skipping", entry)

    all_metadata.sort(key=lambda x: x.get('date_iso', ''), reverse=True)

    total_size = sum(
        os.path.getsize(os.path.join(dp, f))
        for dp, _, files in os.walk(OUTPUT_FOLDER)
        for f in files
        if not os.path.islink(os.path.join(dp, f))
    )
    stats = {
        'last_updated': datetime.now().strftime("%d %b %Y, %H:%M"),
        'archive_size': f"{total_size / (1024*1024):.1f} MB",
        'count': len(all_metadata)
    }
    generate_index(all_metadata, os.path.join(OUTPUT_FOLDER, "index.html"), stats)
    copy_assets(OUTPUT_FOLDER)
    logger.info("Done — %d viewers re-rendered.", len(all_metadata))


def check_new_emails():
    """Quick check: compare IMAP message count vs. archived count.
    Exits 0 if new emails exist, exits 2 if nothing to process."""
    if not GMAIL_USER or not GMAIL_PASSWORD:
        logger.error("Missing credentials: set GMAIL_USER and GMAIL_PASSWORD env vars.")
        sys.exit(1)

    fetcher = EmailFetcher(GMAIL_USER, GMAIL_PASSWORD, TARGET_LABEL)
    try:
        fetcher.connect()
        imap_count = len(fetcher.search_all())
        archived_count = sum(
            1 for d in os.listdir(OUTPUT_FOLDER)
            if os.path.isfile(os.path.join(OUTPUT_FOLDER, d, "metadata.json"))
        ) if os.path.exists(OUTPUT_FOLDER) else 0

        if imap_count > archived_count:
            logger.info("IMAP: %d emails, archived: %d → %d new. Running pipeline.",
                        imap_count, archived_count, imap_count - archived_count)
            sys.exit(0)
        else:
            logger.info("IMAP: %d emails, archived: %d → nothing new. Skipping.",
                        imap_count, archived_count)
            sys.exit(2)
    finally:
        fetcher.close()


if __name__ == "__main__":
    if "--regen-only" in sys.argv:
        regen_only()
    elif "--check-new" in sys.argv:
        check_new_emails()
    else:
        process_emails()
