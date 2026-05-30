"""Точка входа. Запуск: python bot.py"""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import config
import database as db
from handlers_user import router as user_router
from handlers_admin import router as admin_router


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    log = logging.getLogger("bot")

    if not config.BOT_TOKEN:
        log.error("BOT_TOKEN не задан. Заполните .env")
        sys.exit(1)

    await db.init_db()
    log.info("База данных инициализирована: %s", config.DB_PATH)

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # admin router первым : приоритет команд /admin
    dp.include_router(admin_router)
    dp.include_router(user_router)

    me = await bot.get_me()
    log.info("Бот @%s (id=%s) запущен. Админы: %s", me.username, me.id, config.ADMIN_IDS)
    log.info("Откройте бота: https://t.me/%s", me.username)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\nБот остановлен.")
