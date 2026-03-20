
import imaplib
import email
import hashlib
import logging
import re
import time
from email.header import decode_header
from email.utils import parseaddr

logger = logging.getLogger(__name__)

class EmailFetcher:
    def __init__(self, user, password, label):
        self.user = user
        self.password = password
        self.label = label
        self.mail = None

    def connect(self):
        logger.info("Connecting to Gmail...")
        last_err = None
        for attempt in range(3):
            try:
                self.mail = imaplib.IMAP4_SSL("imap.gmail.com")
                self.mail.login(self.user, self.password)
                rv, _ = self.mail.select(f'"{self.label}"')
                if rv != 'OK':
                    logger.error("Label %s not found. Listing available labels:", self.label)
                    status, labels = self.mail.list()
                    if status == 'OK':
                        for label in labels:
                            logger.error(" - %s", label.decode('utf-8'))
                    raise Exception(f"Label {self.label} not found")
                return
            except Exception as e:
                last_err = e
                if attempt < 2:
                    logger.warning("IMAP connect attempt %d failed: %s. Retrying in 5s...", attempt + 1, e)
                    time.sleep(5)
        raise last_err

    def search_all(self):
        status, messages = self.mail.search(None, 'ALL')
        if not messages[0]:
            return []
        return messages[0].split()

    def fetch_headers(self, email_ids):
        """
        Fetch basic headers for synchronization (Phase 1)
        Returns: Dict {deterministic_id: valid_msg_num}
        """
        email_map = {}
        for num in email_ids:
            try:
                # Fetch Subject, Date and Message-ID for better uniqueness
                status, msg_data = self.mail.fetch(num, '(BODY.PEEK[HEADER.FIELDS (SUBJECT DATE MESSAGE-ID)])')
                msg_header = email.message_from_bytes(msg_data[0][1])
                
                subject = self.get_decoded_subject(msg_header)
                date_header = msg_header.get("Date", "")
                msg_id = msg_header.get("Message-ID", "")
                
                clean_subj = self._clean_subject_prefixes(subject)
                # Combine subject with date and msg_id for uniqueness
                f_id = self._get_deterministic_id(clean_subj, date_header, msg_id)
                email_map[f_id] = num
            except Exception as e:
                logger.warning("Error fetching headers for msg %s: %s", num, e)
        return email_map

    def fetch_full_message(self, num):
        status, msg_data = self.mail.fetch(num, '(RFC822)')
        return email.message_from_bytes(msg_data[0][1])

    def close(self):
        if self.mail:
            try:
                if self.mail.state == 'SELECTED':
                    self.mail.close()
            except Exception:
                pass
            try:
                self.mail.logout()
            except Exception:
                pass

    # --- HELPERS ---
    @staticmethod
    def get_decoded_subject(msg):
        subject_header = msg.get("Subject", "")
        if not subject_header: return "Untitled"
        decoded_list = decode_header(subject_header)
        full_subject = ""
        for part, encoding in decoded_list:
            if isinstance(part, bytes):
                full_subject += part.decode(encoding or "utf-8", errors="ignore")
            else:
                full_subject += str(part)
        return full_subject.strip()

    @staticmethod
    def get_decoded_sender(msg):
        """Decode and clean sender name from email headers."""
        from_header = msg.get("From", "")
        if not from_header:
            return "Unknown"
        
        # Decode MIME encoded-word format
        decoded_parts = decode_header(from_header)
        decoded_str = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_str += part.decode(encoding or "utf-8", errors="ignore")
            else:
                decoded_str += str(part)
        
        # Extract only the friendly name, not the email address
        name, addr = parseaddr(decoded_str)
        return name.strip('"').strip() if name else addr

    def _clean_subject_prefixes(self, subject):
        if not subject: return "Untitled"
        pattern = r'^\s*\[?(?:Fwd|Fw|Tr|Re|Aw|Wg)\s*:\s*\]?\s*'
        cleaned = subject
        while re.match(pattern, cleaned, re.IGNORECASE):
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    def _get_deterministic_id(self, subject, date_str="", msg_id=""):
        if not subject: subject = "sans_titre"
        # We combine subject, date and msg_id for high uniqueness
        combined = f"{subject}|{date_str}|{msg_id}"
        hash_object = hashlib.sha256(combined.encode('utf-8', errors='ignore'))
        return hash_object.hexdigest()[:12]
