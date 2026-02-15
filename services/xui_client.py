import requests
import logging
import json
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class XUIClient:
    def __init__(self, host: str, port: int, username: str, password: str, root_path: str = ""):
        self.base_url = f"{host}:{port}"
        # Normalize root path: ensure it starts with / and has no trailing /
        self.root_path = root_path.strip()
        if self.root_path and not self.root_path.startswith('/'):
            self.root_path = '/' + self.root_path
        if self.root_path.endswith('/'):
            self.root_path = self.root_path[:-1]
            
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.logged_in = False

    def login(self) -> bool:
        """
        Authenticates with the 3x-ui panel.
        """
        url = f"{self.base_url}{self.root_path}/login"
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
        url = f"{self.base_url}{self.root_path}/panel/api/inbounds/list"
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

    def get_inbound(self, inbound_id: int) -> Optional[Dict]:
        """
        Retrieves a specific inbound by ID.
        """
        self._ensure_login()
        url = f"{self.base_url}{self.root_path}/panel/api/inbounds/get/{inbound_id}"
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200 and response.json().get('success'):
                return response.json().get('obj')
            return None
        except Exception as e:
            logger.error(f"Error fetching inbound {inbound_id}: {e}")
            return None

    def add_client(self, inbound_id: int, email: str, uuid: str, enable: bool = True) -> Dict:
        """
        Adds a client to an existing inbound.
        """
        self._ensure_login()
        url = f"{self.base_url}{self.root_path}/panel/api/inbounds/addClient"
        
        # Structure for adding a client
        # We need to respect the flow of the inbound, but for VLESS Vision it's explicit.
        # Ideally we fetch the inbound first to get the flow, but that's an extra call.
        # Let's assume standard X-UI structure.
        
        settings = {
            "clients": [
                {
                    "id": uuid,
                    "email": email,
                    "enable": enable,
                    "expiryTime": 0,
                    "limitIp": 0,
                    "totalGB": 0,
                    "flow": "xtls-rprx-vision", # Default for Reality, but ideally should match inbound
                }
            ]
        }
        
        data = {
            "id": inbound_id,
            "settings": json.dumps(settings)
        }
        
        try:
            response = self.session.post(url, data=data, timeout=10)
            logger.info(f"Add client response: {response.status_code} - {response.text}")
            result = response.json()
            if result.get('success'):
                return {"success": True, "msg": "Client added"}
            else:
                return {"success": False, "msg": result.get('msg', 'Unknown error')}
        except Exception as e:
            logger.error(f"Error adding client: {e}")
            return {"success": False, "msg": str(e)}

    def generate_vless_link(self, inbound: Dict, uuid: str, email: str, host_ip: str) -> str:
        """
        Generates a VLESS link based on inbound settings.
        """
        try:
            port = inbound['port']
            stream_settings = json.loads(inbound['streamSettings'])
            network = stream_settings.get('network', 'tcp')
            security = stream_settings.get('security', 'none')
            
            link = f"vless://{uuid}@{host_ip}:{port}?type={network}&security={security}"
            
            # Add reality/tls settings
            if security == 'reality':
                reality = stream_settings.get('realitySettings', {})
                pbk = reality.get('settings', {}).get('publicKey') # MHSanaei structure
                if not pbk: 
                    pbk = reality.get('privateKey') # Fallback if structure differs or if we are mistakenly reading private
                    # Actually typically: realitySettings: { settings: { publicKey: ... }, ... }
                    # Or direct fields dependent on version. 
                    # Let's try to find publicKey in realitySettings directly or nested
                    pbk = reality.get('publicKey') or reality.get('settings', {}).get('publicKey')

                sni = reality.get('serverNames', [''])[0]
                fp = reality.get('fingerprint', 'chrome')
                sid = reality.get('shortIds', [''])[0]
                
                link += f"&pbk={pbk}&fp={fp}&sni={sni}&sid={sid}&flow=xtls-rprx-vision"
            
            link += f"#{email}"
            return link
        except Exception as e:
            logger.error(f"Error generating link: {e}")
            return f"Error generating link: {e}"

    def delete_inbound(self, inbound_id: int) -> bool:
        """
        Deletes an inbound by ID.
        """
        self._ensure_login()
        url = f"{self.base_url}{self.root_path}/panel/api/inbounds/del/{inbound_id}"
        try:
            response = self.session.post(url, timeout=10)
            return response.json().get('success', False)
        except Exception as e:
            logger.error(f"Error deleting inbound: {e}")
            return False

    def delete_client_by_uuid(self, client_uuid: str) -> Dict:
        """
        Deletes a client by UUID. 
        First finds the inbound containing the client, then deletes the client.
        """
        self._ensure_login()
        
        # 1. Find Inbound and Client Email based on UUID
        inbounds = self.get_inbounds()
        target_inbound_id = None
        target_email = None
        
        for inbound in inbounds:
            try:
                settings = json.loads(inbound.get('settings', '{}'))
                clients = settings.get('clients', [])
                for client in clients:
                    if client.get('id') == client_uuid:
                        target_inbound_id = inbound.get('id')
                        target_email = client.get('email')
                        break
            except Exception:
                continue
            
            if target_inbound_id:
                break
                
        if not target_inbound_id:
            return {"success": False, "msg": "Client with this UUID not found."}
            
        # 2. Delete Client
        # Strategy A: /panel/api/inbounds/delClient/{inboundId}/{clientUuid}
        url_a = f"{self.base_url}{self.root_path}/panel/api/inbounds/delClient/{target_inbound_id}/{client_uuid}"
        try:
            logger.info(f"Attempting delete via {url_a}")
            response = self.session.post(url_a, timeout=10)
            logger.info(f"Delete response A: {response.status_code} - {response.text}")
            
            if response.status_code == 200 and response.json().get('success'):
                 return {"success": True, "msg": "Client deleted (Method A)"}
        except Exception as e:
            logger.warning(f"Delete Method A failed: {e}")

        # Strategy B: Remove from settings and update inbound
        # This is the fallback if the specific delete endpoint doesn't work/exist in this version
        try:
            logger.info(f"Attempting delete via Update Inbound (Method B)")
            # Re-fetch inbound to be sure
            inbound = self.get_inbound(target_inbound_id) # Need to implement get_inbound or find it again
            # For now, iterate again or use the one we found if we trust it hasn't changed in sub-second
            # Let's just use the 'inbound' variable from the loop above? No, it's safer to re-find exactly.
            
            # Simple re-find logic from list
            inbounds = self.get_inbounds()
            target_inbound = None
            for i in inbounds:
                if i.get('id') == target_inbound_id:
                    target_inbound = i
                    break
            
            if not target_inbound:
                 return {"success": False, "msg": "Inbound not found for fallback delete."}

            settings = json.loads(target_inbound.get('settings', '{}'))
            clients = settings.get('clients', [])
            
            # Filter out the client
            new_clients = [c for c in clients if c.get('id') != client_uuid]
            
            if len(new_clients) == len(clients):
                 return {"success": False, "msg": "Client not found in inbound settings."}
                 
            settings['clients'] = new_clients
            target_inbound['settings'] = json.dumps(settings)
            
            # Update inbound
            update_url = f"{self.base_url}{self.root_path}/panel/api/inbounds/update/{target_inbound_id}"
            resp = self.session.post(update_url, json=target_inbound, timeout=10)
            logger.info(f"Delete response B: {resp.status_code} - {resp.text}")
            
            if resp.status_code == 200 and resp.json().get('success'):
                return {"success": True, "msg": "Client deleted (Method B)"}
            else:
                return {"success": False, "msg": f"Failed Method B: {resp.text}"}

        except Exception as e:
            logger.error(f"Error deleting client (Method B): {e}")
            return {"success": False, "msg": str(e)}
