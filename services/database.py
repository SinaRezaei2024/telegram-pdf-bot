"""database.py — SQLite وضعیت و سفارش‌ها"""

import aiosqlite
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from config import DB_PATH, OrderStatus

logger = logging.getLogger(__name__)


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                telegram_username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                amount INTEGER,
                status TEXT NOT NULL DEFAULT 'PENDING_RECEIPT',
                receipt_message_id INTEGER,
                admin_message_id INTEGER,
                pdf_sent INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                admin_note TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_state (
                telegram_user_id INTEGER PRIMARY KEY,
                state TEXT,
                temp_data TEXT,
                updated_at TEXT NOT NULL
            )
        """)
        await db.commit()
    logger.info("دیتابیس آماده شد.")


async def get_user_state(user_id: int) -> Optional[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT state FROM user_state WHERE telegram_user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def set_user_state(user_id: int, state: Optional[str], temp_data: Optional[str] = None):
    """اگر temp_data ندهی، داده موقت قبلی حفظ می‌شود."""
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        if temp_data is not None:
            await db.execute("""
                INSERT INTO user_state (telegram_user_id, state, temp_data, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(telegram_user_id) DO UPDATE SET
                    state = excluded.state,
                    temp_data = excluded.temp_data,
                    updated_at = excluded.updated_at
            """, (user_id, state, temp_data, now))
        else:
            await db.execute("""
                INSERT INTO user_state (telegram_user_id, state, temp_data, updated_at)
                VALUES (?, ?, '{}', ?)
                ON CONFLICT(telegram_user_id) DO UPDATE SET
                    state = excluded.state,
                    updated_at = excluded.updated_at
            """, (user_id, state, now))
        await db.commit()


async def get_user_temp_data(user_id: int) -> Dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT temp_data FROM user_state WHERE telegram_user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            if row and row[0]:
                try:
                    return json.loads(row[0])
                except Exception:
                    return {}
            return {}


async def update_user_temp_data(user_id: int, data: Dict[str, Any]):
    now = datetime.now().isoformat()
    payload = json.dumps(data, ensure_ascii=False)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO user_state (telegram_user_id, state, temp_data, updated_at)
            VALUES (?, '', ?, ?)
            ON CONFLICT(telegram_user_id) DO UPDATE SET
                temp_data = excluded.temp_data,
                updated_at = excluded.updated_at
        """, (user_id, payload, now))
        await db.commit()


async def clear_user_state(user_id: int):
    await set_user_state(user_id, None, "{}")


async def create_order(
    telegram_user_id: int,
    telegram_username: Optional[str],
    amount: int,
) -> int:
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            INSERT INTO orders
                (telegram_user_id, telegram_username, amount, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            telegram_user_id, telegram_username,
            amount, OrderStatus.PENDING_RECEIPT, now, now,
        ))
        await db.commit()
        return cur.lastrowid


async def get_order(order_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_active_order_for_user(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM orders
            WHERE telegram_user_id = ? AND status IN (?, ?)
            ORDER BY id DESC LIMIT 1
        """, (user_id, OrderStatus.PENDING_RECEIPT, OrderStatus.PENDING_ADMIN_APPROVAL)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def update_order_status(order_id: int, status: str, admin_note: str = None):
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        if admin_note is not None:
            await db.execute(
                "UPDATE orders SET status=?, admin_note=?, updated_at=? WHERE id=?",
                (status, admin_note, now, order_id),
            )
        else:
            await db.execute(
                "UPDATE orders SET status=?, updated_at=? WHERE id=?",
                (status, now, order_id),
            )
        await db.commit()


async def set_order_receipt(order_id: int, receipt_message_id: int):
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE orders SET receipt_message_id=?, status=?, updated_at=?
            WHERE id=?
        """, (receipt_message_id, OrderStatus.PENDING_ADMIN_APPROVAL, now, order_id))
        await db.commit()


async def set_order_admin_message(order_id: int, admin_message_id: int):
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET admin_message_id=?, updated_at=? WHERE id=?",
            (admin_message_id, now, order_id),
        )
        await db.commit()


async def mark_pdf_sent(order_id: int):
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET pdf_sent=1, updated_at=? WHERE id=?",
            (now, order_id),
        )
        await db.commit()
