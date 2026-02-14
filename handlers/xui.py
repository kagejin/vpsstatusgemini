from telegram import Update
from telegram.ext import ContextTypes
from utils.auth import restricted
from services.xui_client import XUIClient
from config import XUI_HOST, XUI_PORT, XUI_USER, XUI_PASS, XUI_ROOT, HOME_IP
import uuid

# Initialize client
xui_client = XUIClient(XUI_HOST, XUI_PORT, XUI_USER, XUI_PASS, XUI_ROOT)

@restricted
async def xui_help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "⚡ <b>X-UI Management</b>\n\n"
        "<b>Commands:</b>\n"
        "/users - List all active users\n"
        "/add &lt;name&gt; - Add new VLESS user\n"
        "/del &lt;id&gt; - Delete user by Inbound ID\n"
    )
    await update.message.reply_text(msg, parse_mode='HTML')

@restricted
async def list_users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("Fetching users...")
    inbounds = xui_client.get_inbounds()
    
    if not inbounds:
        await msg.edit_text("No users found or connection failed.")
        return

    text = "📂 <b>Active Users:</b>\n\n"
    for i in inbounds:
        # 3x-ui inbound structure varies, usually 'id' is DB ID, 'remark' is name
        # 'settings' has the UUID.
        # We display DB ID for deletion usage.
        text += f"🆔 <b>{i.get('id')}</b> | 👤 <b>{i.get('remark')}</b>\n"
        text += f"   Port: {i.get('port')} | Protocol: {i.get('protocol')}\n\n"
        
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
