"""Все инлайн-клавиатуры. Стиль: минимализм, ч/б, моноширинные эмодзи-маркеры."""
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


# --------- USER ---------
CATEGORY_EMOJI = {
    "Комплекты":           "💝",
    "Халаты":              "🌙",
    "Пеньюары":            "💗",
    "Сорочки":             "🌸",
    "Наборы трусиков":     "💋",
    "Свадебное белье":     "💍",
    "Корсетные изделия":   "⭐",
    "Чулки и колготки":    "🌺",
    "Купальники":          "🌊",
    "Аксессуары":          "💎",
    "Акции":               "🔥",
}


def _cat_label(name: str) -> str:
    emo = CATEGORY_EMOJI.get(name, "•")
    return f"{emo} {name}"


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Каталог",     callback_data="catalog")
    kb.button(text="🔍 Подбор",      callback_data="selector")
    kb.button(text="🛒 Корзина",     callback_data="cart")
    kb.button(text="💬 Информация",  callback_data="info")
    kb.adjust(2, 2)
    return kb.as_markup()


def back_to_main() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="← В меню", callback_data="main")
    return kb.as_markup()


def categories_kb(categories: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for c in categories:
        kb.button(text=_cat_label(c["name"]), callback_data=f"cat:{c['id']}")
    kb.button(text="← В меню", callback_data="main")
    kb.adjust(2)
    return kb.as_markup()


def products_kb(products: list[dict], category_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in products:
        kb.button(
            text=f"{p['name']} · {int(p['price'])} ₽",
            callback_data=f"prod:{p['id']}",
        )
    kb.button(text="← К категориям", callback_data="catalog")
    kb.adjust(1)
    return kb.as_markup()


def product_card_kb(product_id: int, category_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 В корзину", callback_data=f"add:{product_id}")
    kb.button(text="📏 Уточнить размер", callback_data=f"ask_size:{product_id}")
    kb.button(text="💬 Спросить консультанта", callback_data=f"ask_cons:{product_id}")
    kb.button(text="← Назад", callback_data=f"cat:{category_id}")
    kb.adjust(1, 1, 1, 1)
    return kb.as_markup()


def selector_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📏 По размеру", callback_data="sel:size")
    kb.button(text="🎨 По цвету", callback_data="sel:color")
    kb.button(text="🎁 Для подарка", callback_data="sel:gift")
    kb.button(text="💬 Помощь консультанта", callback_data="sel:cons")
    kb.button(text="← В меню", callback_data="main")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def cart_kb(items: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for it in items:
        kb.button(
            text=f"✕ {it['name']}",
            callback_data=f"rm:{it['id']}",
        )
    if items:
        kb.button(text="💳 Реквизиты для оплаты", callback_data="cart:pay")
        kb.button(text="✅ Оформить заказ", callback_data="checkout")
        kb.button(text="🗑 Очистить корзину", callback_data="clear_cart")
    kb.button(text="← В меню", callback_data="main")
    kb.adjust(1)
    return kb.as_markup()


def info_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📍 Адреса и график", callback_data="info:addr")
    kb.button(text="🚚 Доставка", callback_data="info:delivery")
    kb.button(text="💳 Оплата", callback_data="info:pay")
    kb.button(text="🔁 Обмен и возврат", callback_data="info:return")
    kb.button(text="📷 Instagram", callback_data="info:inst")
    kb.button(text="💬 Связь с оператором", callback_data="info:op")
    kb.button(text="← В меню", callback_data="main")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()


def delivery_choice_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🏬 Самовывоз из магазина", callback_data="dlv:Самовывоз")
    kb.button(text="🚚 Доставка курьером", callback_data="dlv:Доставка")
    kb.button(text="📦 Ozon", callback_data="dlv:Ozon")
    kb.adjust(1)
    return kb.as_markup()


def confirm_order_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить заказ", callback_data="confirm_order")
    kb.button(text="❌ Отменить", callback_data="main")
    kb.adjust(1)
    return kb.as_markup()


def skip_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Пропустить", callback_data="skip")
    return kb.as_markup()


def phone_request_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить мой номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# --------- ADMIN ---------
def admin_menu(is_super: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📦 Товары",            callback_data="adm:prods")
    kb.button(text="🗂 Категории",          callback_data="adm:cats")
    kb.button(text="🛒 Заказы",            callback_data="adm:orders")
    kb.button(text="📝 Тексты магазина",   callback_data="adm:texts")
    kb.button(text="💳 Реквизиты",         callback_data="adm:pay")
    kb.button(text="📊 Статистика",         callback_data="adm:stats")
    kb.button(text="📣 Рассылка",          callback_data="adm:broadcast")
    if is_super:
        kb.button(text="👥 Администраторы", callback_data="adm:admins")
    kb.button(text="← Закрыть", callback_data="main")
    if is_super:
        kb.adjust(2, 2, 2, 1, 1)
    else:
        kb.adjust(2, 2, 2, 1)
    return kb.as_markup()


def admin_categories_kb(categories: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for c in categories:
        kb.button(text=f"🗑 {c['name']}", callback_data=f"adm:delcat:{c['id']}")
    kb.button(text="➕ Добавить категорию", callback_data="adm:addcat")
    kb.button(text="← Назад", callback_data="adm:menu")
    kb.adjust(1)
    return kb.as_markup()


def admin_pick_category_kb(categories: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for c in categories:
        kb.button(text=c["name"], callback_data=f"adm:pickcat:{c['id']}")
    kb.button(text="← Отмена", callback_data="adm:menu")
    kb.adjust(2)
    return kb.as_markup()


def admin_pick_product_kb(products: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in products:
        kb.button(
            text=f"{p['name']} · {int(p['price'])} ₽",
            callback_data=f"adm:delprod:{p['id']}",
        )
    kb.button(text="← Назад", callback_data="adm:del_prod")
    kb.adjust(1)
    return kb.as_markup()


def admin_skip_or_cancel() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Пропустить", callback_data="adm:skip")
    kb.button(text="Отмена", callback_data="adm:menu")
    kb.adjust(2)
    return kb.as_markup()


def admin_confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Сохранить", callback_data="adm:save_prod")
    kb.button(text="❌ Отмена", callback_data="adm:menu")
    kb.adjust(2)
    return kb.as_markup()


def admin_payment_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Номер карты",     callback_data="adm:edpay:card")
    kb.button(text="✏️ Имя получателя",  callback_data="adm:edpay:holder")
    kb.button(text="✏️ Банк",            callback_data="adm:edpay:bank")
    kb.button(text="← Назад",            callback_data="adm:menu")
    kb.adjust(1)
    return kb.as_markup()


def order_admin_kb(order_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить оплату", callback_data=f"ord:pay:{order_id}")
    kb.button(text="❌ Отклонить",          callback_data=f"ord:reject:{order_id}")
    kb.adjust(1)
    return kb.as_markup()


def shipping_method_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🏬 Самовывоз",      callback_data="ship:pickup")
    kb.button(text="📮 Почта России",   callback_data="ship:post")
    kb.button(text="📦 Озон",           callback_data="ship:ozon")
    kb.adjust(1)
    return kb.as_markup()


def shipping_admin_kb(order_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Отметить отправленным", callback_data=f"ord:ship:{order_id}")
    kb.adjust(1)
    return kb.as_markup()


# --------- ADMIN: управление админами ---------
def admin_admins_kb(admins: list[dict], is_super: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for a in admins:
        label = f"@{a['username']}" if a.get("username") else f"id:{a['user_id']}"
        kb.button(text=f"🗑 {label}", callback_data=f"adm:rmadm:{a['user_id']}")
    if is_super:
        kb.button(text="➕ Добавить админа", callback_data="adm:addadm")
    kb.button(text="← Назад", callback_data="adm:menu")
    kb.adjust(1)
    return kb.as_markup()


# ============================================================
#          АДМИН-ПАНЕЛЬ : РАСШИРЕННОЕ РЕДАКТИРОВАНИЕ
# ============================================================
TEXT_FIELDS = [
    ("shop_name",          "🏷 Название магазина"),
    ("shop_addresses",     "📍 Адреса магазинов"),
    ("shop_schedule",      "🕐 График работы"),
    ("delivery_info",      "🚚 Информация о доставке"),
    ("payment_info",       "💳 Способы оплаты"),
    ("exchange_info",      "🔁 Обмен и возврат"),
    ("instagram_url",      "📷 Instagram URL"),
    ("operator_username",  "💬 Username оператора"),
]


def admin_texts_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, label in TEXT_FIELDS:
        kb.button(text=label, callback_data=f"adm:edtxt:{key}")
    kb.button(text="← Назад", callback_data="adm:menu")
    kb.adjust(1)
    return kb.as_markup()


def admin_products_filter_kb(categories: list[dict]) -> InlineKeyboardMarkup:
    """Список категорий для выбора, какие товары редактировать."""
    kb = InlineKeyboardBuilder()
    for c in categories:
        kb.button(text=c["name"], callback_data=f"adm:edcat:{c['id']}")
    kb.button(text="← Назад", callback_data="adm:menu")
    kb.adjust(2)
    return kb.as_markup()


def admin_products_list_kb(products: list[dict], cat_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in products:
        kb.button(
            text=f"#{p['id']} {p['name']} · {int(p['price'])} ₽",
            callback_data=f"adm:edprod:{p['id']}",
        )
    kb.button(text="← Назад", callback_data="adm:edprods")
    kb.adjust(1)
    return kb.as_markup()


PRODUCT_FIELDS = [
    ("name",        "Название"),
    ("price",       "Цена"),
    ("category_id", "Категория"),
    ("sizes",       "Размеры"),
    ("colors",      "Цвета"),
    ("material",    "Материал"),
    ("country",     "Страна"),
    ("description", "Описание"),
    ("photo_file_id", "Фото"),
]


def admin_product_edit_kb(product_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, label in PRODUCT_FIELDS:
        kb.button(text=f"✏️ {label}", callback_data=f"adm:edpfld:{product_id}:{key}")
    kb.button(text="🗑 Удалить товар", callback_data=f"adm:delprod:{product_id}")
    kb.button(text="← Назад", callback_data=f"adm:edprods")
    kb.adjust(2, 2, 2, 2, 1, 1, 1)
    return kb.as_markup()


def admin_category_pick_kb(categories: list[dict], product_id: int) -> InlineKeyboardMarkup:
    """Выбор новой категории для товара."""
    kb = InlineKeyboardBuilder()
    for c in categories:
        kb.button(text=c["name"], callback_data=f"adm:setcat:{product_id}:{c['id']}")
    kb.button(text="← Отмена", callback_data=f"adm:edprod:{product_id}")
    kb.adjust(2)
    return kb.as_markup()


def admin_categories_edit_kb(categories: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for c in categories:
        kb.button(text=f"✏️ {c['name']}", callback_data=f"adm:edcatname:{c['id']}")
    kb.button(text="➕ Новая категория", callback_data="adm:addcat")
    kb.button(text="🗑 Удалить категорию", callback_data="adm:delcat")
    kb.button(text="← Назад", callback_data="adm:menu")
    kb.adjust(2, 1, 1, 1)
    return kb.as_markup()


ORDER_STATUSES = [
    ("awaiting_payment", "⏳ Ожидают оплаты"),
    ("paid",             "💰 Оплачены"),
    ("shipping_chosen",  "📦 К отправке"),
    ("completed",        "✅ Завершены"),
    ("cancelled",        "❌ Отменены"),
]


def admin_orders_kb(counts: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for st, label in ORDER_STATUSES:
        n = counts.get(st, 0)
        kb.button(text=f"{label} ({n})", callback_data=f"adm:ords:{st}")
    kb.button(text="📋 Все заказы", callback_data="adm:ords:all")
    kb.button(text="← Назад", callback_data="adm:menu")
    kb.adjust(1)
    return kb.as_markup()


def admin_orders_list_kb(orders: list[dict], filter_st: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for o in orders[:20]:
        kb.button(
            text=f"#{o['id']} · {o['name']} · {int(o['total'])} ₽",
            callback_data=f"adm:ord:{o['id']}",
        )
    kb.button(text="← Назад", callback_data="adm:orders")
    kb.adjust(1)
    return kb.as_markup()


def admin_order_view_kb(order_id: int, status: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if status == "awaiting_payment":
        kb.button(text="✅ Подтвердить оплату", callback_data=f"ord:pay:{order_id}")
        kb.button(text="❌ Отменить заказ",     callback_data=f"adm:ordcanc:{order_id}")
    elif status == "paid":
        kb.button(text="📦 К отправке", callback_data=f"adm:setst:{order_id}:shipping_chosen")
        kb.button(text="❌ Отменить",   callback_data=f"adm:ordcanc:{order_id}")
    elif status == "shipping_chosen":
        kb.button(text="✅ Отметить отправленным", callback_data=f"adm:setst:{order_id}:completed")
        kb.button(text="❌ Отменить",              callback_data=f"adm:ordcanc:{order_id}")
    kb.button(text="← К списку", callback_data="adm:orders")
    kb.button(text="🏠 В админ-меню", callback_data="adm:menu")
    kb.adjust(1)
    return kb.as_markup()
