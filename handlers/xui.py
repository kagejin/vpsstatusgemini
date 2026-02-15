from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler
from utils.auth import restricted
from services.xui_client import XUIClient
from config import XUI_HOST, XUI_PORT, XUI_USER, XUI_PASS, XUI_ROOT, HOME_IP
import uuid
import json
import html

# Initialize client
xui_client = XUIClient(XUI_HOST, XUI_PORT, XUI_USER, XUI_PASS, XUI_ROOT)

@restricted
async def xui_help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["👥 List Users", "➕ Add User"],
        ["🔙 Back"]
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

    keyboard = []
    found_users = False
    
    for inbound in inbounds:
        try:
            settings = json.loads(inbound.get('settings', '{}'))
            clients = settings.get('clients', [])
            
            # Check for clientStats (3x-ui / MHSanaei often puts stats here)
            client_stats = {c.get('email'): c for c in inbound.get('clientStats', [])}
            
            for client in clients:
                found_users = True
                email = client.get('email', 'No Name')
                uuid_str = client.get('id')
                enable = client.get('enable', True)
                status_icon = "🟢" if enable else "🔴"
                
                # Check metrics in client object or clientStats
                up = client.get('up', 0)
                down = client.get('down', 0)
                
                # If 0, try clientStats
                if up == 0 and down == 0 and email in client_stats:
                    stat = client_stats[email]
                    up = stat.get('up', 0)
                    down = stat.get('down', 0)

                button_text = f"{status_icon} {email}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"xui_u_{uuid_str}")])
                
        except Exception as e:
            logger.error(f"Error parsing inbound {inbound.get('id')}: {e}")
            
    if not found_users:
        await msg.edit_text("No clients found in any inbound.")
        return
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await msg.edit_text("📂 <b>Select a User:</b>", reply_markup=reply_markup, parse_mode='HTML')


async def xui_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("xui_u_"):
        # Show User Details
        uuid_str = data.split("xui_u_")[1]
        
        result = xui_client.find_client_by_uuid(uuid_str)
        if not result:
            await query.edit_message_text("❌ Client not found (might have been deleted).")
            return
            
        inbound, client = result
        email = client.get('email', 'No Name')
        enable = client.get('enable', True)
        status = "Active 🟢" if enable else "Disabled 🔴"
        
        # Traffic Stats
        up = client.get('up', 0)
        down = client.get('down', 0)
        
        # Try clientStats if 0
        client_stats = {c.get('email'): c for c in inbound.get('clientStats', [])}
        if up == 0 and down == 0 and email in client_stats:
             stat = client_stats[email]
             up = stat.get('up', 0)
             down = stat.get('down', 0)
             
        total = up + down
        quota = client.get('totalGB', 0)
        
        stats_text = (
            f"👤 <b>User:</b> {html.escape(email)}\n"
            f"🆔 <b>UUID:</b> <code>{uuid_str}</code>\n"
            f"📡 <b>Status:</b> {status}\n\n"
            f"📊 <b>Traffic Usage:</b>\n"
            f"   🔼 Upload: {bytes_to_readable(up)}\n"
            f"   🔽 Download: {bytes_to_readable(down)}\n"
            f"   🔁 Total: {bytes_to_readable(total)}\n"
        )
        
        if quota > 0:
             stats_text += f"   ⛔ Quota: {bytes_to_readable(quota)}\n"
             
        keyboard = [
            [InlineKeyboardButton("🔗 Get Link", callback_data=f"xui_l_{uuid_str}")],
            [InlineKeyboardButton("❌ Delete User", callback_data=f"xui_d_{uuid_str}")],
            [InlineKeyboardButton("🔙 Back to List", callback_data="xui_list")]
        ]
        
        await query.edit_message_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        
    elif data.startswith("xui_l_"):
        # Get Link
        uuid_str = data.split("xui_l_")[1]
        result = xui_client.find_client_by_uuid(uuid_str)
        if not result:
            await query.message.reply_text("❌ Client not found.")
            return
            
        inbound, client = result
        email = client.get('email', 'No Name')
        host_ip = HOME_IP if HOME_IP else "YOUR_IP"
        
        link = xui_client.generate_vless_link(inbound, uuid_str, email, host_ip)
        escaped_link = html.escape(link)
        
        await query.message.reply_text(
            f"🔗 <b>Link for {html.escape(email)}:</b>\n<code>{escaped_link}</code>",
            parse_mode='HTML'
        )
        
    elif data.startswith("xui_d_"):
        # Delete User Confirmation
        uuid_str = data.split("xui_d_")[1]
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"xui_dc_{uuid_str}")],
            [InlineKeyboardButton("🚫 Cancel", callback_data=f"xui_u_{uuid_str}")]
        ]
        await query.edit_message_text("❓ <b>Are you sure you want to delete this user?</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    elif data.startswith("xui_dc_"):
        # Confirmed Delete
        uuid_str = data.split("xui_dc_")[1]
        
        await query.edit_message_text("⏳ Deleting...")
        result = xui_client.delete_client_by_uuid(uuid_str)
        
        if result['success']:
            await query.edit_message_text("✅ User deleted successfully.")
            # Optional: Redirect back to list?
        else:
            await query.edit_message_text(f"❌ Failed to delete: {result['msg']}")
            
    elif data == "xui_list":
        # Back to List - re-run list handler logic locally
        inbounds = xui_client.get_inbounds()
        if not inbounds:
             await query.edit_message_text("No users found.")
             return

        keyboard = []
        for inbound in inbounds:
            try:
                settings = json.loads(inbound.get('settings', '{}'))
                clients = settings.get('clients', [])
                 # Check for clientStats (3x-ui / MHSanaei often puts stats here)
                client_stats = {c.get('email'): c for c in inbound.get('clientStats', [])}

                for client in clients:
                    email = client.get('email', 'No Name')
                    uuid_str = client.get('id')
                    enable = client.get('enable', True)
                    status_icon = "🟢" if enable else "🔴"
                    keyboard.append([InlineKeyboardButton(f"{status_icon} {email}", callback_data=f"xui_u_{uuid_str}")])
            except: pass
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📂 <b>Select a User:</b>", reply_markup=reply_markup, parse_mode='HTML')

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
        host_ip = HOME_IP if HOME_IP else "YOUR_IP"
        link = xui_client.generate_vless_link(target_inbound, client_uuid, name, host_ip)
        import html
        escaped_link = html.escape(link)
        
        await msg.edit_text(
            f"✅ User <b>{html.escape(name)}</b> added!\n"
            f"UUID: <code>{client_uuid}</code>\n\n"
            f"🔗 <b>Link:</b>\n<code>{escaped_link}</code>",
            parse_mode='HTML'
        )
    else:
        await msg.edit_text(f"❌ Failed: {result['msg']}")
