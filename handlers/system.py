from telegram import Update
from telegram.ext import ContextTypes
from utils.auth import restricted
from services.system_monitor import ping_host, check_service_status, get_system_stats

@restricted
async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /ping <IP>")
        return
    
    ip = context.args[0]
    msg = await update.message.reply_text(f"Pinging {ip}...")
    result = ping_host(ip)
    await msg.edit_text(result)

@restricted
async def system_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = get_system_stats()
    
    # Check services
    services = ["3x-ui", "docker", "ssh"] # customizable
    service_status = "\n\n🛠 **Services**:\n"
    for s in services:
        active = check_service_status(s)
        service_status += f"{'✅' if active else '🔴'} {s}\n"
        
    await update.message.reply_text(stats + service_status, parse_mode='Markdown')
