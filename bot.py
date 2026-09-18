"""bot.py — ربات فروش PDF + VIP یک‌بارمصرف"""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters,
)

from config import BOT_TOKEN, DATA_DIR
from services.database import init_db
from handlers.start import start_handler
from handlers.order import (
    start_purchase_handler, text_message_handler, photo_message_handler,
    callback_confirm_purchase, callback_cancel_order, callback_send_receipt_info,
)
from handlers.admin import (
    admin_panel_handler, callback_admin_approve, callback_admin_reject,
    callback_reject_default, callback_reject_custom, callback_admin_msg_customer,
    callback_admin_back, callback_admin_help, admin_text_handler,
)

logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


async def unified_text(update: Update, context):
    if await admin_text_handler(update, context):
        return
    await text_message_handler(update, context)


async def unified_callback(update: Update, context):
    data = update.callback_query.data
    routes = {
        "confirm_purchase": callback_confirm_purchase,
        "cancel_order": callback_cancel_order,
        "send_receipt_info": callback_send_receipt_info,
        "admin_help": callback_admin_help,
    }
    if data in routes:
        await routes[data](update, context)
    elif data == "back_to_menu":
        from services.database import clear_user_state
        from handlers.keyboards import main_menu_keyboard
        await update.callback_query.answer()
        await clear_user_state(update.callback_query.from_user.id)
        await update.callback_query.message.reply_text(
            "🏠 منوی اصلی:", reply_markup=main_menu_keyboard()
        )
    elif data == "view_sample":
        await update.callback_query.answer()
        from handlers.product import sample_pdf_handler
        await sample_pdf_handler(update, context)
    elif data == "start_purchase":
        await update.callback_query.answer()
        await start_purchase_handler(update, context)
    elif data.startswith("admin_approve_"):
        await callback_admin_approve(update, context)
    elif data.startswith("admin_reject_"):
        await callback_admin_reject(update, context)
    elif data.startswith("reject_default_"):
        await callback_reject_default(update, context)
    elif data.startswith("reject_custom_"):
        await callback_reject_custom(update, context)
    elif data.startswith("admin_msg_"):
        await callback_admin_msg_customer(update, context)
    elif data.startswith("admin_back_"):
        await callback_admin_back(update, context)
    else:
        await update.callback_query.answer("نامشخص")


async def post_init(app):
    os.makedirs(DATA_DIR, exist_ok=True)
    await init_db()
    logger.info("ربات PDF + VIP آماده ✅")


def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .pool_timeout(30.0)
        .get_updates_read_timeout(30.0)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("admin", admin_panel_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unified_text))
    app.add_handler(MessageHandler(filters.PHOTO, photo_message_handler))
    app.add_handler(CallbackQueryHandler(unified_callback))
    logger.info("در حال اجرا...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
