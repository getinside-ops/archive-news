import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import mimetypes
import re
import zipfile
import io
import os

# Configuration de la page
st.set_page_config(page_title="Newsletter Injector", page_icon="💉")

st.title("💉 Injecteur de Newsletter (Version +)")
st.markdown("Cet outil permet d'envoyer manuellement du HTML brut ou un fichier ZIP à votre archive.")

# Récupération des secrets
default_user = st.secrets["GMAIL_USER"] if "GMAIL_USER" in st.secrets else ""
default_pass = st.secrets["GMAIL_PASSWORD"] if "GMAIL_PASSWORD" in st.secrets else ""

upload_type = st.radio("Type d'import", ["Code HTML", "Fichier ZIP (.zip comprenant html + images)"])

with st.form("email_form", clear_on_submit=False):
    col1, col2 = st.columns(2)
    with col1:
        user_email = st.text_input("Votre Gmail (Expéditeur)", value=default_user)
        app_password = st.text_input("Mot de passe d'application", type="password", value=default_pass)
    
    with col2:
        dest_email = st.text_input("Envoyer à (Adresse Archive)", value=default_user)
    
    st.write("---")
    subject = st.text_input("Sujet de la Newsletter")
    
    html_content = ""
    zip_file = None
    base_url = ""
    
    if upload_type == "Code HTML":
        base_url = st.text_input("URL d'origine (Recommandé)", placeholder="ex: https://...", 
                                 help="Indispensable pour que les liens et images distantes fonctionnent.")
        html_content = st.text_area("Collez le Code HTML (OuterHTML) ici", height=300)
    else:
        zip_file = st.file_uploader("Choisissez un fichier ZIP", type="zip")
        st.info("Le ZIP doit contenir un fichier .html et les images associées au même niveau ou dans des sous-dossiers.")

    submitted = st.form_submit_button("🚀 Envoyer l'archive")

if submitted:
    if not user_email or not app_password or not subject:
        st.error("Veuillez remplir tous les champs obligatoires (Email, Mot de passe, Sujet).")
    elif upload_type == "Code HTML" and not html_content:
        st.error("Veuillez coller le code HTML.")
    elif upload_type == "Fichier ZIP (.zip comprenant html + images)" and not zip_file:
        st.error("Veuillez uploader un fichier ZIP.")
    else:
        try:
            with st.spinner("Traitement et envoi..."):
                attachments = []
                
                if upload_type == "Fichier ZIP (.zip comprenant html + images)":
                    with zipfile.ZipFile(zip_file) as z:
                        # Find the main HTML file
                        html_files = [f for f in z.namelist() if f.endswith('.html')]
                        if not html_files:
                            st.error("Aucun fichier .html trouvé dans le ZIP.")
                            st.stop()
                        
                        # Use index.html if present, else first html
                        main_html_file = "index.html" if "index.html" in html_files else html_files[0]
                        html_content = z.read(main_html_file).decode('utf-8', errors='ignore')
                        
                        soup = BeautifulSoup(html_content, "html.parser")
                        
                        # Process images in ZIP
                        cid_count = 0
                        for img_tag in soup.find_all('img', src=True):
                            src = img_tag['src']
                            # If it's a local reference (not a URL)
                            if not src.startswith(('http://', 'https://', 'data:', '//')):
                                # Normalize path in ZIP
                                img_path = os.path.normpath(os.path.join(os.path.dirname(main_html_file), src)).replace('\\', '/')
                                if img_path in z.namelist():
                                    mime_type, _ = mimetypes.guess_type(img_path)
                                    if not mime_type or not mime_type.startswith('image/'):
                                        continue  # Skip non-image files
                                    img_data = z.read(img_path)
                                    # Create a unique CID using a counter
                                    basename = os.path.basename(img_path)
                                    cid_name = f"cid_{cid_count}_{basename}"
                                    cid_count += 1
                                    # Update HTML to use CID
                                    img_tag['src'] = f"cid:{cid_name}"
                                    # Prepare attachment
                                    attachments.append((cid_name, img_data))
                        
                        html_content = str(soup)
                else:
                    # Traitement HTML classique
                    soup = BeautifulSoup(html_content, "html.parser")
                    lazy_attrs = ['data-src', 'data-original', 'data-lazy', 'data-url']
                    
                    for img in soup.find_all("img"):
                        for attr in lazy_attrs:
                            if img.get(attr):
                                img['src'] = img[attr]
                                del img[attr]
                                break
                        
                        if img.get('srcset'):
                            first_url = img['srcset'].split(',')[0].split(' ')[0]
                            if not img.get('src'):
                                img['src'] = first_url
                            del img['srcset']

                    if base_url:
                        for img in soup.find_all("img", src=True):
                            if not img["src"].startswith("data:"):
                                if img["src"].startswith("//"):
                                    img["src"] = "https:" + img["src"]
                                else:
                                    img["src"] = urljoin(base_url, img["src"])

                        for a in soup.find_all("a", href=True):
                            a["href"] = urljoin(base_url, a["href"])
                        
                        for tag in soup.find_all(True, background=True):
                            tag["background"] = urljoin(base_url, tag["background"])

                        for tag in soup.find_all(style=True):
                            style = tag['style']
                            if 'url(' in style:
                                def replace_css_url(match):
                                    url_content = match.group(1).strip("'").strip('"')
                                    if not url_content.startswith("data:"):
                                        if url_content.startswith("//"):
                                            new_url = "https:" + url_content
                                        else:
                                            new_url = urljoin(base_url, url_content)
                                        return f"url('{new_url}')"
                                    return match.group(0)
                                
                                new_style = re.sub(r"url\((.*?)\)", replace_css_url, style)
                                tag['style'] = new_style

                    html_content = str(soup)

                # Construction de l'email
                msg = MIMEMultipart("related")
                msg["Subject"] = subject
                msg["From"] = user_email
                msg["To"] = dest_email
                
                msg_alternative = MIMEMultipart("alternative")
                msg.attach(msg_alternative)
                
                part = MIMEText(html_content, "html")
                msg_alternative.attach(part)
                
                # Attach CID images
                for filename, data in attachments:
                    img = MIMEImage(data)
                    img.add_header('Content-ID', f'<{filename}>')
                    img.add_header('Content-Disposition', 'inline', filename=filename)
                    msg.attach(img)
                
                server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
                server.login(user_email, app_password)
                server.sendmail(user_email, dest_email, msg.as_string())
                server.quit()
                
            st.success(f"✅ Newsletter '{subject}' envoyée avec succès !")
            st.balloons()
            
        except Exception as e:
            st.error(f"Erreur lors de l'envoi : {e}")
            st.exception(e)
