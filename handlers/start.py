"""start.py"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from handlers.keyboards import main_menu_keyboard
from services.database import clear_user_state, get_active_order_for_user

logger = logging.getLogger(__name__)

WELCOME = (
    "سلام! 👋\n\n"
    "به ربات فروش جزوه <b>Asli Education</b> خوش آمدید.\n\n"
    "🎓 نسخه <b>PDF دیجیتال</b> ریاضی ۳ پرومکس\n\n"
    "با خرید:\n"
    "• فایل کامل PDF را دریافت می‌کنید\n"
    "• با <b>لینک اختصاصی یک‌بارمصرف</b> وارد گروه VIP حل سؤالات ویدیویی می‌شوید\n\n"
    "از منوی زیر انتخاب کنید:"
)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"/start user={user.id}")
    active = await get_active_order_for_user(user.id)
    if active:
        from handlers.order import show_active_order_info
        await show_active_order_info(update, context, active)
        return
    await clear_user_state(user.id)
    await update.message.reply_text(WELCOME, parse_mode="HTML", reply_markup=main_menu_keyboard())
