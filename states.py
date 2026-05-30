from aiogram.fsm.state import State, StatesGroup


class OrderForm(StatesGroup):
    name = State()
    phone = State()
    city = State()
    delivery = State()
    comment = State()
    confirm = State()


class SelectorForm(StatesGroup):
    size = State()
    color = State()
    gift = State()
    consultant = State()


class AdminAddProduct(StatesGroup):
    category = State()
    name = State()
    price = State()
    sizes = State()
    colors = State()
    material = State()
    country = State()
    description = State()
    photo = State()
    confirm = State()


class AdminAddCategory(StatesGroup):
    name = State()


class AdminBroadcast(StatesGroup):
    text = State()
    confirm = State()


class AdminEditPayment(StatesGroup):
    value = State()


class OrderShipping(StatesGroup):
    method = State()
    pickup = State()
    address = State()


class AdminManageAdmins(StatesGroup):
    add_id = State()
