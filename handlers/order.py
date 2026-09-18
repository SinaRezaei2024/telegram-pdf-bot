"""order.py — خرید PDF بدون دریافت نام/تلفن
مراحل: تأیید خرید → کارت → رسید → تأیید ادمین
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from telegram import Update
from telegram.ext import ContextTypes

from config import (
    PDF_PRICE, PRODUCT_NAME, OrderStatus,
    PAYMENT_CARD_NUMBER, PAYMENT_CARD_HOLDER, PAYMENT_BANK,
)
from handlers.keyboards import (
    main_menu_keyboard, order_confirm_keyboard,
    send_receipt_keyboard, cancel_current_order_keyboard,
)
from services.database import (
    get_user_state, set_user_state, clear_user_state,
    create_order, get_active_order_for_user,
    update_order_status, set_order_receipt, set_order_admin_message,
)
from services.order_service import format_price

logger = logging.getLogger(__name__)

STATE_RECEIPT = "waiting_receipt"


def build_payment_message(amount: int, order_id: int) -> str:
    return (
        f"✅ سفارش ثبت شد — <code>#{order_id}</code>\n\n"
        f"💳 <b>اطلاعات پرداخت</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 مبلغ: <code>{format_price(amount)}</code> تومان\n\n"
        f"شماره کارت:\n<code>{PAYMENT_CARD_NUMBER}</code>\n\n"
        f"👤 به نام: {PAYMENT_CARD_HOLDER}\n"
        f"🏦 بانک: {PAYMENT_BANK}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"پس از پرداخت، <b>تصویر رسید</b> را اینجا بفرستید. 👇"
    )


async def show_active_order_info(update, context, order: Dict[str, Any]):
    msg = update.message or (update.callback_query.message if update.callback_query else None)
    if not msg:
        return
    oid = order["id"]
    if order.get("status") == OrderStatus.PENDING_RECEIPT:
        await msg.reply_text(
            f"⚠️ سفارش فعال دارید: <code>#{oid}</code>\n\n"
            f"📤 تصویر رسید را ارسال کنید.",
            parse_mode="HTML",
            reply_markup=send_receipt_keyboard(),
        )
    else:
        await msg.reply_text(
            f"⏳ سفارش <code>#{oid}</code> در حال بررسی است.",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(),
        )


async def start_purchase_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    active = await get_active_order_for_user(user.id)
    if active:
        await show_active_order_info(update, context, active)
        return

    text = (
        f"🛒 <b>خرید PDF — {PRODUCT_NAME}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 قیمت: <b>{format_price(PDF_PRICE)} تومان</b>\n\n"
        f"🎁 با خرید دریافت می‌کنید:\n"
        f"• فایل کامل PDF\n"
        f"• لینک <b>یک‌بارمصرف</b> عضویت در گروه VIP\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"ادامه می‌دهید؟"
    )
    target = update.callback_query.message if update.callback_query else update.message
    await target.reply_text(text, parse_mode="HTML", reply_markup=order_confirm_keyboard())


async def callback_confirm_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأیید خرید → ثبت سفارش و نمایش کارت (بدون دریافت اطلاعات شخصی)."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    active = await get_active_order_for_user(user.id)
    if active:
        await query.message.reply_text(
            "⚠️ سفارش فعال دارید.",
            reply_markup=cancel_current_order_keyboard(),
        )
        return

    try:
        order_id = await create_order(
            telegram_user_id=user.id,
            telegram_username=user.username,
            amount=PDF_PRICE,
        )
    except Exception as e:
        logger.error(f"create_order: {e}")
        await query.message.reply_text(
            "⚠️ خطا در ثبت سفارش. دوباره تلاش کنید.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await set_user_state(user.id, STATE_RECEIPT)
    await query.message.reply_text(
        build_payment_message(PDF_PRICE, order_id),
        parse_mode="HTML",
        reply_markup=send_receipt_keyboard(),
    )


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    if text == "📚 معرفی جزوه":
        from handlers.product import product_info_handler
        await product_info_handler(update, context)
        return
    if text == "🛒 خرید PDF":
        await start_purchase_handler(update, context)
        return
    if text == "📖 مشاهده نمونه":
        from handlers.product import sample_pdf_handler
        await sample_pdf_handler(update, context)
        return
    if text == "☎️ پشتیبانی":
        from handlers.product import support_handler
        await support_handler(update, context)
        return

    state = await get_user_state(user.id)
    if state == STATE_RECEIPT:
        await update.message.reply_text(
            "📤 لطفاً <b>عکس</b> رسید پرداخت را بفرستید.",
            parse_mode="HTML",
            reply_markup=send_receipt_keyboard(),
        )
        return

    await update.message.reply_text(
        "از منو یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=main_menu_keyboard(),
    )


async def callback_cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    active = await get_active_order_for_user(user.id)
    if active:
        if active.get("status") == OrderStatus.PENDING_ADMIN_APPROVAL:
            await query.message.reply_text(
                "⚠️ رسید در حال بررسی است؛ لغو ممکن نیست.",
                reply_markup=main_menu_keyboard(),
            )
            return
        await update_order_status(active["id"], OrderStatus.CANCELLED)
    await clear_user_state(user.id)
    await query.message.reply_text("❌ سفارش لغو شد.", reply_markup=main_menu_keyboard())


async def callback_send_receipt_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "📤 تصویر رسید را مستقیماً در همین چت بفرستید.\nفقط عکس پذیرفته می‌شود.",
        parse_mode="HTML",
    )


async def photo_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    state = await get_user_state(user.id)

    if state != STATE_RECEIPT:
        active = await get_active_order_for_user(user.id)
        if active and active.get("status") == OrderStatus.PENDING_ADMIN_APPROVAL:
            await update.message.reply_text("⏳ رسید قبلاً دریافت شده و در حال بررسی است.")
            return
        await update.message.reply_text(
            "الان منتظر رسید نیستیم.",
            reply_markup=main_menu_keyboard(),
        )
        return

    active = await get_active_order_for_user(user.id)
    if not active:
        await clear_user_state(user.id)
        await update.message.reply_text(
            "⚠️ سفارش فعال نیست.",
            reply_markup=main_menu_keyboard(),
        )
        return

    try:
        await _forward_to_admin(update, context, active)
    except Exception as e:
        logger.error(f"forward receipt: {e}")
        await update.message.reply_text("⚠️ خطا در ارسال رسید. دوباره تلاش کنید.")
        return

    await set_order_receipt(active["id"], update.message.message_id)
    await update.message.reply_text(
        f"✅ رسید دریافت شد — سفارش <code>#{active['id']}</code>\n\n"
        f"پس از تأیید، PDF و لینک VIP یک‌بارمصرف برایتان ارسال می‌شود.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


async def _forward_to_admin(update, context, order: Dict[str, Any]):
    from config import ADMIN_TELEGRAM_ID
    from handlers.keyboards import admin_order_keyboard

    oid = order["id"]
    try:
        dt = datetime.fromisoformat(order.get("created_at", "")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        dt = order.get("created_at", "")

    uname = order.get("telegram_username") or "—"
    caption = (
        f"🔔 <b>رسید جدید</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 سفارش: <code>#{oid}</code>\n"
        f"🆔 Telegram ID: <code>{order.get('telegram_user_id', '')}</code>\n"
        f"👤 Username: @{uname}\n"
        f"💰 مبلغ: {format_price(order.get('amount', 0))} تومان\n"
        f"📅 {dt}"
    )
    photo = update.message.photo[-1].file_id
    sent = None
    for i in range(1, 4):
        try:
            sent = await context.bot.send_photo(
                chat_id=ADMIN_TELEGRAM_ID,
                photo=photo,
                caption=caption,
                parse_mode="HTML",
                reply_markup=admin_order_keyboard(oid),
                read_timeout=45,
                write_timeout=45,
            )
            break
        except Exception as e:
            logger.warning(f"admin photo try {i}: {e}")
            await asyncio.sleep(2 * i)

    if not sent:
        info = await context.bot.send_message(
            chat_id=ADMIN_TELEGRAM_ID,
            text=caption,
            parse_mode="HTML",
            reply_markup=admin_order_keyboard(oid),
        )
        try:
            await context.bot.copy_message(
                chat_id=ADMIN_TELEGRAM_ID,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id,
            )
        except Exception:
            pass
        sent = info

    await set_order_admin_message(oid, sent.message_id)
