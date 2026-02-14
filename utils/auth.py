from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
import logging
from ..config import ALLOWED_IDS

logger = logging.getLogger(__name__)

def restricted(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ALLOWED_IDS:
            logger.warning(f"Unauthorized access attempt from {user_id} ({update.effective_user.username})")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped
