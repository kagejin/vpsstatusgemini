import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_IDS = [int(x.strip()) for x in os.getenv("ALLOWED_IDS", "").split(",") if x.strip()]

XUI_HOST = os.getenv("XUI_HOST", "http://127.0.0.1")
XUI_PORT = int(os.getenv("XUI_PORT", "2053"))
XUI_USER = os.getenv("XUI_USERNAME", "admin")
XUI_PASS = os.getenv("XUI_PASSWORD", "admin")

HOME_IP = os.getenv("HOME_IP", "")
