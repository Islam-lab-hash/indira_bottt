"""Пользовательские хендлеры: главное меню, каталог, карточка товара, корзина, заказ, подбор, info."""
import os
from aiogram import F, Router, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    Message,
    InputMediaPhoto,
    FSInputFile,
    ReplyKeyboardRemove,
)

import database as db
import keyboards as kb
import config
from states import OrderForm, SelectorForm, OrderShipping

router = Router()

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def _photo_obj(photo_ref: str):
    """Возвращает FSInputFile для локального пути или строку-file_id для Telegram."""
    if photo_ref and os.path.exists(photo_ref):
        return FSInputFile(photo_ref)
    return photo_ref


async def _send_main_menu(message: Message):
    """Отправляет приветствие и главное меню (без фото)."""
    shop_name = await db.get_text("shop_name")
    text = (
        f"<b>{shop_name}</b>\n"
        "Натуральный шёлк · Premium · Turkey\n\n"
        "Выберите раздел:"
    )
    await message.answer(text, reply_markup=kb.main_menu())


async def _show_section(call: CallbackQuery, photo_name: str | None, caption: str, markup):
    """Показывает раздел с фото-баннером.
    Если текущее сообщение фото : меняем только подпись и кнопки (баннер остаётся).
    Если текст : удаляем и шлём новое сообщение с фото-баннером.
    """
    chat_id = call.from_user.id
    path = os.path.join(ASSETS_DIR, photo_name) if photo_name else None
    photo_exists = bool(path and os.path.exists(path))

    if call.message.photo:
        try:
            await call.message.edit_caption(caption=caption, reply_markup=markup)
            return
        except Exception:
            pass

    try:
        await call.message.delete()
    except Exception:
        pass

    if photo_exists:
        try:
            await call.bot.send_photo(chat_id, photo=FSInputFile(path), caption=caption, reply_markup=markup)
            return
        except Exception:
            pass
    await call.bot.send_message(chat_id, caption, reply_markup=markup)


async def _back_to_main_text(call: CallbackQuery):
    """Удаляет текущее сообщение и шлёт текстовое главное меню."""
    try:
        await call.message.delete()
    except Exception:
        pass
    shop_name = await db.get_text("shop_name")
    text = (
        f"<b>{shop_name}</b>\n"
        "Натуральный шёлк · Premium · Turkey\n\n"
        "Выберите раздел:"
    )
    await call.bot.send_message(call.from_user.id, text, reply_markup=kb.main_menu())


def _payment_block(pay: dict, total: int | float | None = None) -> str:
    lines = [
        "💳 <b>Реквизиты для оплаты</b>",
        f"Карта: <code>{pay['card']}</code>",
        f"Получатель: <b>{pay['holder']}</b>",
        f"Банк: <b>{pay['bank']}</b>",
    ]
    if total is not None:
        lines.append(f"\n💰 <b>К оплате: {int(total)} ₽</b>")
    lines.append("\n<i>После перевода пришлите чек менеджеру.</i>")
    return "\n".join(lines)


# ---------------- /start ----------------
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await db.upsert_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
    )
    await _send_main_menu(message)


@router.callback_query(F.data == "main")
async def to_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await _back_to_main_text(call)
    await call.answer()


# ---------------- КАТАЛОГ ----------------
@router.callback_query(F.data == "catalog")
async def show_catalog(call: CallbackQuery):
    cats = await db.list_categories()
    if not cats:
        await call.answer("Каталог пока пуст", show_alert=True)
        return
    await _show_section(
        call, "catalog.png",
        "<b>🗂 Каталог</b>\nВыберите категорию:",
        kb.categories_kb(cats),
    )
    await call.answer()


