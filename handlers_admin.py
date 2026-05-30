"""Админ-панель: добавление/удаление товаров и категорий, статистика, рассылка."""
from aiogram import F, Router, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import database as db
import keyboards as kb
import config
from states import (
    AdminAddProduct,
    AdminAddCategory,
    AdminBroadcast,
    AdminEditPayment,
    AdminManageAdmins,
)

router = Router()


def is_super(user_id: int) -> bool:
    """Суперадмин : тот, кто прописан в config.ADMIN_IDS. Только он может управлять другими админами."""
    return user_id in config.ADMIN_IDS


async def is_admin(user_id: int) -> bool:
    """Полный админ-доступ : суперадмин из config или добавленный в БД."""
    if is_super(user_id):
        return True
    return await db.is_db_admin(user_id)


# ---------- ВХОД В АДМИНКУ ----------
@router.message(Command("admin"))
async def admin_entry(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа.")
        return
    await state.clear()
    await message.answer(
        "<b>Админ-панель</b>\nВыберите действие:",
        reply_markup=kb.admin_menu(is_super=is_super(message.from_user.id)),
    )


@router.callback_query(F.data == "adm:menu")
async def adm_menu(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    await state.clear()
    markup = kb.admin_menu(is_super=is_super(call.from_user.id))
    try:
        await call.message.edit_text("<b>Админ-панель</b>\nВыберите действие:", reply_markup=markup)
    except Exception:
        await call.message.answer("<b>Админ-панель</b>\nВыберите действие:", reply_markup=markup)
    await call.answer()


# ---------- СТАТИСТИКА ----------
@router.callback_query(F.data == "adm:stats")
async def adm_stats(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    s = await db.get_stats()
    text = (
        "<b>📊 Статистика</b>\n\n"
        f"👥 Пользователей: <b>{s['users']}</b>\n"
        f"📁 Категорий: <b>{s['categories']}</b>\n"
        f"🛍 Товаров: <b>{s['products']}</b>\n"
        f"🧾 Заказов: <b>{s['orders']}</b>"
    )
    back = kb.InlineKeyboardBuilder()
    back.button(text="← Назад", callback_data="adm:menu")
    await call.message.edit_text(text, reply_markup=back.as_markup())
    await call.answer()


# ---------- КАТЕГОРИИ ----------
@router.callback_query(F.data == "adm:cats")
async def adm_cats(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    cats = await db.list_categories()
    text = "<b>Категории</b>\nНажмите для удаления, либо добавьте новую:"
    if not cats:
        text = "<b>Категорий пока нет.</b>"
    await call.message.edit_text(text, reply_markup=kb.admin_categories_kb(cats))
    await call.answer()


@router.callback_query(F.data == "adm:addcat")
async def adm_addcat(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    await state.set_state(AdminAddCategory.name)
    await call.message.answer("Введите название новой категории:")
    await call.answer()


@router.message(AdminAddCategory.name)
async def adm_addcat_save(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    name = message.text.strip()
    if not name:
        await message.answer("Пустое имя. Введите ещё раз:")
        return
    try:
        await db.add_category(name)
        await message.answer(f"✅ Категория «{name}» добавлена.", reply_markup=kb.admin_menu())
    except Exception as e:
        await message.answer(f"Ошибка: {e}", reply_markup=kb.admin_menu())
    await state.clear()


@router.callback_query(F.data.startswith("adm:delcat:"))
async def adm_delcat(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    cat_id = int(call.data.split(":")[2])
    await db.delete_category(cat_id)
    cats = await db.list_categories()
    await call.message.edit_text(
        "Категория удалена. ✅\n\n<b>Категории:</b>",
        reply_markup=kb.admin_categories_kb(cats),
    )
    await call.answer("Удалено")


# ---------- ДОБАВЛЕНИЕ ТОВАРА ----------
@router.callback_query(F.data == "adm:add_prod")
async def adm_add_prod(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    cats = await db.list_categories()
    if not cats:
        await call.answer("Сначала создайте категорию", show_alert=True)
        return
    await state.set_state(AdminAddProduct.category)
    await call.message.edit_text(
        "Шаг 1/9. Выберите категорию для нового товара:",
        reply_markup=kb.admin_pick_category_kb(cats),
    )
    await call.answer()


@router.callback_query(AdminAddProduct.category, F.data.startswith("adm:pickcat:"))
async def adm_pick_cat(call: CallbackQuery, state: FSMContext):
    cat_id = int(call.data.split(":")[2])
    await state.update_data(category_id=cat_id)
    await state.set_state(AdminAddProduct.name)
    await call.message.answer("Шаг 2/9. Введите <b>название</b> товара:")
    await call.answer()


@router.message(AdminAddProduct.name)
async def adm_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AdminAddProduct.price)
    await message.answer("Шаг 3/9. Введите <b>цену</b> (число, ₽):")


@router.message(AdminAddProduct.price)
async def adm_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(",", ".").strip())
    except ValueError:
        await message.answer("Не похоже на число. Введите цену ещё раз:")
        return
    await state.update_data(price=price)
    await state.set_state(AdminAddProduct.sizes)
    await message.answer(
        "Шаг 4/9. <b>Размеры в наличии</b> через запятую (например: <code>S, M, L</code>):",
        reply_markup=kb.admin_skip_or_cancel(),
    )


@router.message(AdminAddProduct.sizes)
async def adm_sizes(message: Message, state: FSMContext):
    await state.update_data(sizes=message.text.strip())
    await state.set_state(AdminAddProduct.colors)
    await message.answer(
        "Шаг 5/9. <b>Цвета</b> через запятую (например: <code>белый, чёрный, графит</code>):",
        reply_markup=kb.admin_skip_or_cancel(),
    )


@router.message(AdminAddProduct.colors)
async def adm_colors(message: Message, state: FSMContext):
    await state.update_data(colors=message.text.strip())
    await state.set_state(AdminAddProduct.material)
    await message.answer(
        "Шаг 6/9. <b>Материал</b> (например: <code>100% натуральный шёлк</code>):",
        reply_markup=kb.admin_skip_or_cancel(),
    )


@router.message(AdminAddProduct.material)
async def adm_material(message: Message, state: FSMContext):
    await state.update_data(material=message.text.strip())
    await state.set_state(AdminAddProduct.country)
    await message.answer(
        "Шаг 7/9. <b>Страна производства</b> (например: <code>Turkey</code>):",
        reply_markup=kb.admin_skip_or_cancel(),
    )


@router.message(AdminAddProduct.country)
async def adm_country(message: Message, state: FSMContext):
    await state.update_data(country=message.text.strip())
    await state.set_state(AdminAddProduct.description)
    await message.answer(
        "Шаг 8/9. Краткое <b>описание</b> товара:",
        reply_markup=kb.admin_skip_or_cancel(),
    )


@router.message(AdminAddProduct.description)
async def adm_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(AdminAddProduct.photo)
    await message.answer(
        "Шаг 9/9. Пришлите <b>фото</b> товара (или нажмите «Пропустить»):",
        reply_markup=kb.admin_skip_or_cancel(),
    )


# универсальный skip в любом шаге добавления товара
@router.callback_query(F.data == "adm:skip")
async def adm_skip(call: CallbackQuery, state: FSMContext):
    current = await state.get_state()
    mapping = {
        AdminAddProduct.sizes.state: ("sizes", AdminAddProduct.colors, "Шаг 5/9. Цвета через запятую:"),
        AdminAddProduct.colors.state: ("colors", AdminAddProduct.material, "Шаг 6/9. Материал:"),
        AdminAddProduct.material.state: ("material", AdminAddProduct.country, "Шаг 7/9. Страна производства:"),
        AdminAddProduct.country.state: ("country", AdminAddProduct.description, "Шаг 8/9. Описание товара:"),
        AdminAddProduct.description.state: ("description", AdminAddProduct.photo, "Шаг 9/9. Пришлите фото (или «Пропустить»):"),
        AdminAddProduct.photo.state: ("photo_file_id", None, None),
    }
    if current not in mapping:
        await call.answer()
        return
    key, next_state, prompt = mapping[current]
    await state.update_data(**{key: ""})
    if next_state is None:
        await _adm_confirm_product(call.message, state)
    else:
        await state.set_state(next_state)
        await call.message.answer(prompt, reply_markup=kb.admin_skip_or_cancel())
    await call.answer()


@router.message(AdminAddProduct.photo, F.photo)
async def adm_photo(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(photo_file_id=file_id)
    await _adm_confirm_product(message, state)


@router.message(AdminAddProduct.photo)
async def adm_photo_skip_text(message: Message, state: FSMContext):
    # любой текст в шаге фото : считаем как «пропустить»
    await state.update_data(photo_file_id="")
    await _adm_confirm_product(message, state)


async def _adm_confirm_product(message: Message, state: FSMContext):
    data = await state.get_data()
    cat = await db.get_category(data["category_id"])
    cat_name = cat["name"] if cat else "?"
    text = (
        "<b>Проверьте товар:</b>\n\n"
        f"📁 Категория: <b>{cat_name}</b>\n"
        f"📦 Название: <b>{data.get('name','')}</b>\n"
        f"💰 Цена: <b>{int(data.get('price', 0))} ₽</b>\n"
        f"📏 Размеры: {data.get('sizes', '-') or '-'}\n"
        f"🎨 Цвета: {data.get('colors', '-') or '-'}\n"
        f"🧵 Материал: {data.get('material', '-') or '-'}\n"
        f"🌍 Страна: {data.get('country', '-') or '-'}\n"
        f"📝 Описание: {data.get('description', '-') or '-'}\n"
        f"🖼 Фото: {'есть' if data.get('photo_file_id') else 'нет'}"
    )
    await state.set_state(AdminAddProduct.confirm)
    await message.answer(text, reply_markup=kb.admin_confirm_kb())


@router.callback_query(AdminAddProduct.confirm, F.data == "adm:save_prod")
async def adm_save(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pid = await db.add_product(data)
    await state.clear()
    await call.message.edit_text(
        f"✅ Товар #{pid} «{data['name']}» добавлен.", reply_markup=kb.admin_menu()
    )
    await call.answer("Сохранено")


# ---------- УДАЛЕНИЕ ТОВАРА ----------
@router.callback_query(F.data == "adm:del_prod")
async def adm_del_prod(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    cats = await db.list_categories()
    text = "Выберите категорию, из которой удалить товар:"
    builder = kb.InlineKeyboardBuilder()
    for c in cats:
        builder.button(text=c["name"], callback_data=f"adm:delprodcat:{c['id']}")
    builder.button(text="← Назад", callback_data="adm:menu")
    builder.adjust(2)
    await call.message.edit_text(text, reply_markup=builder.as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("adm:delprodcat:"))
async def adm_del_prod_cat(call: CallbackQuery):
    cat_id = int(call.data.split(":")[2])
    products = await db.list_products(cat_id)
    if not products:
        await call.answer("В этой категории нет товаров", show_alert=True)
        return
    await call.message.edit_text(
        "Выберите товар для удаления:",
        reply_markup=kb.admin_pick_product_kb(products),
    )
    await call.answer()


@router.callback_query(F.data.startswith("adm:delprod:"))
async def adm_delprod(call: CallbackQuery):
    pid = int(call.data.split(":")[2])
    await db.delete_product(pid)
    await call.message.edit_text(
        f"✅ Товар #{pid} удалён.", reply_markup=kb.admin_menu()
    )
    await call.answer("Удалено")


# ---------- РАССЫЛКА ----------
@router.callback_query(F.data == "adm:broadcast")
async def adm_broadcast(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True)
        return
    await state.set_state(AdminBroadcast.text)
    await call.message.answer(
        "Пришлите текст рассылки (можно с HTML-разметкой).\n"
        "Будет отправлено всем пользователям бота."
    )
    await call.answer()


@router.message(AdminBroadcast.text)
async def adm_broadcast_send(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    text = message.html_text if message.html_text else message.text
    user_ids = await db.get_all_user_ids()
    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, text)
            sent += 1
        except Exception:
            failed += 1
    await state.clear()
    await message.answer(
        f"📣 Рассылка завершена.\nОтправлено: <b>{sent}</b>\nОшибок: <b>{failed}</b>",
        reply_markup=kb.admin_menu(),
    )

# ---------- РЕКВИЗИТЫ ОПЛАТЫ ----------
PAY_FIELDS = {
    "card":   ("pay_card",   "номер карты"),
    "holder": ("pay_holder", "имя получателя"),
    "bank":   ("pay_bank",   "название банка"),
}


async def _show_payment(target, state: FSMContext | None = None):
    if state is not None:
        await state.clear()
    pay = await db.get_payment_info()
    text = (
        "<b>💳 Реквизиты для оплаты</b>\n\n"
        f"Карта: <code>{pay['card']}</code>\n"
        f"Получатель: <b>{pay['holder']}</b>\n"
        f"Банк: <b>{pay['bank']}</b>\n\n"
        "Выберите поле для изменения:"
    )
    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=kb.admin_payment_kb())
        except Exception:
            await target.message.answer(text, reply_markup=kb.admin_payment_kb())
    else:
        await target.answer(text, reply_markup=kb.admin_payment_kb())


@router.callback_query(F.data == "adm:pay")
async def adm_pay(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    await _show_payment(call, state)
    await call.answer()


@router.callback_query(F.data.startswith("adm:edpay:"))
async def adm_edpay(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    field = call.data.split(":")[2]
    if field not in PAY_FIELDS:
        await call.answer("Неизвестное поле", show_alert=True); return
    key, label = PAY_FIELDS[field]
    await state.set_state(AdminEditPayment.value)
    await state.update_data(pay_key=key, pay_label=label)
    await call.message.answer(f"Введите новое значение для поля «<b>{label}</b>»:")
    await call.answer()


@router.message(AdminEditPayment.value, F.photo)
async def adm_universal_save_photo(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    data = await state.get_data()
    kind = data.get("setting_kind", "payment")
    if kind != "product" or data.get("product_field") != "photo_file_id":
        await message.answer("Ожидался текст, а не фото.")
        return
    file_id = message.photo[-1].file_id
    pid = data.get("product_id")
    await db.update_product(pid, photo_file_id=file_id)
    await state.clear()
    await message.answer("✅ Фото обновлено")
    # вернуться к карточке
    p = await db.get_product(pid)
    if p:
        text = (
            f"<b>#{p['id']} {p['name']}</b>\n"
            f"💰 {int(p['price'])} ₽\n"
            f"📐 {p.get('sizes','-') or '-'}\n"
            f"🎨 {p.get('colors','-') or '-'}\n"
            f"🧵 {p.get('material','-') or '-'}\n"
            f"🌍 {p.get('country','-') or '-'}\n"
            f"\n{p.get('description','') or ''}\n\nЧто меняем?"
        )
        await message.answer(text, reply_markup=kb.admin_product_edit_kb(pid))


@router.message(AdminEditPayment.value)
async def adm_universal_save(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    data = await state.get_data()
    value = (message.text or "").strip()
    kind = data.get("setting_kind", "payment")

    if kind == "payment":
        key = data.get("pay_key")
        label = data.get("pay_label", "значение")
        if not key:
            await state.clear(); return
        if not value:
            await message.answer("Пустое значение, попробуйте ещё раз:"); return
        await db.set_setting(key, value)
        await state.clear()
        await message.answer(f"✅ Сохранено: <b>{label}</b> = <code>{value}</code>")
        await _show_payment(message)
        return

    if kind == "text":
        key = data.get("setting_key")
        label = data.get("setting_label", key)
        if not key or not value:
            await message.answer("Пустое значение, попробуйте ещё раз:"); return
        await db.set_setting(key, value)
        await state.clear()
        await message.answer(
            f"✅ Сохранено: <b>{label}</b>\n<code>{value}</code>",
            reply_markup=kb.admin_texts_kb(),
        )
        return

    if kind == "category":
        cid = data.get("category_id")
        if not cid or not value:
            await message.answer("Пустое значение, попробуйте ещё раз:"); return
        await db.rename_category(cid, value)
        await state.clear()
        cats = await db.list_categories()
        await message.answer(
            f"✅ Категория переименована: <b>{value}</b>",
            reply_markup=kb.admin_categories_edit_kb(cats),
        )
        return

    if kind == "product":
        pid = data.get("product_id")
        field = data.get("product_field")
        label = data.get("setting_label", field)
        if not pid or not field:
            await state.clear(); return
        if field == "photo_file_id":
            await message.answer("📷 Нужно прислать фото, а не текст.")
            return
        if not value:
            await message.answer("Пустое значение, попробуйте ещё раз:"); return
        save_val: object = value
        if field == "price":
            try:
                save_val = float(value.replace(",", ".").replace(" ", ""))
            except ValueError:
                await message.answer("Цена должна быть числом, например 4990. Попробуйте ещё раз:")
                return
        await db.update_product(pid, **{field: save_val})
        await state.clear()
        await message.answer(f"✅ <b>{label}</b> обновлено.")
        p = await db.get_product(pid)
        if p:
            text = (
                f"<b>#{p['id']} {p['name']}</b>\n"
                f"💰 {int(p['price'])} ₽\n"
                f"📐 {p.get('sizes','-') or '-'}\n"
                f"🎨 {p.get('colors','-') or '-'}\n"
                f"🧵 {p.get('material','-') or '-'}\n"
                f"🌍 {p.get('country','-') or '-'}\n"
                f"\n{p.get('description','') or ''}\n\nЧто меняем?"
            )
            await message.answer(text, reply_markup=kb.admin_product_edit_kb(pid))
        return

    await state.clear()


# ============================================================
#                УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ
# ============================================================
@router.callback_query(F.data == "adm:admins")
async def adm_admins(call: CallbackQuery, state: FSMContext):
    if not is_super(call.from_user.id):
        await call.answer("⛔ Только для суперадмина", show_alert=True); return
    await state.clear()
    admins = await db.list_admins()
    lines = ["<b>👥 Администраторы</b>\n"]
    lines.append(f"⭐ Суперадмин: <code>{config.ADMIN_IDS[0]}</code> (из config.py)")
    if admins:
        lines.append("\n<b>Добавленные через бот:</b>")
        for a in admins:
            u = f"@{a['username']}" if a.get("username") else "(без username)"
            lines.append(f"• <code>{a['user_id']}</code> {u}")
    else:
        lines.append("\nДругих админов нет.")
    text = "\n".join(lines)
    try:
        await call.message.edit_text(text, reply_markup=kb.admin_admins_kb(admins, True))
    except Exception:
        await call.message.answer(text, reply_markup=kb.admin_admins_kb(admins, True))
    await call.answer()


@router.callback_query(F.data == "adm:addadm")
async def adm_addadm(call: CallbackQuery, state: FSMContext):
    if not is_super(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    await state.set_state(AdminManageAdmins.add_id)
    await call.message.answer(
        "Введите <b>Telegram ID</b> пользователя, которого хотите сделать админом.\n\n"
        "💡 Узнать ID: пользователь должен написать боту <code>/myid</code> или переслать "
        "своё сообщение в @userinfobot."
    )
    await call.answer()


@router.message(AdminManageAdmins.add_id)
async def adm_addadm_save(message: Message, state: FSMContext, bot: Bot):
    if not is_super(message.from_user.id):
        await state.clear(); return
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("❌ Это не число. Введите числовой Telegram ID.")
        return
    uid = int(raw)
    if uid in config.ADMIN_IDS:
        await message.answer("Этот пользователь уже суперадмин.")
        await state.clear(); return
    # попробуем подтянуть username из таблицы users
    username = ""
    try:
        u = await db.get_user(uid)
        if u and u.get("username"):
            username = u["username"]
    except Exception:
        pass
    await db.add_admin(uid, added_by=message.from_user.id, username=username)
    await state.clear()
    await message.answer(f"✅ Пользователь <code>{uid}</code> назначен админом.")
    # уведомить нового админа
    try:
        await bot.send_message(
            uid,
            "🎉 Вам выданы права <b>администратора</b>.\nНаберите /admin, чтобы открыть панель.",
        )
    except Exception:
        pass
    # вернуться в список
    admins = await db.list_admins()
    await message.answer(
        "<b>👥 Администраторы</b>",
        reply_markup=kb.admin_admins_kb(admins, True),
    )


@router.callback_query(F.data.startswith("adm:rmadm:"))
async def adm_rmadm(call: CallbackQuery, bot: Bot):
    if not is_super(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    uid = int(call.data.split(":")[2])
    await db.remove_admin(uid)
    await call.answer(f"Админ {uid} удалён")
    try:
        await bot.send_message(uid, "Ваши права администратора отозваны.")
    except Exception:
        pass
    # перерисовать список
    admins = await db.list_admins()
    try:
        await call.message.edit_reply_markup(reply_markup=kb.admin_admins_kb(admins, True))
    except Exception:
        pass


# ============================================================
#         ПОДТВЕРЖДЕНИЕ ОПЛАТЫ / ОТКЛОНЕНИЕ / ОТПРАВКА
# ============================================================
@router.callback_query(F.data.startswith("ord:pay:"))
async def ord_confirm_pay(call: CallbackQuery, bot: Bot):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    order_id = int(call.data.split(":")[2])
    order = await db.get_order(order_id)
    if not order:
        await call.answer("Заказ не найден", show_alert=True); return
    if order["status"] != "awaiting_payment":
        await call.answer(f"Статус уже: {order['status']}", show_alert=True); return
    await db.update_order_status(order_id, "paid")
    # обновить сообщение админа
    try:
        await call.message.edit_text(
            call.message.html_text + f"\n\n✅ <b>Оплата подтверждена</b> ({call.from_user.full_name})",
            reply_markup=None,
        )
    except Exception:
        pass
    await call.answer("✅ Оплата подтверждена")
    # уведомить покупателя : выбрать способ получения
    try:
        await bot.send_message(
            order["user_id"],
            f"✅ <b>Оплата по заказу #{order_id} подтверждена!</b>\n\n"
            "Выберите способ получения товара:",
            reply_markup=kb.shipping_method_kb(),
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("ord:reject:"))
async def ord_reject(call: CallbackQuery, bot: Bot):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    order_id = int(call.data.split(":")[2])
    order = await db.get_order(order_id)
    if not order:
        await call.answer("Заказ не найден", show_alert=True); return
    await db.update_order_status(order_id, "cancelled")
    try:
        await call.message.edit_text(
            call.message.html_text + f"\n\n❌ <b>Заказ отклонён</b> ({call.from_user.full_name})",
            reply_markup=None,
        )
    except Exception:
        pass
    await call.answer("Заказ отклонён")
    try:
        await bot.send_message(
            order["user_id"],
            f"❌ <b>Заказ #{order_id} отклонён.</b>\n\n"
            "Оплата не поступила. Если это ошибка : напишите оператору.",
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("ord:ship:"))
async def ord_ship(call: CallbackQuery, bot: Bot):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    order_id = int(call.data.split(":")[2])
    order = await db.get_order(order_id)
    if not order:
        await call.answer("Заказ не найден", show_alert=True); return
    await db.update_order_status(order_id, "completed")
    try:
        await call.message.edit_text(
            call.message.html_text + f"\n\n📦 <b>Отправлено</b> ({call.from_user.full_name})",
            reply_markup=None,
        )
    except Exception:
        pass
    await call.answer("Заказ отмечен как отправленный")
    try:
        await bot.send_message(
            order["user_id"],
            f"📦 Ваш заказ <b>#{order_id}</b> отправлен!\nСпасибо за покупку 🤍",
        )
    except Exception:
        pass


# ============================================================
#                      ТЕКСТЫ МАГАЗИНА
# ============================================================
class _AnyEditText(AdminEditPayment):
    pass  # переиспользуем состояние value


@router.callback_query(F.data == "adm:texts")
async def adm_texts(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    await state.clear()
    text = (
        "<b>📝 Тексты магазина</b>\n\n"
        "Выберите, какой текст изменить:"
    )
    try:
        await call.message.edit_text(text, reply_markup=kb.admin_texts_kb())
    except Exception:
        await call.message.answer(text, reply_markup=kb.admin_texts_kb())
    await call.answer()


@router.callback_query(F.data.startswith("adm:edtxt:"))
async def adm_edtxt(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    key = call.data.split(":")[2]
    label = dict(kb.TEXT_FIELDS).get(key, key)
    current = await db.get_setting(key, "")
    await state.set_state(AdminEditPayment.value)
    await state.update_data(setting_key=key, setting_label=label, setting_kind="text")
    await call.message.answer(
        f"✏️ <b>{label}</b>\n\nТекущее значение:\n<code>{current}</code>\n\n"
        "Пришлите новый текст одним сообщением.\nИли /cancel чтобы отменить."
    )
    await call.answer()


# Универсальный приёмник изменений текстов (включая реквизиты)
# Оригинальный adm_edpay_save уже принимает AdminEditPayment.value, перепишем его
# чтобы он умел работать и с обычными текстами : по полю setting_kind в state data.


@router.message(Command("cancel"))
async def cancel_any(message: Message, state: FSMContext):
    if await state.get_state():
        await state.clear()
        await message.answer("Отменено.", reply_markup=kb.admin_menu(is_super(message.from_user.id)))


# ============================================================
#                    КАТЕГОРИИ : РЕДАКТИРОВАНИЕ
# ============================================================
@router.callback_query(F.data == "adm:cats")
async def adm_cats(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    await state.clear()
    cats = await db.list_categories()
    text = "<b>🗂 Категории</b>\n\nВыберите категорию для переименования или используйте кнопки ниже:"
    try:
        await call.message.edit_text(text, reply_markup=kb.admin_categories_edit_kb(cats))
    except Exception:
        await call.message.answer(text, reply_markup=kb.admin_categories_edit_kb(cats))
    await call.answer()


@router.callback_query(F.data.startswith("adm:edcatname:"))
async def adm_edcatname(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    cat_id = int(call.data.split(":")[2])
    c = await db.get_category(cat_id)
    if not c:
        await call.answer("Категория не найдена", show_alert=True); return
    await state.set_state(AdminEditPayment.value)
    await state.update_data(setting_kind="category", category_id=cat_id, setting_label=c["name"])
    await call.message.answer(
        f"✏️ Переименование категории «{c['name']}».\n\nПришлите новое название одним сообщением."
    )
    await call.answer()


# ============================================================
#                       ТОВАРЫ : РЕДАКТИРОВАНИЕ
# ============================================================
@router.callback_query(F.data == "adm:prods")
async def adm_prods(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    await state.clear()
    text = "<b>📦 Товары</b>\n\nЧто делаем?"
    pkb = kb.InlineKeyboardBuilder()
    pkb.button(text="➕ Добавить товар",  callback_data="adm:add_prod")
    pkb.button(text="✏️ Редактировать",  callback_data="adm:edprods")
    pkb.button(text="🗑 Удалить",        callback_data="adm:del_prod")
    pkb.button(text="← Назад",          callback_data="adm:menu")
    pkb.adjust(1)
    try:
        await call.message.edit_text(text, reply_markup=pkb.as_markup())
    except Exception:
        await call.message.answer(text, reply_markup=pkb.as_markup())
    await call.answer()


@router.callback_query(F.data == "adm:edprods")
async def adm_edprods(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    await state.clear()
    cats = await db.list_categories()
    text = "<b>✏️ Редактировать товары</b>\n\nВыберите категорию:"
    try:
        await call.message.edit_text(text, reply_markup=kb.admin_products_filter_kb(cats))
    except Exception:
        await call.message.answer(text, reply_markup=kb.admin_products_filter_kb(cats))
    await call.answer()


@router.callback_query(F.data.startswith("adm:edcat:"))
async def adm_edcat(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    cat_id = int(call.data.split(":")[2])
    cat = await db.get_category(cat_id)
    prods = await db.list_products(cat_id)
    text = f"<b>{cat['name']}</b>\nТоваров: {len(prods)}\n\nВыберите товар для редактирования:"
    try:
        await call.message.edit_text(text, reply_markup=kb.admin_products_list_kb(prods, cat_id))
    except Exception:
        await call.message.answer(text, reply_markup=kb.admin_products_list_kb(prods, cat_id))
    await call.answer()


@router.callback_query(F.data.startswith("adm:edprod:"))
async def adm_edprod(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    await state.clear()
    pid = int(call.data.split(":")[2])
    p = await db.get_product(pid)
    if not p:
        await call.answer("Не найден", show_alert=True); return
    text = (
        f"<b>#{p['id']} {p['name']}</b>\n"
        f"💰 {int(p['price'])} ₽\n"
        f"📐 {p.get('sizes', '-') or '-'}\n"
        f"🎨 {p.get('colors', '-') or '-'}\n"
        f"🧵 {p.get('material', '-') or '-'}\n"
        f"🌍 {p.get('country', '-') or '-'}\n"
        f"\n{p.get('description', '') or ''}\n\n"
        "Что меняем?"
    )
    try:
        await call.message.edit_text(text, reply_markup=kb.admin_product_edit_kb(pid))
    except Exception:
        await call.message.answer(text, reply_markup=kb.admin_product_edit_kb(pid))
    await call.answer()


@router.callback_query(F.data.startswith("adm:edpfld:"))
async def adm_edpfld(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    _, _, pid_s, field = call.data.split(":")
    pid = int(pid_s)
    if field == "category_id":
        cats = await db.list_categories()
        await call.message.answer(
            "Выберите новую категорию для товара:",
            reply_markup=kb.admin_category_pick_kb(cats, pid),
        )
        await call.answer(); return
    label = dict(kb.PRODUCT_FIELDS).get(field, field)
    await state.set_state(AdminEditPayment.value)
    await state.update_data(setting_kind="product", product_id=pid, product_field=field, setting_label=label)
    if field == "photo_file_id":
        await call.message.answer(
            "📷 Пришлите новое <b>фото</b> товара одной картинкой.\n/cancel чтобы отменить."
        )
    elif field == "price":
        await call.message.answer(
            f"✏️ Новая <b>{label.lower()}</b> (число в рублях, например 4990).\n/cancel чтобы отменить."
        )
    else:
        await call.message.answer(
            f"✏️ Новое значение для поля <b>{label}</b>.\n/cancel чтобы отменить."
        )
    await call.answer()


@router.callback_query(F.data.startswith("adm:setcat:"))
async def adm_setcat(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    _, _, pid_s, cid_s = call.data.split(":")
    pid, cid = int(pid_s), int(cid_s)
    await db.update_product(pid, category_id=cid)
    await call.answer("✅ Категория изменена")
    # вернуться к карточке товара
    call.data = f"adm:edprod:{pid}"
    await adm_edprod(call, state)


# ============================================================
#       УНИВЕРСАЛЬНЫЙ ПРИЁМНИК ИЗМЕНЕНИЙ (тексты, товары, реквизиты)
# ============================================================
# Перехватчик идёт ПОСЛЕ существующего adm_edpay_save : aiogram запускает
# первый подошедший хэндлер. Поэтому переопределим adm_edpay_save :
# он уже сидит на AdminEditPayment.value. Нужно либо удалить его, либо
# модифицировать, чтобы поддерживал все ветки.


# ============================================================
#                          ЗАКАЗЫ
# ============================================================
def _order_text(o: dict) -> str:
    status_label = dict(kb.ORDER_STATUSES).get(o["status"], o["status"])
    return (
        f"<b>Заказ #{o['id']}</b> · {status_label}\n"
        f"👤 {o['name']}\n"
        f"📞 <code>{o['phone']}</code>\n"
        f"🛍 {o['items']}\n"
        f"💰 <b>{int(o['total'])} ₽</b>\n"
        f"💬 {o.get('comment') or '-'}\n"
        f"🚚 {o.get('delivery') or '-'}\n"
        f"📍 {o.get('city') or '-'}\n"
        f"🕐 {o.get('created_at') or '-'}"
    )


@router.callback_query(F.data == "adm:orders")
async def adm_orders(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    await state.clear()
    counts = await db.order_stats_by_status()
    text = "<b>🛒 Заказы</b>\n\nВыберите фильтр по статусу:"
    try:
        await call.message.edit_text(text, reply_markup=kb.admin_orders_kb(counts))
    except Exception:
        await call.message.answer(text, reply_markup=kb.admin_orders_kb(counts))
    await call.answer()


@router.callback_query(F.data.startswith("adm:ords:"))
async def adm_ords_list(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    st = call.data.split(":")[2]
    status = None if st == "all" else st
    orders = await db.list_orders(status=status, limit=30)
    label = dict(kb.ORDER_STATUSES).get(st, "Все заказы")
    if not orders:
        text = f"<b>{label}</b>\n\nЗаказов нет."
    else:
        text = f"<b>{label}</b>\nНайдено: {len(orders)}\n\nВыберите заказ:"
    try:
        await call.message.edit_text(text, reply_markup=kb.admin_orders_list_kb(orders, st))
    except Exception:
        await call.message.answer(text, reply_markup=kb.admin_orders_list_kb(orders, st))
    await call.answer()


@router.callback_query(F.data.startswith("adm:ord:"))
async def adm_ord_view(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    oid = int(call.data.split(":")[2])
    o = await db.get_order(oid)
    if not o:
        await call.answer("Заказ не найден", show_alert=True); return
    try:
        await call.message.edit_text(_order_text(o), reply_markup=kb.admin_order_view_kb(oid, o["status"]))
    except Exception:
        await call.message.answer(_order_text(o), reply_markup=kb.admin_order_view_kb(oid, o["status"]))
    await call.answer()


@router.callback_query(F.data.startswith("adm:setst:"))
async def adm_setst(call: CallbackQuery, bot: Bot):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    _, _, oid_s, status = call.data.split(":")
    oid = int(oid_s)
    await db.update_order_status(oid, status)
    o = await db.get_order(oid)
    if o:
        # уведомить покупателя
        try:
            label = dict(kb.ORDER_STATUSES).get(status, status)
            await bot.send_message(o["user_id"], f"📦 Статус вашего заказа #{oid}: <b>{label}</b>")
        except Exception:
            pass
        try:
            await call.message.edit_text(_order_text(o), reply_markup=kb.admin_order_view_kb(oid, o["status"]))
        except Exception:
            pass
    await call.answer("✅ Статус обновлён")


@router.callback_query(F.data.startswith("adm:ordcanc:"))
async def adm_ord_cancel(call: CallbackQuery, bot: Bot):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔", show_alert=True); return
    oid = int(call.data.split(":")[2])
    await db.update_order_status(oid, "cancelled")
    o = await db.get_order(oid)
    if o:
        try:
            await bot.send_message(
                o["user_id"],
                f"❌ Заказ #{oid} отменён. Если это ошибка, свяжитесь с оператором."
            )
        except Exception:
            pass
        try:
            await call.message.edit_text(_order_text(o), reply_markup=kb.admin_order_view_kb(oid, o["status"]))
        except Exception:
            pass
    await call.answer("Отменён")
