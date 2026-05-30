"""Засеивает БД тестовыми товарами (по 3 на категорию) и генерирует им фото.

Запуск:  python seed_demo.py
"""
import asyncio
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import database as db

ROOT = Path(__file__).parent
PRODUCTS_DIR = ROOT / "assets" / "products"
PRODUCTS_DIR.mkdir(parents=True, exist_ok=True)


PALETTE = [
    ("#f4f1ec", "#1a1a1a"),
    ("#e8e6e1", "#1a1a1a"),
    ("#1a1a1a", "#f4f1ec"),
    ("#d9d5cf", "#1a1a1a"),
]

TEMPLATES = {
    "Комплекты": [
        ("Комплект «Lara»",  4990, "S, M, L",       "чёрный, графит",        "шёлк 100%"),
        ("Комплект «Mia»",   5490, "S, M, L, XL",   "белый, кремовый",       "шёлк 100%"),
        ("Комплект «Ева»",   6290, "M, L",          "небесно-голубой",       "шёлк 100%, кружево"),
    ],
    "Халаты": [
        ("Халат «Шёлк»",     3990, "S, M, L",       "графит",                "шёлк 100%"),
        ("Халат «Нуар»",     4490, "M, L, XL",      "чёрный",                "шёлк 100%"),
        ("Халат «Перла»",    4990, "S, M, L",       "белый",                 "шёлк 100%"),
    ],
    "Пеньюары": [
        ("Пеньюар «Aurora»", 5990, "S, M, L",       "белый",                 "шёлк 100%, кружево"),
        ("Пеньюар «Noir»",   6490, "M, L",          "чёрный",                "шёлк 100%, кружево"),
        ("Пеньюар «Sky»",    5790, "S, M, L",       "небесно-голубой",       "шёлк 100%"),
    ],
    "Сорочки": [
        ("Сорочка «Liza»",   2990, "S, M, L, XL",   "белый",                 "шёлк 100%"),
        ("Сорочка «Nina»",   3290, "M, L",          "графит",                "шёлк 100%"),
        ("Сорочка «Anna»",   3490, "S, M, L",       "чёрный",                "шёлк 100%"),
    ],
    "Наборы трусиков": [
        ("Набор 3 пары · classic",   249, "S, M, L, XL",   "белый, чёрный, графит", "хлопок"),
        ("Набор 3 пары · lace",      349, "S, M, L",       "чёрный, белый",         "кружево + хлопок"),
        ("Набор 3 пары · silk",      449, "S, M, L",       "графит, кремовый",      "шёлк 100%"),
    ],
    "Свадебное белье": [
        ("Комплект «Bride»",  7990, "S, M, L",      "белый",                  "шёлк, кружево, жемчуг"),
        ("Пояс для чулок",    2490, "S, M, L",      "белый",                  "кружево"),
        ("Подвязка свадебная", 990, "one size",     "белый",                  "кружево, атлас"),
    ],
    "Корсетные изделия": [
        ("Корсет «Bella»",   6990, "S, M, L",       "чёрный",                 "сатин, косточки"),
        ("Корсет «Vera»",    7490, "S, M, L, XL",   "графит",                 "сатин, косточки"),
        ("Бюстье «Mira»",    3990, "S, M, L",       "белый",                  "кружево"),
    ],
    "Чулки и колготки": [
        ("Чулки классика",    890, "S, M, L",       "чёрный",                 "20 den, микрофибра"),
        ("Чулки кружевные",  1290, "S, M, L",       "чёрный, белый",          "кружево"),
        ("Колготки 40 den",   690, "2, 3, 4",       "графит, чёрный",         "микрофибра"),
    ],
    "Купальники": [
        ("Купальник «Sun»",  3990, "S, M, L",       "чёрный",                 "полиамид + эластан"),
        ("Купальник «Riva»", 4290, "S, M, L",       "белый",                  "полиамид + эластан"),
        ("Купальник «Mare»", 4490, "M, L, XL",      "графит",                 "полиамид + эластан"),
    ],
    "Аксессуары": [
        ("Маска для сна шёлк",  990, "one size",    "чёрный",                 "шёлк 100%"),
        ("Резинки шёлк (3 шт)", 590, "one size",    "графит",                 "шёлк 100%"),
        ("Чехол для белья",     790, "M, L",        "бежевый",                "хлопок"),
    ],
    "Акции": [
        ("Комплект -50% «Sale»",  2490, "S, M, L",  "чёрный",                 "шёлк 100%"),
        ("Халат -40% «Sale»",     2490, "M, L",     "графит",                 "шёлк 100%"),
        ("Сорочка -30% «Sale»",   1990, "S, M, L",  "белый",                  "шёлк 100%"),
    ],
}


def _find_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def make_image(path: Path, title: str, subtitle: str, idx: int) -> None:
    bg, fg = PALETTE[idx % len(PALETTE)]
    W, H = 900, 900
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)

    # тонкая рамка
    d.rectangle([20, 20, W - 20, H - 20], outline=fg, width=2)

    # бренд сверху
    f_brand = _find_font(28)
    d.text((W // 2, 90), "LINGERIE BOUTIQUE", fill=fg, font=f_brand, anchor="mm")

    # заголовок (название)
    f_title = _find_font(54)
    d.text((W // 2, H // 2 - 30), title, fill=fg, font=f_title, anchor="mm")

    # подзаголовок (категория)
    f_sub = _find_font(28)
    d.text((W // 2, H // 2 + 40), subtitle.upper(), fill=fg, font=f_sub, anchor="mm")

    # подпись внизу
    f_foot = _find_font(22)
    d.text((W // 2, H - 90), "premium silk · turkey", fill=fg, font=f_foot, anchor="mm")

    img.save(path, "JPEG", quality=88)


async def seed() -> None:
    await db.init_db()
    cats = await db.list_categories()
    cat_by_name = {c["name"]: c["id"] for c in cats}

    # Сносим уже засеянные демо-товары, чтобы не плодились дубли
    import aiosqlite
    async with aiosqlite.connect(db.DB_PATH) as conn:
        await conn.execute(
            "DELETE FROM products WHERE photo_file_id LIKE ?",
            (f"{PRODUCTS_DIR}%",),
        )
        await conn.commit()

    total = 0
    for cat_name, items in TEMPLATES.items():
        if cat_name not in cat_by_name:
            print(f"⚠ Категория не найдена: {cat_name}")
            continue
        cat_id = cat_by_name[cat_name]
        for idx, (name, price, sizes, colors, material) in enumerate(items):
            slug = f"{cat_id}_{idx}".replace(" ", "_")
            photo_path = PRODUCTS_DIR / f"{slug}.jpg"
            make_image(photo_path, name, cat_name, idx)
            await db.add_product({
                "category_id": cat_id,
                "name": name,
                "price": price,
                "sizes": sizes,
                "colors": colors,
                "material": material,
                "country": "Turkey",
                "description": f"Тестовый товар категории «{cat_name}». Premium-качество.",
                "photo_file_id": str(photo_path),
            })
            total += 1
            print(f"  + {name} ({price} ₽)")

    print(f"\n✅ Засеяно товаров: {total}")
    print(f"📁 Фото лежат в: {PRODUCTS_DIR}")


if __name__ == "__main__":
    asyncio.run(seed())