@router.callback_query(F.data.startswith("cat:"))
async def show_category(call: CallbackQuery):
    cat_id = int(call.data.split(":")[1])
    cat = await db.get_category(cat_id)
    if not cat:
        await call.answer("Категория не найдена", show_alert=True)
        return
    products = await db.list_products(cat_id)
    emo = kb.CATEGORY_EMOJI.get(cat["name"], "◾")
    if not products:
        await _show_section(
            call, "catalog.png",
            f"<b>{emo} {cat['name']}</b>\n\nПока нет товаров в этой категории.",
            kb.products_kb([], cat_id),
        )
        await call.answer()
        return
    await _show_section(
        call, "catalog.png",
        f"<b>{emo} {cat['name']}</b>\nВыберите товар:",
        kb.products_kb(products, cat_id),
    )
    await call.answer()


def _product_caption(p: dict) -> str:
    lines = [f"<b>{p['name']}</b>", f"💰 <b>{int(p['price'])} ₽</b>", ""]
    if p.get("sizes"):
        lines.append(f"📏 Размеры: {p['sizes']}")
    if p.get("colors"):
        lines.append(f"🎨 Цвета: {p['colors']}")
    if p.get("material"):
        lines.append(f"🧵 Материал: {p['material']}")
    if p.get("country"):
        lines.append(f"🌍 Страна: {p['country']}")
    if p.get("description"):
        lines.append(f"\n{p['description']}")
    return "\n".join(lines)


@router.callback_query(F.data.startswith("prod:"))
async def show_product(call: CallbackQuery, bot: Bot):
    pid = int(call.data.split(":")[1])
    p = await db.get_product(pid)
    if not p:
        await call.answer("Товар не найден", show_alert=True)
        return
    caption = _product_caption(p)
    markup = kb.product_card_kb(p["id"], p["category_id"])
    # удалить старое сообщение и прислать карточку
    try:
        await call.message.delete()
    except Exception:
        pass
    if p["photo_file_id"]:
        try:
            await bot.send_photo(
                call.from_user.id,
                photo=_photo_obj(p["photo_file_id"]),
                caption=caption,
                reply_markup=markup,
            )
        except Exception:
            await bot.send_message(call.from_user.id, caption, reply_markup=markup)
    else:
        await bot.send_message(call.from_user.id, caption, reply_markup=markup)
    await call.answer()


# ---------------- КОРЗИНА ----------------
@router.callback_query(F.data.startswith("add:"))
async def add_cart(call: CallbackQuery):
    pid = int(call.data.split(":")[1])
    await db.add_to_cart(call.from_user.id, pid, 1)
    await call.answer("✅ Добавлено в корзину")
    # Сразу показываем реквизиты и итоговую сумму
    items = await db.get_cart(call.from_user.id)
    total = sum(it["price"] * it["qty"] for it in items)
    pay = await db.get_payment_info()
    text = (
        "🛒 <b>Товар добавлен в корзину</b>\n\n"
        + _payment_block(pay, total)
    )
    await call.message.answer(text, reply_markup=kb.cart_kb(items))


@router.callback_query(F.data.startswith("rm:"))
async def remove_cart(call: CallbackQuery):
    pid = int(call.data.split(":")[1])
    await db.remove_from_cart(call.from_user.id, pid)
    await _render_cart(call)
    await call.answer("Удалено")


@router.callback_query(F.data == "clear_cart")
async def clear_cart_cb(call: CallbackQuery):
    await db.clear_cart(call.from_user.id)
    await _render_cart(call)
    await call.answer("Корзина очищена")


@router.callback_query(F.data == "cart")
async def cart_open(call: CallbackQuery):
    await _render_cart(call)
    await call.answer()


@router.callback_query(F.data == "cart:pay")
async def cart_pay_only(call: CallbackQuery):
    items = await db.get_cart(call.from_user.id)
    total = sum(it["price"] * it["qty"] for it in items) if items else 0
    pay = await db.get_payment_info()
    await call.message.answer(_payment_block(pay, total), reply_markup=kb.back_to_main())
    await call.answer()


