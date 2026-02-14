from telegram import Update
from telegram.ext import ContextTypes
from utils.auth import restricted
from services.xui_client import XUIClient
from config import XUI_HOST, XUI_PORT, XUI_USER, XUI_PASS

# Initialize client
xui_client = XUIClient(XUI_HOST, XUI_PORT, XUI_USER, XUI_PASS)

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
    msg = await update.message.reply_text(f"Creating user '{name}'...")
    
    # Auto-assign port? Simple logic for now: Random or let server decide? 
    # 3x-ui usually needs explicit port.
    # Let's pick a random port between 10000-60000 for simplicity or ask user.
    # For now, let's use a random port.
    import random
    port = random.randint(10000, 60000)
    
    result = xui_client.add_inbound(name, port)
    
    if result['success']:
        await msg.edit_text(
            f"✅ User <b>{name}</b> created!\n"
            f"Port: {port}\n"
            f"UUID: <code>{result.get('uuid')}</code>\n\n"
            f"<i>Link generation not implemented in V1</i>",
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
