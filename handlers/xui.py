from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from utils.auth import restricted
from services.xui_client import XUIClient
from config import XUI_HOST, XUI_PORT, XUI_USER, XUI_PASS, XUI_ROOT, HOME_IP
import uuid
import json

# Initialize client
xui_client = XUIClient(XUI_HOST, XUI_PORT, XUI_USER, XUI_PASS, XUI_ROOT)

@restricted
async def xui_help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["👥 List Users", "➕ Add User"],
        ["❌ Delete User", "🔙 Back"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("⚡ <b>X-UI Management Panel</b>\nSelect an action:", reply_markup=reply_markup, parse_mode='HTML')

import logging
logger = logging.getLogger(__name__)

def bytes_to_readable(bytes_val):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.2f} PB"

@restricted
async def list_users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("Fetching users...")
    inbounds = xui_client.get_inbounds()
    
    if not inbounds:
        await msg.edit_text("No users found or connection failed.")
        return

    text = "📂 <b>Active Users:</b>\n\n"
    found_users = False
    
    for inbound in inbounds:
        try:
            settings_str = inbound.get('settings', '{}')
            settings = json.loads(settings_str)
            clients = settings.get('clients', [])
            
            for client in clients:
                found_users = True
                email = client.get('email', 'No Name')
                uuid_str = client.get('id')
                enable = client.get('enable', True)
                status = "✅" if enable else "🔴"
                
                up = client.get('up', 0)
                down = client.get('down', 0)
                usage_str = bytes_to_readable(up + down)
                
                # Escape all dynamic data for HTML
                import html
                escaped_email = html.escape(email)
                escaped_usage = html.escape(usage_str)
                
                # Format: Name | Usage | Status
                # Action: /link_{uuid}
                text += f"{status} <b>{escaped_email}</b>\n"
                text += f"📊 {escaped_usage} | ID: {inbound.get('id')}\n"
                text += f"🔗 Get Link: /link_{uuid_str}\n\n"
                
        except Exception as e:
            logger.error(f"Error parsing inbound {inbound.get('id')}: {e}")
            
    if not found_users:
        text = "No clients found in any inbound."
        
    # Telegram message limit check
    if len(text) > 4000:
        text = text[:4000] + "\n... (truncated)"

    await msg.edit_text(text, parse_mode='HTML')

@restricted
async def get_user_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles /link_<uuid> commands to fetch VLESS link on demand.
    """
    try:
        command = update.message.text
        # Format: /link_UUID
        if not command.startswith("/link_"):
            return
            
        uuid_str = command.split("/link_")[1].strip()
        
        msg = await update.message.reply_text("Fetching link...")
        
        result = xui_client.find_client_by_uuid(uuid_str)
        if not result:
            await msg.edit_text("❌ Client not found.")
            return
            
        inbound, client = result
        email = client.get('email', 'No Name')
        
        # Generate Link
        host_ip = HOME_IP if HOME_IP else "YOUR_IP"
        link = xui_client.generate_vless_link(inbound, uuid_str, email, host_ip)
        
        import html
        escaped_link = html.escape(link)
        
        await msg.edit_text(
            f"🔗 <b>Link for {email}:</b>\n\n"
            f"<code>{escaped_link}</code>",
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error generating link: {e}")
        await update.message.reply_text("❌ Error generating link.")

@restricted
async def add_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /add <name>")
        return
    
    name = context.args[0]
    msg = await update.message.reply_text(f"Adding user '{name}'...")
    
    # 1. Find a suitable inbound (prefer vless/vmess)
    inbounds = xui_client.get_inbounds()
    target_inbound = None
    if inbounds:
        for i in inbounds:
            if i.get('protocol') in ['vless', 'vmess']:
                target_inbound = i
                break
        if not target_inbound:
             target_inbound = inbounds[0]
    
    if not target_inbound:
        await msg.edit_text("❌ No inbounds found. Please create an inbound in the panel first.")
        return

    inbound_id = target_inbound.get('id')
    client_uuid = str(uuid.uuid4())
    
    # 2. Add client to inbound
    result = xui_client.add_client(inbound_id, name, client_uuid)
    
    if result['success']:
        # 3. Generate Link
        # Use configured HOME_IP or fallback to 'YOUR_IP'
        host_ip = HOME_IP if HOME_IP else "YOUR_IP"
        
        link = xui_client.generate_vless_link(target_inbound, client_uuid, name, host_ip)
        
        await msg.edit_text(
            f"✅ User <b>{name}</b> added to Inbound {inbound_id}!\n"
            f"UUID: <code>{client_uuid}</code>\n\n"
            f"🔗 <b>Link:</b>\n<code>{link}</code>\n\n"
            f"<i>Link generated using IP: {host_ip}</i>\n"
            f"<i>(Set HOME_IP in .env to fix IP)</i>",
            parse_mode='HTML'
        )
    else:
        await msg.edit_text(f"❌ Failed: {result['msg']}")

@restricted
async def del_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /del <uuid>")
        return
    
    client_uuid = context.args[0]
        
    msg = await update.message.reply_text(f"Deleting user with UUID {client_uuid}...")
    result = xui_client.delete_client_by_uuid(client_uuid)
    
    if result['success']:
        await msg.edit_text(f"✅ User deleted successfully.")
    else:
        await msg.edit_text(f"❌ Failed to delete: {result['msg']}")
