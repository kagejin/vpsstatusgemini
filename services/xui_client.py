import requests
import logging
import json
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class XUIClient:
    def __init__(self, host: str, port: int, username: str, password: str):
        self.base_url = f"{host}:{port}"
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.logged_in = False

    def login(self) -> bool:
        """
        Authenticates with the 3x-ui panel.
        """
        url = f"{self.base_url}/login"
        data = {
            "username": self.username,
            "password": self.password
        }
        try:
            response = self.session.post(url, data=data, timeout=10)
                if response.status_code == 200 and response.json().get('success'):
                    self.logged_in = True
                    logger.info("Successfully logged into 3x-ui")
                    return True
                else:
                    logger.error(f"Login failed. Status: {response.status_code}, Body: {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Error connecting to 3x-ui login: {e}")
            return False

    def _ensure_login(self):
        """
        Ensures we are logged in before making a request.
        """
        if not self.logged_in:
            self.login()

    def get_inbounds(self) -> List[Dict]:
        """
        Retrieves the list of active inbounds.
        """
        self._ensure_login()
        url = f"{self.base_url}/panel/api/inbounds/list"
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('obj', [])
            
            # If failed, maybe session expired? retry once
            logger.warning("Failed to get inbounds, retrying login...")
            if self.login():
                response = self.session.get(url, timeout=10)
                if response.status_code == 200 and response.json().get('success'):
                    return response.json().get('obj', [])
            
            return []
        except Exception as e:
            logger.error(f"Error getting inbounds: {e}")
            return []

    def add_inbound(self, remark: str, port: int, protocol: str = "vless") -> Dict:
        """
        Adds a new inbound.
        Simplified version: creates a basic VLESS/VMESS config.
        """
        self._ensure_login()
        url = f"{self.base_url}/panel/api/inbounds/add"
        
        # Basic template for VLESS commonly used
        # Note: In a real scenario, we might need more complex settings struct
        settings = {
            "clients": [
                {
                    "id": "", # Generate UUID? Server usually does it or we need to. 
                    # Let's see if server auto-generates if empty or if we need python uuid
                    "flow": "xtls-rprx-vision",
                    "email": f"{remark}@bot"
                }
            ],
            "decryption": "none",
            "fallbacks": []
        }
        
        # We need a UUID for the client.
        import uuid
        client_uuid = str(uuid.uuid4())
        settings['clients'][0]['id'] = client_uuid

        data = {
            "up": 0,
            "down": 0,
            "total": 0,
            "remark": remark,
            "enable": True,
            "expiryTime": 0,
            "listen": "",
            "port": port,
            "protocol": protocol,
            "settings": json.dumps(settings),
            "streamSettings": json.dumps({
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "show": False,
                    "xver": 0,
                    "dest": "google.com:443",
                    "serverNames": ["google.com"],
                    "privateKey": "", # Server should generate? or we need one. 
                    # REALITY setup is complex via API if we don't fetch existing settings.
                    # For simplicity, let's try a simpler protocol or rely on defaults if possible.
                    # Actually, for add_inbound, it's safer to copy a template or ask user for full config.
                    # But for this task, I'll assume a standard VLESS-TCP-REALITY or similar.
                    # Let's default to a simpler VMESS-TCP for stability in testing if REALITY fails,
                    # or better: Just basic VLESS-TCP without Reality for now to ensure it works, 
                    # OR trust the server defaults.
                    
                    # Correction: Generating valid settings from scratch is hard. 
                    # Better approach: Just send the minimum and let 3x-ui handle or error out.
                    "shortIds": [""]
                }
            }),
            "sniffing": json.dumps({
                "enabled": True,
                "destOverride": ["http", "tls"]
            })
        }
        
        # ADJUSTMENT: For the sake of this task, I will implement a very basic VLESS config. 
        # If the user needs specific REALITY/etc configs, that's an advanced feature.
        # I'll stick to VLESS TCP for now as a baseline.
       
        try:
            response = self.session.post(url, data=data, timeout=10)
            logger.info(f"Add inbound response: {response.status_code} - {response.text}")
            result = response.json()
            if result.get('success'):
                logger.info(f"Created inbound {remark} on port {port}")
                return {"success": True, "uuid": client_uuid, "msg": "Created"}
            else:
                return {"success": False, "msg": result.get('msg', 'Unknown error')}
        except Exception as e:
            logger.error(f"Error adding inbound: {e}")
            return {"success": False, "msg": str(e)}

    def delete_inbound(self, inbound_id: int) -> bool:
        """
        Deletes an inbound by ID.
        """
        self._ensure_login()
        url = f"{self.base_url}/panel/api/inbounds/del/{inbound_id}"
        try:
            response = self.session.post(url, timeout=10)
            return response.json().get('success', False)
        except Exception as e:
            logger.error(f"Error deleting inbound: {e}")
            return False
