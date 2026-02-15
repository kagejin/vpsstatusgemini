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
                
                # Generate Link
                host_ip = HOME_IP if HOME_IP else "YOUR_IP"
                link = xui_client.generate_vless_link(inbound, uuid_str, email, host_ip)
                
                text += f"{status} <b>{email}</b> (ID: {inbound.get('id')})\n"
                text += f"📊 Usage: {usage_str}\n"
                text += f"🔗 Link: <code>{link}</code>\n\n"
                
        except Exception as e:
            logger.error(f"Error parsing inbound {inbound.get('id')}: {e}")
            
    if not found_users:
        text = "No clients found in any inbound."
        
    # Telegram message limit check (rough)
    if len(text) > 4000:
        text = text[:4000] + "\n... (truncated)"

    await msg.edit_text(text, parse_mode='HTML')

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
        await update.message.reply_text("Usage: /del <id>")
        return
    
    try:
        inbound_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID must be a number.")
        return
        
    msg = await update.message.reply_text(f"Deleting ID {inbound_id}...")
    success = xui_client.delete_inbound(inbound_id)
    
    if success:
        await msg.edit_text(f"✅ Inbound {inbound_id} deleted.")
    else:
        await msg.edit_text("❌ Failed to delete. Check ID or logs.")
