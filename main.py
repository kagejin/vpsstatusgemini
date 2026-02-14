import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from config import TOKEN
from utils.logger import setup_logger
from handlers.general import start, help_command
from handlers.system import ping_command, system_status_handler
from handlers.xui import xui_help_handler, list_users_handler, add_user_handler, del_user_handler

def main():
    setup_logger()
    
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
        return

    application = ApplicationBuilder().token(TOKEN).build()

    # General
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # System
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(MessageHandler(filters.Regex("^🖥 System Status$"), system_status_handler))
    
    # X-UI
    application.add_handler(MessageHandler(filters.Regex("^⚡ X-UI Panel$"), xui_help_handler))
    application.add_handler(CommandHandler("users", list_users_handler))
    application.add_handler(CommandHandler("add", add_user_handler))
    application.add_handler(CommandHandler("del", del_user_handler))

    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
