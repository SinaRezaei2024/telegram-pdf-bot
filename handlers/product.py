"""product.py"""

import logging
import os
from telegram import Update
from telegram.ext import ContextTypes

from config import (
    PRODUCT_NAME, PRODUCT_DESCRIPTION, PRODUCT_PAGES, PDF_PRICE,
    COVER_IMAGE_PATH, SAMPLE_PDF_PATH, SUPPORT_USERNAME,
)
from handlers.keyboards import main_menu_keyboard, product_inline_keyboard
from services.order_service import format_price

logger = logging.getLogger(__name__)


async def product_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price = format_price(PDF_PRICE)
    text = (
        f"📚 <b>{PRODUCT_NAME}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{PRODUCT_DESCRIPTION}\n\n"
        f"📄 صفحات: <b>{PRODUCT_PAGES}</b>\n"
        f"💾 فرمت: <b>PDF</b>\n"
        f"💰 قیمت: <b>{price} تومان</b>\n\n"
        f"🎁 <b>هدیه خرید:</b>\n"
        f"عضویت در گروه VIP حل سؤالات ویدیویی\n"
        f"(لینک اختصاصی یک‌بارمصرف)\n\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    kb = product_inline_keyboard()
    msg = update.message
    if os.path.exists(COVER_IMAGE_PATH):
        try:
            with open(COVER_IMAGE_PATH, "rb") as f:
                await msg.reply_photo(photo=f, caption=text, parse_mode="HTML", reply_markup=kb)
            return
        except Exception as e:
            logger.warning(f"cover: {e}")
    await msg.reply_text(text, parse_mode="HTML", reply_markup=kb)


async def sample_pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or (update.callback_query.message if update.callback_query else None)
    if not message:
        return
    wait = await message.reply_text("⏳ در حال ارسال نمونه...")
    if not os.path.exists(SAMPLE_PDF_PATH):
        await wait.edit_text("⚠️ فایل نمونه موجود نیست.")
        return
    try:
        with open(SAMPLE_PDF_PATH, "rb") as f:
            await message.reply_document(
                document=f,
                filename="نمونه_ریاضی۳_پرومکس.pdf",
                caption=f"📖 <b>نمونه {PRODUCT_NAME}</b>\n\nبرای خرید کامل از منو اقدام کنید.",
                parse_mode="HTML",
            )
        await wait.delete()
    except Exception as e:
        logger.error(f"sample: {e}")
        await wait.edit_text("⚠️ خطا در ارسال نمونه.")


async def support_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"☎️ <b>پشتیبانی</b>\n\n"
        f"👤 @{SUPPORT_USERNAME}\n\n"
        f"⏰ ۹ صبح تا ۱۰ شب",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )
