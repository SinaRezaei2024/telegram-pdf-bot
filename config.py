"""config.py — تنظیمات از .env"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val:
        raise EnvironmentError(f"متغیر '{key}' در فایل .env تنظیم نشده است.")
    return val


BOT_TOKEN: str = _require("BOT_TOKEN")
ADMIN_TELEGRAM_ID: int = int(_require("ADMIN_TELEGRAM_ID"))

PAYMENT_CARD_NUMBER: str = _require("PAYMENT_CARD_NUMBER")
PAYMENT_CARD_HOLDER: str = _require("PAYMENT_CARD_HOLDER")
PAYMENT_BANK: str = _require("PAYMENT_BANK")

PDF_PRICE: int = int(os.getenv("PDF_PRICE", "350000"))
SUPPORT_USERNAME: str = os.getenv("SUPPORT_USERNAME", "sinarezaeiifn").strip()

_gid = os.getenv("VIP_GROUP_ID", "").strip()
VIP_GROUP_ID: Optional[int] = int(_gid) if _gid else None

PRODUCT_NAME: str = "ریاضی ۳ پرومکس"
PRODUCT_PAGES: int = 180
PRODUCT_DESCRIPTION: str = (
    "در این مجموعه خط به خط کتاب درسی بررسی شده است و همچنین تمامی سؤالات "
    "امتحان نهایی ریاضی 3 رشته تجربی و سؤالات مشترک از درس حسابان 2 رشته ریاضی "
    "از دی ماه 1397 تا دی ماه 1404 را به صورت درس به درس و از ساده به دشوار "
    "دسته‌بندی کرده‌ایم، همچنین سؤالات پرتکرار در هر بخش با علامت ستاره مشخص شده است."
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR = os.path.join(BASE_DIR, "data")

COVER_IMAGE_PATH = os.path.join(ASSETS_DIR, "cover.jpg")
SAMPLE_PDF_PATH = os.path.join(ASSETS_DIR, "sample.pdf")
FULL_PDF_PATH = os.path.join(ASSETS_DIR, "full.pdf")
DB_PATH = os.path.join(DATA_DIR, "bot_state.db")


class OrderStatus:
    PENDING_RECEIPT = "PENDING_RECEIPT"
    PENDING_ADMIN_APPROVAL = "PENDING_ADMIN_APPROVAL"
    PAID = "PAID"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
