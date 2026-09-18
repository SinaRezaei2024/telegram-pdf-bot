"""admin.py — تأیید، ارسال PDF، لینک VIP یک‌بارمصرف"""

import logging
import os
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from config import (
    ADMIN_TELEGRAM_ID, OrderStatus, SUPPORT_USERNAME,
    FULL_PDF_PATH, VIP_GROUP_ID, PRODUCT_NAME,
)
from handlers.keyboards import (
    admin_main_keyboard, admin_reject_reason_keyboard,
    admin_order_keyboard, main_menu_keyboard,
)
from services.database import (
    get_order, update_order_status, get_user_state, set_user_state,
    mark_pdf_sent, clear_user_state,
)
from services.order_service import format_price

logger = logging.getLogger(__name__)

ADMIN_STATE_REJECT = "admin_waiting_custom_reject"
ADMIN_STATE_MSG = "admin_waiting_msg_for_user"
CTX_ORDER = "admin_order_id"
CTX_TARGET = "admin_target_user"


def is_admin(uid: int) -> bool:
    return uid == ADMIN_TELEGRAM_ID


async def denied(update: Update):
    if update.message:
        await update.message.reply_text("⛔ دسترسی غیرمجاز.")
    elif update.callback_query:
        await update.callback_query.answer("⛔ غیرمجاز", show_alert=True)


async def admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await denied(update)
        return
    await update.message.reply_text(
        "🔐 <b>پنل مدیریت</b>\n\n"
        "رسیدهای پرداخت به‌صورت پیام جداگانه با دکمه‌های تأیید/رد می‌آیند.\n\n"
        "دستورات:\n"
        "• تأیید → ارسال خودکار PDF + لینک VIP یک‌بارمصرف\n"
        "• رد → اطلاع به مشتری",
        parse_mode="HTML",
        reply_markup=admin_main_keyboard(),
    )


async def callback_admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await denied(update)
        return
    await query.answer()
    await query.message.reply_text(
        "ℹ️ وقتی مشتری رسید بفرستد، پیام با دکمه‌های تأیید/رد دریافت می‌کنید.\n\n"
        "✅ تأیید = PDF + لینک یک‌بارمصرف گروه VIP\n"
        "❌ رد = پیام به مشتری",
    )


async def create_onetime_vip_link(bot) -> Optional[str]:
    """لینک دعوت یک‌بارمصرف برای گروه VIP."""
    if not VIP_GROUP_ID:
        logger.error("VIP_GROUP_ID در .env تنظیم نشده.")
        return None
    try:
        invite = await bot.create_chat_invite_link(
            chat_id=VIP_GROUP_ID,
            member_limit=1,
            name="خریدار PDF",
            creates_join_request=False,
        )
        return invite.invite_link
    except Exception as e:
        logger.error(f"ساخت لینک VIP ناموفق: {e}")
        return None


async def send_pdf_and_vip(bot, order: dict) -> tuple[bool, str]:
    uid = order["telegram_user_id"]
    oid = order["id"]
    notes = []

    if not os.path.exists(FULL_PDF_PATH):
        return False, "فایل assets/full.pdf یافت نشد"

    try:
        with open(FULL_PDF_PATH, "rb") as f:
            await bot.send_document(
                chat_id=uid,
                document=f,
                filename=f"{PRODUCT_NAME}.pdf",
                caption=(
                    f"✅ <b>پرداخت تأیید شد</b>\n\n"
                    f"📋 سفارش <code>#{oid}</code>\n"
                    f"📎 فایل کامل PDF پیوست است."
                ),
                parse_mode="HTML",
                read_timeout=120,
                write_timeout=120,
            )
        await mark_pdf_sent(oid)
        notes.append("PDF ✅")
    except Exception as e:
        logger.error(f"PDF to {uid}: {e}")
        return False, f"خطا در ارسال PDF: {e}"

    link = await create_onetime_vip_link(bot)
    try:
        if link:
            await bot.send_message(
                chat_id=uid,
                text=(
                    f"🎁 <b>گروه VIP — لینک اختصاصی شما</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"این لینک <b>فقط برای شما</b> و <b>یک‌بارمصرف</b> است.\n"
                    f"اگر برای شخص دیگری بفرستید، برای او کار نمی‌کند.\n\n"
                    f"🔗 {link}\n\n"
                    f"پس از عضویت، به حل سؤالات ویدیویی دسترسی دارید."
                ),
                parse_mode="HTML",
            )
            notes.append("VIP لینک یک‌بارمصرف ✅")
        else:
            await bot.send_message(
                chat_id=uid,
                text=(
                    f"✅ PDF ارسال شد.\n\n"
                    f"برای عضویت VIP با پشتیبانی هماهنگ کنید:\n"
                    f"@{SUPPORT_USERNAME}"
                ),
                parse_mode="HTML",
            )
            notes.append("VIP لینک ساخته نشد — پشتیبانی")
    except Exception as e:
        notes.append(f"VIP پیام: {e}")

    return True, " | ".join(notes)