async def _render_cart(call: CallbackQuery):
    items = await db.get_cart(call.from_user.id)
    if not items:
        text = "<b>🛒 Корзина пуста</b>\n\nДобавьте товары из каталога."
    else:
        total = sum(it["price"] * it["qty"] for it in items)
        lines = ["<b>🛒 Ваша корзина</b>\n"]
        for it in items:
            lines.append(
                f"• {it['name']} × {it['qty']} = {int(it['price'] * it['qty'])} ₽"
            )
        lines.append(f"\n<b>Итого: {int(total)} ₽</b>")
        pay = await db.get_payment_info()
        lines.append("\n" + _payment_block(pay))
        text = "\n".join(lines)
    await _show_section(call, "cart.png", text, kb.cart_kb(items))


# ---------------- ОФОРМЛЕНИЕ ЗАКАЗА ----------------
async def _notify_admins(bot: Bot, text: str, markup=None):
    """Шлёт уведомление всем админам : суперадминам из config + добавленным в БД."""
    ids = set(config.ADMIN_IDS)
    try:
        for a in await db.list_admins():
            ids.add(a["user_id"])
    except Exception:
        pass
    for uid in ids:
        try:
            await bot.send_message(uid, text, reply_markup=markup)
        except Exception:
            pass


@router.callback_query(F.data == "checkout")
async def checkout_start(call: CallbackQuery, state: FSMContext):
    items = await db.get_cart(call.from_user.id)
    if not items:
        await call.answer("Корзина пуста", show_alert=True)
        return
    await state.clear()
    await state.set_state(OrderForm.name)
    await call.message.answer("Введите ваше <b>имя</b>:")
    await call.answer()


@router.message(OrderForm.name)
async def order_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(OrderForm.phone)
    await message.answer(
        "Введите ваш <b>телефон</b> или отправьте контакт кнопкой ниже:",
        reply_markup=kb.phone_request_kb(),
    )


