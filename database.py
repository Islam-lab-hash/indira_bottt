"""SQLite слой через aiosqlite. Хранит категории, товары, корзины и заказы."""
import aiosqlite
from typing import Optional
from config import DB_PATH

DEFAULT_CATEGORIES = [
    "Комплекты",
    "Халаты",
    "Пеньюары",
    "Сорочки",
    "Наборы трусиков",
    "Свадебное белье",
    "Корсетные изделия",
    "Чулки и колготки",
    "Купальники",
    "Аксессуары",
    "Акции",
]

DEFAULT_SETTINGS = {
    # реквизиты оплаты
    "pay_card":   "0000 0000 0000 0000",
    "pay_holder": "ИВАНОВА А. А.",
    "pay_bank":   "Сбербанк",
    # тексты магазина (редактируются из админки)
    "shop_name":          "LINGERIE BOUTIQUE",
    "shop_addresses":     "📍 Grozny Mall, г. Грозный\n📍 (добавьте другие адреса)",
    "shop_schedule":      "Ежедневно 10:00 - 22:00",
    "delivery_info":      "",
    "payment_info":        "",
    "exchange_info":       "",
    "instagram_url":       "",
    "operator_username":   "",
}


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                position INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                sizes TEXT DEFAULT '',
                colors TEXT DEFAULT '',
                material TEXT DEFAULT '',
                country TEXT DEFAULT '',
                description TEXT DEFAULT '',
                photo_file_id TEXT DEFAULT '',
                in_stock INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS carts (
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                qty INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, product_id),
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT,
                phone TEXT,
                city TEXT DEFAULT '',
                delivery TEXT DEFAULT '',
                comment TEXT DEFAULT '',
                items TEXT,
                total REAL,
                status TEXT DEFAULT 'awaiting_payment',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT DEFAULT '',
                added_by INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        # Миграция: добавить status в orders, если столбца ещё нет (старые БД)
        try:
            await db.execute("ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'awaiting_payment'")
        except Exception:
            pass
        # Сидим базовые категории если их нет
        cur = await db.execute("SELECT COUNT(*) FROM categories")
        row = await cur.fetchone()
        if row and row[0] == 0:
            for i, name in enumerate(DEFAULT_CATEGORIES):
                await db.execute(
                    "INSERT INTO categories (name, position) VALUES (?, ?)",
                    (name, i),
                )
        # Сидим дефолтные настройки оплаты
        for k, v in DEFAULT_SETTINGS.items():
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
            )
        await db.commit()


# ---------- SETTINGS ----------
async def get_setting(key: str, default: str = "") -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = await cur.fetchone()
        return row[0] if row else default


async def set_setting(key: str, value: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        await db.commit()


async def get_payment_info() -> dict:
    return {
        "card":   await get_setting("pay_card",   DEFAULT_SETTINGS["pay_card"]),
        "holder": await get_setting("pay_holder", DEFAULT_SETTINGS["pay_holder"]),
        "bank":   await get_setting("pay_bank",   DEFAULT_SETTINGS["pay_bank"]),
    }


# ---------- USERS ----------
async def upsert_user(user_id: int, username: Optional[str], first_name: Optional[str]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username or "", first_name or ""),
        )
        await db.execute(
            "UPDATE users SET username=?, first_name=? WHERE user_id=?",
            (username or "", first_name or "", user_id),
        )
        await db.commit()


async def get_user(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users")
        return [r[0] for r in await cur.fetchall()]


# ---------- CATEGORIES ----------
async def list_categories() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT id, name FROM categories ORDER BY position, id"
        )
        return [dict(r) for r in await cur.fetchall()]


async def get_category(cat_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM categories WHERE id = ?", (cat_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def add_category(name: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM categories")
        pos = (await cur.fetchone())[0]
        cur = await db.execute(
            "INSERT INTO categories (name, position) VALUES (?, ?)", (name, pos)
        )
        await db.commit()
        return cur.lastrowid


