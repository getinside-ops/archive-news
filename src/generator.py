
import datetime
import json
import os

import jinja2
from markupsafe import Markup

# Setup Jinja2 environment
TEMPLATE_DIR = os.path.join(os.getcwd(), 'templates')
env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATE_DIR),
    autoescape=jinja2.select_autoescape(['html', 'xml'])
)
def _format_date(d):
    """Parse an ISO 8601 date string and return DD/MM/YYYY, or return d unchanged."""
    if not d:
        return d
    try:
        return datetime.datetime.fromisoformat(d).strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        return d

env.globals.update(format_date=_format_date)

def generate_viewer(metadata, html_content, links, output_path, lang='fr', detected_pixels=[], audit={}):
    """
    Generates the viewer HTML using Jinja2 template.
    """
    template = env.get_template('viewer.html')
    
    # Calculate size for Gmail clipping warning
    email_size = len(html_content.encode('utf-8'))
    
    # Escape </script> to avoid breaking the viewer's script tag, then mark as safe for Jinja2
    safe_html_json = Markup(json.dumps(html_content).replace('</script>', r'<\/script>'))
    
    rendered_html = template.render(
        subject=metadata.get('subject', 'No Subject'),
        email_date=metadata.get('date_rec', ''),
        sender_name=metadata.get('sender', 'Unknown'),
        archiving_date=metadata.get('date_arch', ''),
        preheader=metadata.get('preheader', ''),
        reading_time=metadata.get('reading_time', ''),
        links=links,
        safe_html=safe_html_json,
        email_size=email_size,
        lang=lang,
        detected_pixels=detected_pixels,
        audit=metadata.get('audit', {}),
        crm=metadata.get('crm'),
        links_json=Markup(json.dumps(links).replace('</script>', r'<\/script>'))
    )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(rendered_html)
def generate_index(emails_metadata, output_path, stats=None):
    """
    Generates the main index.html landing page.
    """
    template = env.get_template('index.html')
    # Sort by date desc
    sorted_emails = sorted(emails_metadata, key=lambda x: x.get('date_iso', ''), reverse=True)
    
    rendered_html = template.render(
        emails=sorted_emails,
        stats=stats or {}
    )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(rendered_html)

def copy_assets(output_dir):
    """
    Copies static assets from src/assets to the output directory (docs/assets).
    Also copies the project-root fonts/ folder to docs/fonts/ for @font-face serving.
    """
    import shutil

    src_assets = os.path.join(os.path.dirname(__file__), 'assets')
    dest_assets = os.path.join(output_dir, 'assets')

    if os.path.exists(src_assets):
        if os.path.exists(dest_assets):
            shutil.rmtree(dest_assets)
        shutil.copytree(src_assets, dest_assets)

    src_fonts = os.path.join(os.getcwd(), 'fonts')
    dest_fonts = os.path.join(output_dir, 'fonts')
    if os.path.exists(src_fonts):
        if os.path.exists(dest_fonts):
            shutil.rmtree(dest_fonts)
        shutil.copytree(src_fonts, dest_fonts)
