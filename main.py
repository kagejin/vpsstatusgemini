import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from config import TOKEN
from utils.logger import setup_logger
from handlers.general import start, help_command
from handlers.system import system_status_handler
from handlers.xui import xui_help_handler, list_users_handler, add_user_handler, del_user_handler

def main():
    setup_logger()
    
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
        return

    application = ApplicationBuilder().token(TOKEN).read_timeout(30).write_timeout(30).connect_timeout(30).build()

    # General
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # System
    # Conversation Handler for Ping
    from telegram.ext import ConversationHandler
    PING_STATE = 1
    
    async def start_ping(update, context):
        await update.message.reply_text("Please enter the IP address or Hostname to ping:", parse_mode='Markdown')
        return PING_STATE

    async def handle_ping_input(update, context):
        ip = update.message.text
        msg = await update.message.reply_text(f"Pinging {ip} (10 packets)... please wait.")
        # Run ping with count=10
        from services.system_monitor import ping_host
        result = ping_host(ip, count=10)
        await msg.edit_text(result)
        return ConversationHandler.END

    async def cancel_ping(update, context):
        await update.message.reply_text("Ping cancelled.")
        return ConversationHandler.END

    ping_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🏓 Ping$"), start_ping),
            CommandHandler("ping", start_ping) # Also allow /ping to start flow
        ],
        states={
            PING_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ping_input)]
        },
        fallbacks=[CommandHandler("cancel", cancel_ping)]
    )

    application.add_handler(ping_conv_handler)
    application.add_handler(MessageHandler(filters.Regex("^🖥 System Status$"), system_status_handler))
    
    # X-UI
    # X-UI
    application.add_handler(MessageHandler(filters.Regex("^⚡ X-UI Panel$"), xui_help_handler))
    application.add_handler(MessageHandler(filters.Regex("^👥 List Users$"), list_users_handler))
    application.add_handler(MessageHandler(filters.Regex("^🔙 Back$"), start))
    
    async def add_prompt(update, context):
        await update.message.reply_text("To add a user, send:\n`/add <name>`", parse_mode='Markdown')
        
    async def del_prompt(update, context):
        await update.message.reply_text("To delete a user, send:\n`/del <id>`\n(Find ID in 'List Users')", parse_mode='Markdown')

    application.add_handler(MessageHandler(filters.Regex("^➕ Add User$"), add_prompt))
    application.add_handler(MessageHandler(filters.Regex("^❌ Delete User$"), del_prompt))

    application.add_handler(CommandHandler("users", list_users_handler))
    application.add_handler(CommandHandler("add", add_user_handler))
    application.add_handler(CommandHandler("del", del_user_handler))

    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
