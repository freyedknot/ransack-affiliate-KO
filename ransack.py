import requests
import time
import re
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

def smart_subscribe(email):
    """Try to find the actual form endpoint"""
    print(f"[*] Attempting to subscribe {email}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # First, get the main page to find form action
    try:
        resp = requests.get("https://newsletter.chrisjkoerner.com", headers=headers, timeout=10)
        if resp.status_code == 200:
            # Look for form action in HTML
            import re
            match = re.search(r'<form[^>]+action="([^"]+)"', resp.text)
            if match:
                form_url = match.group(1)
                if not form_url.startswith("http"):
                    form_url = "https://newsletter.chrisjkoerner.com" + form_url
                
                # Submit the form
                data = {"email": email}
                post_resp = requests.post(form_url, data=data, headers=headers, timeout=10)
                if post_resp.status_code in [200, 302, 201]:
                    print("[+] Subscribed successfully via form endpoint")
                    return True
    except Exception as e:
        print(f"[-] Error during form detection: {e}")
    
    # Fallback: try common newsletter endpoints
    endpoints = [
        "https://newsletter.chrisjkoerner.com/subscribe",
        "https://newsletter.chrisjkoerner.com/api/subscribe",
        "https://chrisjkoerner.com/subscribe"
    ]
    for url in endpoints:
        try:
            r = requests.post(url, data={"email": email}, headers=headers, timeout=5)
            if r.status_code < 400:
                print(f"[+] Subscribed via {url}")
                return True
        except:
            continue
    
    print("[-] All subscription attempts failed. Manual signup may be required.")
    return False

# ---------- MAIN RANSACK ----------
def ransack():
    print(f"[*] Ransack started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    email, session, sid_token = get_disposable_email()
    print(f"[+] Disposable email: {email}")
    
    with open("target_email.txt", "w") as f:
        f.write(email)
    
    smart_subscribe(email)
    
    last_id = 0
    all_emails = []
    
    for hour in range(168):  # 7 days
        print(f"[*] Hour {hour+1}/168 checking inbox...")
        
        new_emails, last_id = check_inbox(session, sid_token, last_id)
        for email_obj in new_emails:
            full = read_full_email(session, email_obj.get('mail_id'), sid_token)
            if full:
                email_data = {
                    "timestamp": datetime.now().isoformat(),
                    "subject": email_obj.get('mail_subject'),
                    "from": email_obj.get('mail_from'),
                    "body": full.get('mail_body', '')[:5000]
                }
                all_emails.append(email_data)
                print(f"[!] Captured: {email_data['subject']}")
        
        with open("ransack_results.json", "w") as f:
            json.dump(all_emails, f, indent=2)
        
        with open("ransack_report.txt", "w", encoding="utf-8") as f:
            f.write(f"KOERNER RANSACK REPORT\nTarget email: {email}\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for e in all_emails:
                f.write(f"Subject: {e['subject']}\nFrom: {e['from']}\nTime: {e['timestamp']}\n{e['body']}\n\n{'-'*40}\n\n")
        
        time.sleep(3600)
    
    print("[*] Ransack complete!")

if __name__ == "__main__":
    ransack()
