import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = [
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
]

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "store.db")

# Контакты / тексты магазина (правьте под себя)
SHOP_NAME = "LINGERIE BOUTIQUE"
SHOP_ADDRESSES = "📍 Grozny Mall, г. Грозный\n📍 (добавьте другие адреса в config.py)"
SHOP_SCHEDULE = "Ежедневно 10:00 : 22:00"
DELIVERY_INFO = (
    "🚚 Доставка по всей России\n"
    "• Самовывоз из магазина (бесплатно)\n"
    "• Курьер по Грозному\n"
    "• Ozon : отправка в любой город РФ\n"
    "• СДЭК / Почта России : по запросу"
)
PAYMENT_INFO = (
    "💳 Способы оплаты:\n"
    "• Наличные в магазине\n"
    "• Перевод по СБП / на карту\n"
    "• Оплата при получении (Ozon, СДЭК)"
)
EXCHANGE_INFO = (
    "🔁 Обмен и возврат:\n"
    "• Обмен размера : в течение 14 дней\n"
    "• Возврат возможен по закону РФ (товар нижнего белья : по согласованию)\n"
    "• Все подробности уточнит консультант"
)
INSTAGRAM_URL = "https://instagram.com/your_shop"  # замените на свой
OPERATOR_USERNAME = "@your_manager"  # замените на @username менеджера
