
from bs4 import BeautifulSoup
import html
import json
import logging
import mimetypes
import os
import re
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urljoin

logger = logging.getLogger(__name__)

TRACKING_PATTERNS = [
    "api.getinside.media", "google-analytics.com", "doubleclick.net", "facebook.com/tr",
    "criteo.com", "matomo", "pixel.gif", "analytics", "tracking", "open.aspx",
    "hs-analytics.net", "hubspot.com", "marketo.com", "pardot.com"
]

# CRM Detection Patterns
CRM_PATTERNS = {
    'Mailchimp': ['list-manage.com', 'mailchimp.com', 'mc.us', 'mcusercontent.com', 'campaign-archive.com'],
    'Brevo': ['sibforms.com', 'sendinblue.com', 'brevo.com', 'sib.com'],
    'Klaviyo': ['klaviyo.com', 'klclick.com', 'kclick.com'],
    'Mailjet': ['mailjet.com', 'mjt.lu'],
    'HubSpot': ['hubspot.com', 'hs-analytics.net', 'hubspotemail.net', 'hsforms.com'],
    'Salesforce': ['salesforce.com', 'exacttarget.com', 'sfmc-content.com', 'igodigital.com'],
    'Oracle Responsys': ['responsys.net', 'rsys2.com', 'rsys5.com'],
    'Braze': ['braze.com', 'appboy.com'],
    'ActiveCampaign': ['activecampaign.com', 'activehosted.com', 'acems.com'],
    'Adobe Marketo': ['marketo.com', 'mktotrack.com'],
    'Dotdigital': ['dotdigital.com', 'dotmailer.com', 'dmptrk.com'],
    'Campaign Monitor': ['createsend.com', 'cmail'],
    'MailerLite': ['mailerlite.com', 'mlsend.com'],
    'SendPulse': ['sendpulse.com', 'sendpulse.me'],
    'Moosend': ['moosend.com'],
    'Emma': ['myemma.com', 'e2ma.net'],
    'Listrak': ['listrak.com', 'listrakbi.com'],
    'Sailthru': ['sailthru.com'],
    'Bluecore': ['bluecore.com'],
    'Mad Mimi': ['madmimi.com'],
    'iContact': ['icontact.com'],
    'AWeber': ['aweber.com'],
    'Postmark': ['postmarkapp.com', 'pstmrk.it'],
    'Sendgrid': ['sendgrid.net', 'sendgrid.com'],
    'Sarbacane': ['sarbacane.com', 'sbc'],
    'Splio': ['splio.com'],
    'Dolist': ['dolist.com', 'dolist.net'],
    'Shopify': ['shopify.com', 'shopifyemail.com'],
}

RESOLVE_REDIRECTS = True
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    'Sec-Fetch-Dest': 'image',
    'Sec-Fetch-Mode': 'no-cors',
    'Sec-Fetch-Site': 'cross-site',
}


def _http_get(url, retries=3, timeout=10, referer=None):
    """GET with exponential backoff (1s, 2s, 4s) on transient failures."""
    delays = [1, 2, 4]
    last_err = None
    req_headers = dict(HEADERS)
    if referer:
        req_headers['Referer'] = referer
    for attempt in range(retries):
        try:
            return requests.get(url, headers=req_headers, timeout=timeout)
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(delays[attempt])
    raise last_err

def _strip_outer_wrapper(raw_html):
    """Strip simple outer HTML wrapper (e.g. added by Gmail/SMTP relay) when body contains a full email HTML."""
    # Only check the beginning to avoid expensive full-string scan
    if re.search(r'<body[^>]*>\s*(?:<!DOCTYPE|<html\b)', raw_html[:2000], re.IGNORECASE):
        inner = re.search(r'<body[^>]*>(.*)</body\s*>', raw_html, re.DOTALL | re.IGNORECASE)
        if inner:
            return inner.group(1).strip()
    return raw_html