@router.message(OrderForm.phone, F.contact)
async def order_phone_contact(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await _ask_comment(message, state)


@router.message(OrderForm.phone)
async def order_phone_text(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await _ask_comment(message, state)


async def _ask_comment(message: Message, state: FSMContext):
    await state.set_state(OrderForm.comment)
    await message.answer(
        "Добавьте <b>комментарий</b> к заказу или нажмите «Пропустить»:",
        reply_markup=kb.skip_kb(),
    )
    # убрать reply-клавиатуру контакта
    try:
        await message.answer("⏳", reply_markup=ReplyKeyboardRemove())
    except Exception:
        pass


@router.callback_query(OrderForm.comment, F.data == "skip")
async def order_skip_comment(call: CallbackQuery, state: FSMContext):
    await state.update_data(comment="-")
    await _show_order_confirm(call.message, state, call.from_user.id)
    await call.answer()


@router.message(OrderForm.comment)
async def order_comment(message: Message, state: FSMContext):
    await state.update_data(comment=message.text.strip())
    await _show_order_confirm(message, state, message.from_user.id)


async def _show_order_confirm(message: Message, state: FSMContext, user_id: int):
    data = await state.get_data()
    items = await db.get_cart(user_id)
    total = sum(it["price"] * it["qty"] for it in items)
    items_text = "\n".join(
        f"• {it['name']} × {it['qty']} = {int(it['price'] * it['qty'])} ₽" for it in items
    )
    pay = await db.get_payment_info()
    text = (
        "<b>Проверьте заказ</b>\n\n"
        f"👤 Имя: {data['name']}\n"
        f"📞 Телефон: {data['phone']}\n"
        f"💬 Комментарий: {data.get('comment', '-')}\n\n"
        f"<b>Состав:</b>\n{items_text}\n\n"
        f"<b>Итого: {int(total)} ₽</b>\n\n"
        + _payment_block(pay, total)
    )
    await state.set_state(OrderForm.confirm)
    await message.answer(text, reply_markup=kb.confirm_order_kb())


@router.callback_query(OrderForm.confirm, F.data == "confirm_order")
async def order_confirm(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    items = await db.get_cart(call.from_user.id)
    if not items:
        await call.answer("Корзина пуста", show_alert=True)
        await state.clear()
        return
    total = sum(it["price"] * it["qty"] for it in items)
    items_text = "; ".join(f"{it['name']} ×{it['qty']}" for it in items)
    order_id = await db.create_order(
        {
            "user_id": call.from_user.id,
            "name": data["name"],
            "phone": data["phone"],
            "comment": data.get("comment", ""),
            "items": items_text,
            "total": total,
            "status": "awaiting_payment",
        }
    )
    await db.clear_cart(call.from_user.id)
    await state.clear()

    # уведомление менеджеру(ам) с кнопками подтверждения
    user = call.from_user
    contact = f"@{user.username}" if user.username else f"id:{user.id}"
    manager_text = (
        f"🆕 <b>Заказ #{order_id}</b> : ожидает оплаты\n\n"
        f"👤 {data['name']} ({contact})\n"
        f"📞 {data['phone']}\n"
        f"💬 {data.get('comment', '-')}\n\n"
        f"<b>{items_text}</b>\n"
        f"💰 <b>Итого: {int(total)} ₽</b>\n\n"
        "Проверьте поступление и подтвердите оплату:"
    )
    await _notify_admins(bot, manager_text, markup=kb.order_admin_kb(order_id))

    pay = await db.get_payment_info()
    await call.message.answer(
        f"✅ <b>Заказ #{order_id} создан</b>\n\n"
        + _payment_block(pay, total)
        + "\n\n⏳ Переведите сумму по реквизитам выше.\n"
        "Как только поступление будет проверено, мы пришлём подтверждение и попросим выбрать способ получения.",
        reply_markup=kb.back_to_main(),
    )
    await call.answer()


# ---------------- ВЫБОР ДОСТАВКИ (после подтверждения оплаты) ----------------
SHIPPING_NAMES = {
    "pickup": "🏬 Самовывоз",
    "post":   "📮 Почта России",
    "ozon":   "📦 Озон",
}


@router.callback_query(F.data.startswith("ship:"))
async def shipping_choose(call: CallbackQuery, state: FSMContext):
    method_key = call.data.split(":")[1]
    method = SHIPPING_NAMES.get(method_key)
    if not method:
        await call.answer("Неизвестный способ", show_alert=True); return
    # найти самый свежий paid-заказ этого пользователя
    order = await db.get_latest_user_order(call.from_user.id, status="paid")
    if not order:
        await call.answer("Не нашёл оплаченный заказ", show_alert=True); return
    await state.update_data(order_id=order["id"], ship_method=method, ship_key=method_key)
    if method_key == "pickup":
        await state.set_state(OrderShipping.pickup)
        await call.message.answer(
            f"🏬 <b>Самовывоз</b>\n\n{addresses}\n\n"
            "Напишите, из какого магазина удобно забрать (или просто подтвердите):",
        )
    else:
        await state.set_state(OrderShipping.address)
        prompt = (
            "📮 Напишите <b>полный адрес</b> доставки Почтой России\n"
            "(индекс, город, улица, дом, квартира, ФИО получателя):"
            if method_key == "post"
            else "📦 Напишите <b>город и адрес пункта выдачи Озон</b>\n(или индекс ПВЗ):"
        )
        await call.message.answer(prompt)
    await call.answer()


@router.message(OrderShipping.pickup)
async def shipping_pickup_save(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    address = message.text.strip()
    await _finalize_shipping(message, state, bot, data, address)


@router.message(OrderShipping.address)
async def shipping_address_save(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    address = message.text.strip()
    await _finalize_shipping(message, state, bot, data, address)


async def _finalize_shipping(message: Message, state: FSMContext, bot: Bot, data: dict, address: str):
    order_id = data.get("order_id")
    method = data.get("ship_method", "")
    if not order_id:
        await state.clear()
        await message.answer("Ошибка: заказ не найден.")
        return
    await db.update_order_delivery(order_id, method, address)
    await db.update_order_status(order_id, "shipping_chosen")
    await state.clear()

    order = await db.get_order(order_id)
    user = message.from_user
    contact = f"@{user.username}" if user.username else f"id:{user.id}"
    admin_text = (
        f"📦 <b>Заказ #{order_id} : к отправке</b>\n\n"
        f"👤 {order['name']} ({contact})\n"
        f"📞 {order['phone']}\n"
        f"🚚 Способ: <b>{method}</b>\n"
        f"📍 Адрес: {address}\n\n"
        f"<b>{order['items']}</b>\n"
        f"💰 Итого: {int(order['total'])} ₽"
    )
    await _notify_admins(bot, admin_text, markup=kb.shipping_admin_kb(order_id))

    await message.answer(
        f"✅ <b>Готово!</b>\n\n"
        f"Заказ #{order_id} : <b>{method}</b>\n"
        f"📍 {address}\n\n"
        "Мы свяжемся при отправке. Спасибо за покупку 🤍",
        reply_markup=kb.back_to_main(),
    )


# ---------------- ПОДБОР ----------------
@router.callback_query(F.data == "selector")
async def selector_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await _show_section(
        call, "selector.png",
        "<b>🎯 Подбор</b>\nКак удобнее подобрать?",
        kb.selector_kb(),
    )
    await call.answer()


@router.callback_query(F.data == "sel:size")
async def sel_size(call: CallbackQuery, state: FSMContext):
    await state.set_state(SelectorForm.size)
    await call.message.answer("Введите ваш размер (например, <b>S</b>, <b>M</b>, <b>44</b>):")
    await call.answer()


@router.message(SelectorForm.size)
async def sel_size_result(message: Message, state: FSMContext):
    size = message.text.strip()
    found = await db.search_products_by_size(size)
    await state.clear()
    if not found:
        await message.answer(
            f"По размеру <b>{size}</b> ничего не нашлось. Напишите консультанту:",
            reply_markup=kb.selector_kb(),
        )
        return
    await message.answer(f"Нашлось товаров: <b>{len(found)}</b>")
    for p in found[:10]:
        await _send_short_product(message, p)
    await message.answer("Готово ✅", reply_markup=kb.back_to_main())


@router.callback_query(F.data == "sel:color")
async def sel_color(call: CallbackQuery, state: FSMContext):
    await state.set_state(SelectorForm.color)
    await call.message.answer(
        "Введите цвет (белый, чёрный, графит, голубой и т.п.):"
    )
    await call.answer()


@router.message(SelectorForm.color)
async def sel_color_result(message: Message, state: FSMContext):
    color = message.text.strip()
    found = await db.search_products_by_color(color)
    await state.clear()
    if not found:
        await message.answer(
            f"По цвету <b>{color}</b> ничего не нашлось.",
            reply_markup=kb.selector_kb(),
        )
        return
    await message.answer(f"Нашлось товаров: <b>{len(found)}</b>")
    for p in found[:10]:
        await _send_short_product(message, p)
    await message.answer("Готово ✅", reply_markup=kb.back_to_main())


@router.callback_query(F.data == "sel:gift")
async def sel_gift(call: CallbackQuery):
    text = (
        "🎁 <b>Подарок</b>\n\n"
        "Напишите оператору : поможем подобрать комплект, добавим красивую упаковку "
        "и открытку. Бюджет и пожелания обсудим в личной переписке."
    )
    op = (await db.get_text("operator_username")).lstrip('@')
    op_kb = kb.InlineKeyboardBuilder()
    op_kb.button(text="💬 Написать оператору", url=f"https://t.me/{op}")
    op_kb.button(text="← Назад", callback_data="selector")
    op_kb.adjust(1)
    await _show_section(call, "selector.png", text, op_kb.as_markup())
    await call.answer()


@router.callback_query(F.data == "sel:cons")
async def sel_cons(call: CallbackQuery):
    text = (
        "💬 <b>Помощь консультанта</b>\n\n"
        "Опишите, что вы ищете, размер и предпочтения по цвету : "
        "консультант подберёт варианты лично."
    )
    op = (await db.get_text("operator_username")).lstrip('@')
    op_kb = kb.InlineKeyboardBuilder()
    op_kb.button(text="💬 Открыть чат", url=f"https://t.me/{op}")
    op_kb.button(text="← Назад", callback_data="selector")
    op_kb.adjust(1)
    await _show_section(call, "selector.png", text, op_kb.as_markup())
    await call.answer()


async def _send_short_product(message: Message, p: dict):
    caption = _product_caption(p)
    pk = kb.InlineKeyboardBuilder()
    pk.button(text="🛒 В корзину", callback_data=f"add:{p['id']}")
    pk.button(text="Открыть", callback_data=f"prod:{p['id']}")
    pk.adjust(2)
    if p["photo_file_id"]:
        try:
            await message.answer_photo(
                photo=_photo_obj(p["photo_file_id"]), caption=caption, reply_markup=pk.as_markup()
            )
        except Exception:
            await message.answer(caption, reply_markup=pk.as_markup())
    else:
        await message.answer(caption, reply_markup=pk.as_markup())


# ---------------- УТОЧНИТЬ РАЗМЕР / СПРОСИТЬ КОНСУЛЬТАНТА ----------------
@router.callback_query(F.data.startswith("ask_size:"))
async def ask_size_btn(call: CallbackQuery):
    pid = int(call.data.split(":")[1])
    p = await db.get_product(pid)
    if not p:
        await call.answer("Товар не найден", show_alert=True)
        return
    op = (await db.get_text("operator_username")).lstrip('@')
    await call.message.answer(
        f"📏 Уточнить размер по «{p['name']}» : напишите консультанту: "
        f"<a href='https://t.me/{op}'>@{op}</a>"
    )
    await call.answer()


@router.callback_query(F.data.startswith("ask_cons:"))
async def ask_cons_btn(call: CallbackQuery):
    pid = int(call.data.split(":")[1])
    p = await db.get_product(pid)
    if not p:
        await call.answer("Товар не найден", show_alert=True)
        return
    op = (await db.get_text("operator_username")).lstrip('@')
    await call.message.answer(
        f"💬 По товару «{p['name']}» : задайте вопрос консультанту: "
        f"<a href='https://t.me/{op}'>@{op}</a>"
    )
    await call.answer()


# ---------------- ИНФО ----------------
@router.callback_query(F.data == "info")
async def info_menu(call: CallbackQuery):
    shop_name = await db.get_text("shop_name")
    await _show_section(
        call, "info.png",
        f"<b>ℹ️ Информация</b>\n{shop_name}",
        kb.info_kb(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("info:"))
async def info_page(call: CallbackQuery):
    key = call.data.split(":")[1]
    op = (await db.get_text("operator_username")).lstrip('@')
    shop_name = await db.get_text("shop_name")
    shop_addresses = await db.get_text("shop_addresses")
    shop_schedule = await db.get_text("shop_schedule")
    delivery_info = await db.get_text("delivery_info")
    payment_info = await db.get_text("payment_info")
    exchange_info = await db.get_text("exchange_info")
    instagram_url = await db.get_text("instagram_url")
    texts = {
        "addr": f"<b>📍 Адреса и график</b>\n\n{shop_addresses}\n\n🕐 {shop_schedule}",
        "delivery": delivery_info,
        "pay": payment_info,
        "return": exchange_info,
        "inst": f"📷 <b>Instagram</b>\n{instagram_url}",
        "op": f"💬 <b>Связь с оператором</b>\n<a href='https://t.me/{op}'>@{op}</a>",
    }
    text = texts.get(key, "Раздел в разработке")
    back = kb.InlineKeyboardBuilder()
    back.button(text="← Назад", callback_data="info")
    back.button(text="← В меню", callback_data="main")
    back.adjust(2)
    await _show_section(call, "info.png", text, back.as_markup())
    await call.answer()