async def delete_category(cat_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
        await db.commit()


# ---------- PRODUCTS ----------
async def list_products(category_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM products WHERE category_id = ? ORDER BY id DESC",
            (category_id,),
        )
        return [dict(r) for r in await cur.fetchall()]


async def get_product(product_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def add_product(data: dict) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO products
            (category_id, name, price, sizes, colors, material, country,
             description, photo_file_id, in_stock)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (
                data["category_id"],
                data["name"],
                data["price"],
                data.get("sizes", ""),
                data.get("colors", ""),
                data.get("material", ""),
                data.get("country", ""),
                data.get("description", ""),
                data.get("photo_file_id", ""),
            ),
        )
        await db.commit()
        return cur.lastrowid


async def delete_product(product_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        await db.commit()


async def search_products_by_size(size: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM products WHERE sizes LIKE ? ORDER BY id DESC LIMIT 20",
            (f"%{size}%",),
        )
        return [dict(r) for r in await cur.fetchall()]


async def search_products_by_color(color: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM products WHERE colors LIKE ? ORDER BY id DESC LIMIT 20",
            (f"%{color}%",),
        )
        return [dict(r) for r in await cur.fetchall()]


# ---------- CART ----------
async def add_to_cart(user_id: int, product_id: int, qty: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO carts (user_id, product_id, qty) VALUES (?, ?, ?)
               ON CONFLICT(user_id, product_id) DO UPDATE SET qty = qty + excluded.qty""",
            (user_id, product_id, qty),
        )
        await db.commit()


async def remove_from_cart(user_id: int, product_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM carts WHERE user_id = ? AND product_id = ?",
            (user_id, product_id),
        )
        await db.commit()


async def get_cart(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT p.id, p.name, p.price, p.photo_file_id, c.qty
               FROM carts c JOIN products p ON p.id = c.product_id
               WHERE c.user_id = ?""",
            (user_id,),
        )
        return [dict(r) for r in await cur.fetchall()]


async def clear_cart(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM carts WHERE user_id = ?", (user_id,))
        await db.commit()


# ---------- ORDERS ----------
async def create_order(data: dict) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO orders
            (user_id, name, phone, city, delivery, comment, items, total, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["user_id"],
                data["name"],
                data["phone"],
                data.get("city", ""),
                data.get("delivery", ""),
                data.get("comment", ""),
                data.get("items", ""),
                data["total"],
                data.get("status", "awaiting_payment"),
            ),
        )
        await db.commit()
        return cur.lastrowid


# ---------- STATS for admin ----------
async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        out = {}
        for key, sql in [
            ("users", "SELECT COUNT(*) FROM users"),
            ("products", "SELECT COUNT(*) FROM products"),
            ("categories", "SELECT COUNT(*) FROM categories"),
            ("orders", "SELECT COUNT(*) FROM orders"),
        ]:
            cur = await db.execute(sql)
            out[key] = (await cur.fetchone())[0]
        return out


# ---------- HELPERS ----------
async def get_order(order_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def update_order_status(order_id: int, status: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (status, order_id),
        )
        await db.commit()


async def update_order_delivery(order_id: int, method: str, address: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET delivery = ?, city = ? WHERE id = ?",
            (method, address, order_id),
        )
        await db.commit()


async def is_db_admin(uid: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT 1 FROM admins WHERE user_id = ?", (uid,))
        row = await cur.fetchone()
        return row is not None


async def add_admin(uid: int, added_by: Optional[int] = None, username: str = "") -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO admins (user_id, username, added_by) VALUES (?, ?, ?)",
            (uid, username or "", added_by),
        )
        await db.commit()


async def remove_admin(uid: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE user_id = ?", (uid,))
        await db.commit()


async def list_admins() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM admins ORDER BY added_at DESC")
        return [dict(r) for r in await cur.fetchall()]


async def get_latest_user_order(user_id: int, status: Optional[str] = None) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cur = await db.execute(
                "SELECT * FROM orders WHERE user_id=? AND status=? ORDER BY id DESC LIMIT 1",
                (user_id, status),
            )
        else:
            cur = await db.execute(
                "SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 1",
                (user_id,),
            )
        row = await cur.fetchone()
        return dict(row) if row else None


# ---------- PRODUCT EDIT / CATEGORY EDIT / ORDERS LIST ----------
async def update_product(product_id: int, **fields) -> None:
    """Частичное обновление товара : любые поля из products."""
    allowed = {
        "category_id", "name", "price", "sizes", "colors",
        "material", "country", "description", "photo_file_id",
    }
    sets, vals = [], []
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k} = ?")
            vals.append(v)
    if not sets:
        return
    vals.append(product_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE products SET {', '.join(sets)} WHERE id = ?", vals
        )
        await db.commit()


async def list_all_products() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT p.*, c.name AS category_name FROM products p "
            "LEFT JOIN categories c ON c.id = p.category_id ORDER BY c.position, p.id"
        )
        return [dict(r) for r in await cur.fetchall()]


async def rename_category(cat_id: int, new_name: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE categories SET name = ? WHERE id = ?", (new_name, cat_id))
        await db.commit()


async def list_orders(status: Optional[str] = None, limit: int = 30) -> list[dict]:
    sql = "SELECT * FROM orders"
    params: list = []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(sql, params)
        return [dict(r) for r in await cur.fetchall()]


async def order_stats_by_status() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT status, COUNT(*) AS n FROM orders GROUP BY status"
        )
        return {s: n for s, n in await cur.fetchall()}


# алиас для совместимости
async def get_text(key: str) -> str:
    return await get_setting(key, "")