class EmailParser:
    def __init__(self, raw_html, output_folder, headers=None, attachments=None):
        raw_html = _strip_outer_wrapper(raw_html)
        self._raw_html = raw_html
        self.soup = BeautifulSoup(raw_html, "html.parser")
        self.output_folder = output_folder
        self.headers = headers or {}
        self.attachments = attachments or {} # {cid: bytes_content}
        self.links = []
        self.detected_pixels = []
        self.detected_crm = None
        # Source URL forwarded by the Streamlit injector via X-Source-URL.
        # Used as the Referer when localizing images so ESP CDNs (e.g. news.but.fr)
        # don't 403 hot-link attempts.
        self.source_url = (self.headers.get('X-Source-URL') or self.headers.get('x-source-url') or '').strip() or None
        self.failed_images = []

    def detect_crm(self):
        """Detect which CRM/ESP was used to send this email by analyzing URLs and headers."""
        
        # 1. Check Headers (Most reliable)
        header_mapping = {
            'X-Mailer': {
                'Mailchimp': 'mailchimp',
                'Brevo': 'brevo',
                'Sendinblue': 'sendinblue',
                'Mailjet': 'mailjet',
                'Klaviyo': 'klaviyo',
                'HubSpot': 'hubspot',
                'Salesforce': 'salesforce',
                'ActiveCampaign': 'activecampaign',
                'Shopify': 'shopify'
            },
            'X-Report-Abuse-To': {
                'Mailchimp': 'mcsv.net',
                'Brevo': 'brevo',
                'Sendinblue': 'sendinblue'
            },
            'List-Unsubscribe': {
                'Mailchimp': 'list-manage.com',
                'Brevo': 'brevo',
                'Klaviyo': 'klclick',
                'HubSpot': 'hubspot',
                'Shopify': 'shopifyemail'
            }
        }

        for header_key, mapping in header_mapping.items():
            val = str(self.headers.get(header_key, '')).lower()
            if val:
                for crm_name, marker in mapping.items():
                    if marker in val:
                        self.detected_crm = crm_name
                        return crm_name

        # 2. Check URLs as fallback
        all_urls = []
        for a in self.soup.find_all('a', href=True):
            all_urls.append(a['href'].lower())
        for img in self.soup.find_all('img', src=True):
            all_urls.append(img['src'].lower())
        
        # Priority check for specific strong markers
        for url in all_urls:
            if 'shopifyemail.com' in url or 'shopify.com' in url:
                self.detected_crm = 'Shopify'
                return 'Shopify'
            if 'klclick.com' in url or 'klaviyo' in url:
                self.detected_crm = 'Klaviyo'
                return 'Klaviyo'
            if 'mcsv.net' in url or 'list-manage.com' in url:
                self.detected_crm = 'Mailchimp'
                return 'Mailchimp'

        # Generic pattern check
        for crm_name, patterns in CRM_PATTERNS.items():
            for pattern in patterns:
                for url in all_urls:
                    if pattern in url:
                        # Extra validation: if it's sendgrid/amazonses, only set if nothing else found
                        if crm_name in ['Sendgrid', 'Amazon SES'] and self.detected_crm:
                            continue
                        self.detected_crm = crm_name
                        return crm_name
        
        return None

    def _extract_mso_blocks(self):
        """Return (mso_blocks, not_mso_blocks) — lists of inner HTML from conditional comments.

        We extract only the content between the <!--[if mso]> and <![endif]--> markers,
        so it can be re-parsed by BeautifulSoup without being treated as a comment again.
        """
        mso = re.findall(
            r'<!--\[if\s+(?:gte\s+)?mso[^\]]*\]>(.*?)<!\[endif\]-->',
            self._raw_html, flags=re.DOTALL | re.IGNORECASE
        )
        not_mso = re.findall(
            r'<!--\[if\s+!mso[^\]]*\]>(.*?)<!\[endif\]-->',
            self._raw_html, flags=re.DOTALL | re.IGNORECASE
        )
        return mso, not_mso

    def _pixel_warnings(self, src, img, mso_blocks, not_mso_blocks):
        """Return list of warning dicts describing why this pixel may not fire."""
        warnings = []

        if any(src in block for block in mso_blocks):
            warnings.append({
                'code': 'mso_block',
                'label': 'Dans un bloc [if mso]',
                'detail': 'Ce pixel n\'est chargé que par Microsoft Outlook. '
                          'Il est ignoré par tous les webmails (Gmail, Yahoo…), iOS Mail, Android et les navigateurs.',
                'fix': 'Sortir le pixel du bloc <!--[if mso]>…<![endif]--> et le placer '
                       'juste avant </body>, dans le flux HTML standard.'
            })

        if any(src in block for block in not_mso_blocks):
            warnings.append({
                'code': 'not_mso_block',
                'label': 'Dans un bloc [if !mso]',
                'detail': 'Ce pixel est masqué dans Outlook. Il ne se chargera pas chez les utilisateurs Outlook.',
                'fix': 'Sortir le pixel du bloc <!--[if !mso]>…<![endif]--> et le placer '
                       'dans le flux HTML standard.'
            })

        if src.startswith('http://'):
            warnings.append({
                'code': 'insecure_url',
                'label': 'URL en HTTP (non sécurisée)',
                'detail': 'Les contextes HTTPS (Gmail, Yahoo, iOS) bloquent les ressources HTTP. '
                          'Le pixel ne se chargera pas dans la majorité des clients modernes.',
                'fix': 'Remplacer http:// par https:// dans l\'URL du pixel.'
            })

        if src.startswith('//'):
            warnings.append({
                'code': 'protocol_relative',
                'label': 'URL protocole-relative (//',
                'detail': 'Certains clients email ne résolvent pas les URLs sans protocole explicite.',
                'fix': 'Remplacer // par https:// dans l\'URL du pixel.'
            })

        if img.get('width') == '0' or img.get('height') == '0':
            warnings.append({
                'code': 'zero_dimensions',
                'label': 'Dimensions 0×0',
                'detail': 'Certains clients filtrent les ressources de taille nulle et ne les chargent pas.',
                'fix': 'Utiliser width="1" height="1" à la place de 0×0.'
            })

        if img.find_parent('head'):
            warnings.append({
                'code': 'in_head',
                'label': 'Placé dans <head>',
                'detail': 'Certains clients email n\'exécutent pas les ressources déclarées dans le <head>.',
                'fix': 'Déplacer le pixel dans le <body>, juste avant </body>.'
            })

        if img.find_parent('noscript'):
            warnings.append({
                'code': 'noscript',
                'label': 'Dans <noscript>',
                'detail': 'Le contenu <noscript> ne s\'affiche que si JavaScript est désactivé. '
                          'La quasi-totalité des clients email ignorent cette balise.',
                'fix': 'Sortir le pixel du bloc <noscript> et le placer directement dans le <body>.'
            })

        if img.find_parent(style=re.compile(r'display\s*:\s*none', re.I)):
            warnings.append({
                'code': 'hidden_parent',
                'label': 'Conteneur masqué (display:none)',
                'detail': 'Le pixel est dans un élément CSS masqué. '
                          'Bien que display:none n\'empêche pas toujours le chargement, '
                          'certains clients optimisés ne chargent pas ces ressources.',
                'fix': 'Déplacer le pixel hors du conteneur masqué.'
            })

        def _is_preheader_container(tag):
            s = tag.get('style', '')
            return (re.search(r'(?:max-)?height\s*:\s*0', s, re.I)
                    and re.search(r'overflow\s*:\s*hidden', s, re.I))

        if img.find_parent(_is_preheader_container):
            warnings.append({
                'code': 'hidden_overflow',
                'label': 'Conteneur preheader (height:0 + overflow:hidden)',
                'detail': 'Le pixel est coincé dans le bloc preheader invisible. '
                          'Ce bloc a height:0 et overflow:hidden — le pixel ne se charge pas.',
                'fix': 'Déplacer le pixel hors du bloc preheader, juste avant </body>.'
            })

        return warnings

    def _scan_conditional_blocks_for_pixels(self, mso_blocks, not_mso_blocks):
        """Detect tracking pixels hidden inside MSO/not-mso conditional comment blocks.

        BeautifulSoup treats <!--[if mso]>...<![endif]--> as opaque Comment nodes,
        so img tags inside are invisible to find_all('img'). This method parses
        the raw block content independently and appends any found pixels to
        self.detected_pixels with the appropriate placement warning.
        """
        already_seen = {px['url'] for px in self.detected_pixels}

        for block_html, warning_code, warning_label, warning_detail, warning_fix in [
            (
                '\n'.join(mso_blocks),
                'mso_block',
                'Dans un bloc [if mso]',
                "Ce pixel n'est chargé que par Microsoft Outlook. "
                "Il est ignoré par tous les webmails (Gmail, Yahoo…), iOS Mail, Android et les navigateurs.",
                "Sortir le pixel du bloc <!--[if mso]>…<![endif]--> et le placer "
                "juste avant </body>, dans le flux HTML standard."
            ),
            (
                '\n'.join(not_mso_blocks),
                'not_mso_block',
                'Dans un bloc [if !mso]',
                "Ce pixel est masqué dans Outlook. Il ne se chargera pas chez les utilisateurs Outlook.",
                "Sortir le pixel du bloc <!--[if !mso]>…<![endif]--> et le placer "
                "dans le flux HTML standard."
            ),
        ]:
            if not block_html.strip():
                continue
            block_soup = BeautifulSoup(block_html, "html.parser")
            for img in block_soup.find_all("img"):
                src = img.get("src", "").strip()
                if not src or src in already_seen:
                    continue
                width = img.get("width", "")
                height = img.get("height", "")
                is_tracking = (
                    any(p in src for p in TRACKING_PATTERNS)
                    or (width == "1" and height == "1")
                )
                if not is_tracking:
                    continue
                try:
                    pixel_domain = urlparse(src).netloc.replace('www.', '')
                    if not pixel_domain:
                        continue
                except Exception:
                    continue
                already_seen.add(src)
                # Build full warning list: placement warning first, then URL-level checks
                w_placement = {
                    'code': warning_code,
                    'label': warning_label,
                    'detail': warning_detail,
                    'fix': warning_fix,
                }
                extra_warnings = self._pixel_warnings(src, img, [], [])  # URL checks only
                warnings = [w_placement] + extra_warnings
                self.detected_pixels.append({
                    'url': src,
                    'status': 'Problème détecté',
                    'domain': pixel_domain,
                    'is_gtinsi': 'gtinsi.de' in src,
                    'warnings': warnings,
                    'has_issues': True,
                })

    def clean_and_process(self):
        # 1. Pixel Detection & Cleanup
        mso_blocks, not_mso_blocks = self._extract_mso_blocks()
        for img in self.soup.find_all("img"):
            # Handle lazy-loading attributes BEFORE checking src
            # This ensures we capture the actual tracking URL
            for lazy_attr in ['data-src', 'data-original', 'data-url']:
                if img.get(lazy_attr):
                    img['src'] = img.get(lazy_attr)
                    break
            
            src = img.get("src", "")
            width = img.get("width")
            height = img.get("height")

            # Detect by pattern OR dimensions (1x1)
            reason = None
            if any(pattern in src for pattern in TRACKING_PATTERNS):
                reason = "Known Tracking Domain"
            elif width == "1" and height == "1":
                reason = "1x1 Pixel Dimensions"

            if reason:
                # Skip pixel if src is empty
                if not src:
                    img['src'] = ""
                    img['style'] = "display:none !important;"
                    continue
                
                # Extract domain; skip pixel if URL is unparseable
                try:
                    pixel_domain = urlparse(src).netloc.replace('www.', '')
                    # If domain is still empty after parsing, skip this pixel
                    if not pixel_domain:
                        img['src'] = ""
                        img['style'] = "display:none !important;"
                        continue
                except Exception:
                    img['src'] = ""
                    img['style'] = "display:none !important;"
                    continue

                # Check if pixel contains gtinsi.de
                is_gtinsi = 'gtinsi.de' in src

                warnings = self._pixel_warnings(src, img, mso_blocks, not_mso_blocks)
                self.detected_pixels.append({
                    'url': src,
                    'status': 'Problème détecté' if warnings else 'Integration: OK',
                    'domain': pixel_domain,
                    'is_gtinsi': is_gtinsi,
                    'warnings': warnings,
                    'has_issues': bool(warnings),
                })
                img['src'] = ""
                img['style'] = "display:none !important;"

        # Scan pixels hidden inside MSO conditional comment blocks (invisible to BS4)
        self._scan_conditional_blocks_for_pixels(mso_blocks, not_mso_blocks)

        # 2. Extract Preheader (Text approximation)
        # Strip invisible characters like zero-width joiners and spacing characters used in emails
        text = self.soup.get_text(separator=" ", strip=True)
        text = re.sub(r'[\u200b\u200c\u200d\u200e\u200f\ufeff\u2007\u034f\u2060\u2061\u2062\u2063\u2064\u206a\u206b\u206c\u206d\u206e\u206f]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        self.preheader = text[:160] + "..." if len(text) > 160 else text
        self.reading_time = f"{max(1, round(len(text.split()) / 200))} min"

        # 3. Process Links (Audit + List)
        link_idx = 0
        self.audit = {
            'subject_length': 0,
            'subject_check': 'OK',
            'unsubscribe_found': False,
            'link_count': 0,
            'images_no_alt': 0
        }
        
        # Link Audit
        for a in self.soup.find_all('a', href=True):
            link_idx += 1
            a['data-index'] = str(link_idx)
            original_url = a['href']
            
            # Domain Extraction
            domain = ""
            try:
                parsed = urlparse(original_url)
                domain = parsed.netloc.replace('www.', '')
            except Exception:
                pass

            # Tracking Check
            is_tracking = any(pattern in original_url.lower() for pattern in TRACKING_PATTERNS)
            
            # Security & Dev Audit
            is_secure = original_url.startswith('https://') or original_url.startswith('//')
            dev_patterns = ['test', 'staging', 'dev.', 'localhost', 'internal', 'bat.', 'preprod']
            is_dev = any(p in original_url.lower() for p in dev_patterns)

            # Unsubscribe check
            txt = a.get_text(strip=True).lower()
            if 'unsubscribe' in txt or 'désinscrire' in txt or 'opt-out' in txt or 'manage preferences' in txt:
                self.audit['unsubscribe_found'] = True

            self.links.append({
                'index': link_idx,
                'txt': a.get_text(strip=True)[:50],
                'original_url': original_url,
                'final_url': original_url,
                'domain': domain,
                'is_tracking': is_tracking,
                'is_secure': is_secure,
                'is_dev': is_dev
            })
            
        self.audit['link_count'] = link_idx
        
        # Image Alt Audit
        for img in self.soup.find_all('img'):
            if not img.get('alt') and img.get('style') != "display:none !important;":
                self.audit['images_no_alt'] += 1

            
    def download_images_parallel(self):
        images_to_download = []
        image_idx = 0
        for img in self.soup.find_all("img"):
            # Handle lazy attrs
            for attr in ['data-src', 'data-original', 'data-url']:
                if img.get(attr):
                    img['src'] = img.get(attr)
                    break
            
            src = img.get("src")
            if not src or src.startswith("data:"): continue
            
            # Special case for CID images
            if src.startswith("cid:"):
                cid = src.replace("cid:", "").strip("<>")
                if cid in self.attachments:
                    content = self.attachments[cid]
                    
                    # Detect extension from magic bytes
                    ext = ".jpg" # Default
                    if content.startswith(b'\x89PNG\r\n\x1a\n'):
                        ext = ".png"
                    elif content.startswith(b'GIF87a') or content.startswith(b'GIF89a'):
                        ext = ".gif"
                    elif content.startswith(b'\xff\xd8\xff'):
                        ext = ".jpg"
                    elif content.startswith(b'RIFF') and content[8:12] == b'WEBP':
                        ext = ".webp"
                    
                    local_name = f"img_{image_idx}{ext}"
                    image_idx += 1
                    path = os.path.join(self.output_folder, local_name)
                    with open(path, "wb") as f:
                        f.write(content)
                    img['src'] = local_name
                    continue # Already processed
                else:
                    logger.warning("CID %s not found in attachments.", cid)
                    continue

            if src.startswith("//"): src = "https:" + src
            # Only http(s) is fetchable. Browser DOM dumps (outerHTML copies)
            # often contain chrome-extension://, moz-extension://, blob:, etc.
            # injected by user extensions — skip silently so they don't pollute
            # failed_images.json or trigger a misleading viewer warning chip.
            if not (src.startswith("http://") or src.startswith("https://")):
                logger.debug("Skipping non-http image src: %s", src[:80])
                continue
            images_to_download.append((img, src, image_idx))
            image_idx += 1
            
        MAX_IMG_BYTES = 15 * 1024 * 1024

        def _image_origin(url):
            try:
                parsed = urlparse(url)
                if parsed.scheme and parsed.netloc:
                    return f"{parsed.scheme}://{parsed.netloc}/"
            except Exception:
                pass
            return None

        def _attempt(url, referer):
            r = _http_get(url, referer=referer)
            if not (200 <= r.status_code < 300):
                return r, None, f"http_{r.status_code}"
            ctype = (r.headers.get('content-type') or '').split(';')[0].strip().lower()
            if not ctype.startswith('image/'):
                return r, None, f"bad_content_type:{ctype or 'unknown'}"
            size = len(r.content)
            if size <= 0 or size > MAX_IMG_BYTES:
                return r, None, f"bad_size:{size}"
            ext = mimetypes.guess_extension(ctype) or ".jpg"
            return r, ext, None

        def _download(img_obj, url, idx):
            # Check for existing file with standard extensions (resume support)
            for ext in ['.jpg', '.png', '.gif', '.jpeg', '.webp']:
                potential_name = f"img_{idx}{ext}"
                potential_path = os.path.join(self.output_folder, potential_name)
                if os.path.exists(potential_path):
                    return img_obj, potential_name, None

            # Referer fallback chain: source URL → image origin → none
            referer_chain = []
            if self.source_url:
                referer_chain.append(self.source_url)
            origin = _image_origin(url)
            if origin and origin not in referer_chain:
                referer_chain.append(origin)
            referer_chain.append(None)

            last_reason = None
            last_referer = None
            for referer in referer_chain:
                try:
                    r, ext, reason = _attempt(url, referer)
                    last_reason = reason
                    last_referer = referer
                    if ext is None:
                        # 403 with a Referer often means the CDN rejects any cross-origin Referer.
                        # 429 → respect Retry-After once.
                        if r.status_code == 429:
                            retry_after = r.headers.get('Retry-After')
                            try:
                                time.sleep(min(float(retry_after), 5.0)) if retry_after else None
                            except Exception:
                                pass
                        continue
                    local_name = f"img_{idx}{ext}"
                    path = os.path.join(self.output_folder, local_name)
                    with open(path, "wb") as f:
                        f.write(r.content)
                    return img_obj, local_name, None
                except Exception as e:
                    last_reason = f"exception:{type(e).__name__}:{e}"
                    last_referer = referer
                    continue

            logger.warning("Image download failed for %s (referer=%s reason=%s)", url, last_referer, last_reason)
            return img_obj, None, {
                'url': url,
                'reason': last_reason or 'unknown',
                'referer_used': last_referer,
            }

        with ThreadPoolExecutor(max_workers=5) as ex:
            futures = {ex.submit(_download, item[0], item[1], item[2]): item for item in images_to_download}
            for f in as_completed(futures):
                img, local, failure = f.result()
                if local:
                    img['src'] = local
                elif failure:
                    self.failed_images.append(failure)

        if self.failed_images:
            try:
                fail_path = os.path.join(self.output_folder, 'failed_images.json')
                with open(fail_path, 'w', encoding='utf-8') as f:
                    json.dump(self.failed_images, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning("Could not write failed_images.json: %s", e)

    def resolve_redirects_parallel(self):
        """Pre-calculate redirect chains for all links to avoid CORS issues in the statics viewer."""
        if not RESOLVE_REDIRECTS or not self.links:
            return

        unique_urls = list(set(l['original_url'] for l in self.links))
        results_cache = {}

        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # One shared session per worker thread
        _extra_headers = {
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Upgrade-Insecure-Requests': '1',
        }

        def _make_session():
            s = requests.Session()
            s.headers.update(HEADERS)
            s.headers.update(_extra_headers)
            return s

        def _resolve(args):
            url, session = args
            chain = []
            try:
                current_url = url
                for _ in range(15):
                    try:
                        resp = session.get(current_url, allow_redirects=False, timeout=15)
                    except requests.exceptions.Timeout:
                        chain.append({'status': 'Timeout', 'url': current_url})
                        break
                    except Exception:
                        chain.append({'status': 'Error', 'url': current_url})
                        break

                    chain.append({'status': resp.status_code, 'url': current_url})

                    if 300 <= resp.status_code < 400 and 'Location' in resp.headers:
                        current_url = urljoin(current_url, resp.headers['Location'])
                    else:
                        break

                return {'chain': chain, 'date': now}

            except Exception as e:
                logger.warning("Error resolving %s: %s", url, e)
                return {'chain': [{'status': 'Error', 'url': url}], 'date': now}

        # Build (url, session) pairs — one session reused per worker
        n_workers = 10
        sessions = [_make_session() for _ in range(n_workers)]
        work = [(url, sessions[i % n_workers]) for i, url in enumerate(unique_urls)]

        with ThreadPoolExecutor(max_workers=n_workers) as ex:
            futures = {ex.submit(_resolve, item): item[0] for item in work}
            for f in as_completed(futures):
                url = futures[f]
                results_cache[url] = f.result()

        # Apply results back to links
        for link in self.links:
            url = link['original_url']
            if url in results_cache:
                res = results_cache[url]
                link['redirect_chain'] = res['chain']
                link['audit_date'] = res['date']
                if link['redirect_chain']:
                    link['final_url'] = link['redirect_chain'][-1]['url']

    def inject_base_target(self):
        """Inject <base target="_blank"> to make all links open in new tab."""
        base_tag = self.soup.new_tag('base', target='_blank')
        if self.soup.head:
            self.soup.head.insert(0, base_tag)
        else:
            # Create head if it doesn't exist
            head_tag = self.soup.new_tag('head')
            head_tag.insert(0, base_tag)
            if self.soup.html:
                self.soup.html.insert(0, head_tag)

    def get_html(self):
        self.inject_base_target()
        return str(self.soup)
