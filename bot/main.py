import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, BotCommandScopeDefault

from bot.common import setup_logging
from bot.di import init_di_container
from bot.routers import main_router
from bot.settings import bot_settings

logger = logging.getLogger(__name__)


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🚀 Старт / Авторизация"),
        BotCommand(command="help", description="❓ Помощь"),
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())
    logger.debug("Commands bot's set")


def create_storage():
    storage = RedisStorage.from_url(
        bot_settings.REDIS.redis_url,
    )
    logger.debug("Redis storage created")
    return storage


async def run_bot():
    bot = Bot(
        token=bot_settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    storage = create_storage()

    dp = Dispatcher(storage=storage)

    init_di_container(dp)

    dp.include_router(main_router)

    await bot.delete_webhook()

    await set_commands(bot)

    logger.debug("Bot started")
    setup_logging()
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_bot())
