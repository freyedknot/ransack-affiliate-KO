import requests
import time
import re
import os
import json
from datetime import datetime

# ---------- DISPOSABLE EMAIL ----------
def get_disposable_email():
    session = requests.Session()
    resp = session.get("https://api.guerrillamail.com/ajax.php?f=get_email_address")
    if resp.status_code != 200:
        raise Exception("Failed to get disposable email")
    data = resp.json()
    email = data.get("email_addr")
    sid_token = data.get("sid_token")
    return email, session, sid_token

def check_inbox(session, sid_token, last_id=0):
    resp = session.get(f"https://api.guerrillamail.com/ajax.php?f=get_email_list&sid_token={sid_token}")
    if resp.status_code != 200:
        return [], last_id
    emails = resp.json().get("list", [])
    new_emails = [e for e in emails if int(e.get("mail_id", 0)) > last_id]
    if new_emails:
        last_id = max(int(e.get("mail_id", 0)) for e in emails)
    return new_emails, last_id

def read_full_email(session, email_id, sid_token):
    resp = session.get(f"https://api.guerrillamail.com/ajax.php?f=fetch_email&email_id={email_id}&sid_token={sid_token}")
    if resp.status_code != 200:
        return None
    return resp.json()

def subscribe_http_only(email):
    """HTTP-only subscribe (no browser needed for GitHub Actions)"""
    print(f"[*] Subscribing with {email} via HTTP request...")
    
    # Try common form endpoints
    urls = [
        "https://newsletter.chrisjkoerner.com/subscribe",
        "https://newsletter.chrisjkoerner.com/api/subscribe",
        "https://chrisjkoerner.com/subscribe"
    ]
    
    data = {
        "email": email,
        "submit": "Subscribe"
    }
    
    for url in urls:
        try:
            resp = requests.post(url, data=data, timeout=10)
            if resp.status_code in [200, 302]:
                print(f"[+] Successfully subscribed via {url}")
                return True
        except:
            continue
    
    print("[-] HTTP subscribe failed — will rely on manual or next step")
    return False

# ---------- MAIN RANSACK ----------
def ransack():
    print(f"[*] Ransack started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    email, session, sid_token = get_disposable_email()
    print(f"[+] Disposable email: {email}")
    
    # Save email to file so we can see it
    with open("target_email.txt", "w") as f:
        f.write(email)
    
    # Try to subscribe
    subscribe_http_only(email)
    
    # Monitor for 7 days
    last_id = 0
    all_emails = []
    
    for hour in range(168):  # 7 days * 24 hours
        print(f"[*] Hour {hour+1}/168 checking inbox...")
        
        new_emails, last_id = check_inbox(session, sid_token, last_id)
        for email_obj in new_emails:
            full = read_full_email(session, email_obj.get('mail_id'), sid_token)
            if full:
                email_data = {
                    "timestamp": datetime.now().isoformat(),
                    "subject": email_obj.get('mail_subject'),
                    "from": email_obj.get('mail_from'),
                    "body": full.get('mail_body', '')[:5000]  # Truncate for GitHub
                }
                all_emails.append(email_data)
                print(f"[!] Captured: {email_data['subject']}")
        
        # Save progress every hour
        with open("ransack_results.json", "w") as f:
            json.dump(all_emails, f, indent=2)
        
        # Also save as readable text
        with open("ransack_report.txt", "w", encoding="utf-8") as f:
            f.write(f"KOERNER RANSACK REPORT\n")
            f.write(f"Target email: {email}\n")
            f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*60 + "\n\n")
            for e in all_emails:
                f.write(f"Subject: {e['subject']}\n")
                f.write(f"From: {e['from']}\n")
                f.write(f"Time: {e['timestamp']}\n")
                f.write("-"*40 + "\n")
                f.write(e['body'] + "\n\n")
                f.write("="*60 + "\n\n")
        
        time.sleep(3600)  # Wait 1 hour between checks
    
    print("[*] Ransack complete!")

if __name__ == "__main__":
    ransack()
