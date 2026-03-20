import os
from src.imap_client import EmailFetcher

# CONFIG from environment or process_email.py defaults
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD")
TARGET_LABEL = os.environ.get("GMAIL_LABEL", "Github/archive-newsletters")

def debug_gmail():
    if not GMAIL_USER or not GMAIL_PASSWORD:
        print("Error: Missing credentials")
        return

    print("Connecting to Gmail...")
    fetcher = EmailFetcher(GMAIL_USER, GMAIL_PASSWORD, TARGET_LABEL)
    
    try:
        # 1. Connect and List Labels
        fetcher.mail = fetcher.connect_and_return_mail_obj() 
        # Note: connect() in imap_client doesn't return mail obj, but sets self.mail
        # Let's use the public connect() method from the original class
        fetcher.connect()
        
        print("\n--- Label Verification ---")
        status, labels = fetcher.mail.list()
        found_target = False
        if status == 'OK':
            for l in labels:
                decoded = l.decode('utf-8')
                if TARGET_LABEL in decoded:
                    print(f"FOUND TARGET: {decoded}")
                    found_target = True
                
        if not found_target:
             print(f"WARNING: '{TARGET_LABEL}' not explicitly found in list (might be exact match required).")

        # 2. Check Inbox Count
        print(f"\n--- Checking Messages in '{TARGET_LABEL}' ---")
        # connect() selects the label.
        ids = fetcher.search_all()
        print(f"Total Messages Found: {len(ids)}")
        
        # 3. List Last 10 headers
        print("\n--- Last 10 Messages (Headers) ---")
        if ids:
            last_10 = ids[-10:]
            email_map = fetcher.fetch_headers(last_10)
            
            # fetching headers returns a map, but we want to see the details we just fetched
            # Re-fetch individually to print diagnosis
            for num in last_10:
                print(f"Msg Num: {num.decode('utf-8')}")
                try:
                   status, msg_data = fetcher.mail.fetch(num, '(BODY.PEEK[HEADER.FIELDS (SUBJECT DATE FROM)])')
                   print(f"  Header Raw: {msg_data[0][1]}")
                except Exception as e:
                    print(f"  Error: {e}")
        else:
            print("No messages found.")

    except Exception as e:
        print(f"Debug Error: {e}")
    finally:
        fetcher.close()

if __name__ == "__main__":
    debug_gmail()
