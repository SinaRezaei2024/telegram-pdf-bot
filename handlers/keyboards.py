"""keyboards.py"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["📚 معرفی جزوه", "🛒 خرید PDF"],
            ["📖 مشاهده نمونه", "☎️ پشتیبانی"],
        ],
        resize_keyboard=True,
    )


def product_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📖 مشاهده نمونه", callback_data="view_sample"),
        InlineKeyboardButton("🛒 خرید PDF", callback_data="start_purchase"),
    ]])


def order_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید و ادامه", callback_data="confirm_purchase")],
        [InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back_to_menu")],
    ])


def send_receipt_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 راهنمای ارسال رسید", callback_data="send_receipt_info")],
        [InlineKeyboardButton("❌ لغو سفارش", callback_data="cancel_order")],
    ])


def cancel_current_order_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ لغو سفارش فعلی", callback_data="cancel_order")],
        [InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back_to_menu")],
    ])


def admin_order_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ تأیید و ارسال PDF", callback_data=f"admin_approve_{order_id}"),
            InlineKeyboardButton("❌ رد پرداخت", callback_data=f"admin_reject_{order_id}"),
        ],
        [InlineKeyboardButton("💬 پیام به مشتری", callback_data=f"admin_msg_{order_id}")],
    ])


def admin_reject_reason_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 پیام آماده", callback_data=f"reject_default_{order_id}")],
        [InlineKeyboardButton("✏️ پیام دلخواه", callback_data=f"reject_custom_{order_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin_back_{order_id}")],
    ])


def admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("ℹ️ راهنمای پنل", callback_data="admin_help")],
    ])
