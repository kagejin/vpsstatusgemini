from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from utils.auth import restricted

@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["🖥 System Status", "⚡ X-UI Panel"],
        ["🏓 Ping Home", "❓ Help"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("🤖 VPS Manager Bot Ready.\nSelect an option:", reply_markup=reply_markup)

@restricted
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "<b>Commands:</b>\n"
        "/start - Show main menu\n"
        "/ping <IP> - Ping specific IP\n"
        "\n"
        "<b>Features:</b>\n"
        "🖥 <b>System Status</b>: Check CPU/RAM and Services.\n"
        "⚡ <b>X-UI Panel</b>: Manage VPN users."
    )
    await update.message.reply_text(msg, parse_mode='HTML')