async def callback_admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await denied(update)
        return
    await query.answer()

    oid = int(query.data.split("_")[-1])
    order = await get_order(oid)
    if not order:
        await query.message.reply_text("⚠️ سفارش یافت نشد.")
        return
    if order.get("status") == OrderStatus.PAID:
        await query.message.reply_text("ℹ️ قبلاً تأیید شده.")
        return

    await update_order_status(oid, OrderStatus.PAID)
    order = await get_order(oid)
    ok, status = await send_pdf_and_vip(context.bot, order)
    await clear_user_state(order["telegram_user_id"])

    await query.message.reply_text(
        f"✅ سفارش #{oid} تأیید شد\n\n"
        f"{'✅' if ok else '❌'} {status}",
        parse_mode="HTML",
    )


async def callback_admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await denied(update)
        return
    await query.answer()
    oid = int(query.data.split("_")[-1])
    await query.message.reply_text(
        f"رد سفارش #{oid} — نوع پیام:",
        reply_markup=admin_reject_reason_keyboard(oid),
    )


async def callback_reject_default(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await denied(update)
        return
    await query.answer()
    await _reject(query, context, int(query.data.split("_")[-1]), True)


async def callback_reject_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await denied(update)
        return
    await query.answer()
    oid = int(query.data.split("_")[-1])
    context.user_data[CTX_ORDER] = oid
    await set_user_state(query.from_user.id, ADMIN_STATE_REJECT)
    await query.message.reply_text("✏️ متن رد را بنویسید:")


async def _reject(query_or_fake, context, oid: int, default: bool, custom: Optional[str] = None):
    order = await get_order(oid)
    msg = getattr(query_or_fake, "message", None)
    if not order:
        if msg:
            await msg.reply_text("⚠️ سفارش یافت نشد.")
        return

    note = custom or "رد پیش‌فرض"
    await update_order_status(oid, OrderStatus.REJECTED, admin_note=note)
    await clear_user_state(order["telegram_user_id"])

    if default:
        text = (
            f"❌ پرداخت تأیید نشد — سفارش <code>#{oid}</code>\n\n"
            f"می‌توانید دوباره سفارش دهید یا با پشتیبانی تماس بگیرید:\n"
            f"@{SUPPORT_USERNAME}"
        )
    else:
        text = f"❌ پرداخت تأیید نشد — #{oid}\n\n{custom}"

    try:
        await context.bot.send_message(
            chat_id=order["telegram_user_id"],
            text=text,
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(),
        )
    except Exception as e:
        logger.warning(f"reject notify: {e}")

    if msg:
        await msg.reply_text(f"✅ رد #{oid} ثبت شد.")


async def callback_admin_msg_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await denied(update)
        return
    await query.answer()
    oid = int(query.data.split("_")[-1])
    order = await get_order(oid)
    if not order:
        await query.message.reply_text("⚠️ سفارش یافت نشد.")
        return
    context.user_data[CTX_ORDER] = oid
    context.user_data[CTX_TARGET] = order["telegram_user_id"]
    await set_user_state(query.from_user.id, ADMIN_STATE_MSG)
    await query.message.reply_text(f"💬 پیام برای مشتری #{oid}:")


async def callback_admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await denied(update)
        return
    await query.answer()
    oid = int(query.data.split("_")[-1])
    await query.message.reply_text(f"سفارش #{oid}", reply_markup=admin_order_keyboard(oid))


async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not is_admin(user.id):
        return False
    state = await get_user_state(user.id)

    if state == ADMIN_STATE_REJECT:
        oid = context.user_data.get(CTX_ORDER)
        custom = update.message.text.strip()
        await clear_user_state(user.id)
        if not oid:
            await update.message.reply_text("⚠️ سفارش نامشخص.")
            return True

        class F:
            message = update.message

        await _reject(F(), context, oid, False, custom)
        return True

    if state == ADMIN_STATE_MSG:
        oid = context.user_data.get(CTX_ORDER)
        target = context.user_data.get(CTX_TARGET)
        text = update.message.text.strip()
        await clear_user_state(user.id)
        if not target:
            await update.message.reply_text("⚠️ کاربر نامشخص.")
            return True
        try:
            await context.bot.send_message(
                chat_id=target,
                text=f"💬 <b>پیام پشتیبانی:</b>\n\n{text}",
                parse_mode="HTML",
            )
            await update.message.reply_text(f"✅ ارسال شد (#{oid}).")
        except Exception as e:
            await update.message.reply_text(f"⚠️ {e}")
        return True

    return False
