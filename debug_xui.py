import requests
import os
from dotenv import load_dotenv

load_dotenv()

XUI_HOST = os.getenv("XUI_HOST", "http://127.0.0.1")
XUI_PORT = os.getenv("XUI_PORT", "2053")
XUI_USER = os.getenv("XUI_USERNAME", "admin")
XUI_PASS = os.getenv("XUI_PASSWORD", "admin")
XUI_ROOT = os.getenv("XUI_ROOT", "")

# Normalize root path
root_path = XUI_ROOT.strip()
if root_path and not root_path.startswith('/'):
    root_path = '/' + root_path
if root_path.endswith('/'):
    root_path = root_path[:-1]

BASE_URL = f"{XUI_HOST}:{XUI_PORT}{root_path}"

print("🔍 X-UI Debug Tool")
print(f"Connecting to: {BASE_URL}")
print(f"User: {XUI_USER}, Pass: {'*' * len(XUI_PASS)}")

try:
    login_url = f"{BASE_URL}/login"
    data = {"username": XUI_USER, "password": XUI_PASS}
    
    print(f"\nAttempts POST {login_url}...")
    session = requests.Session()
    resp = session.post(login_url, data=data, timeout=10)
    
    print(f"Response Code: {resp.status_code}")
    print(f"Response Headers: {resp.headers}")
    print(f"Response Body (first 200 chars): {resp.text[:200]}")
    
    if resp.status_code == 200 and resp.json().get('success'):
        print("✅ LOGIN SUCCESS!")
        
        inbounds_url = f"{BASE_URL}/panel/api/inbounds/list"
        print(f"\nChecking Inbounds: {inbounds_url}...")
        resp2 = session.get(inbounds_url)
        print(f"Inbounds Response Code: {resp2.status_code}")
        print(f"Inbounds Body: {resp2.text[:200]}")
    else:
        print("❌ LOGIN FAILED (Check URL or Credentials)")
        
except Exception as e:
    print(f"❌ CRITICAL ERROR: {e}")
