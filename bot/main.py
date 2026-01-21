import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram_dialog import setup_dialogs

from bot.common import setup_logging
from bot.di import init_di_container
from bot.routers import main_router
from bot.settings import bot_settings

logger = logging.getLogger(__name__)


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Старт"),
        BotCommand(command="help", description="Инфо о боте"),
        BotCommand(command="profile", description="Посмотреть свой профиль"),
        BotCommand(command="agents", description="Выбрать агента с которым хотите общаться")
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())
    logger.debug("Commands bot's set")


def create_storage():
    if not bot_settings.DEBUG:
        storage = RedisStorage.from_url(
            bot_settings.REDIS.redis_url,
            key_builder=DefaultKeyBuilder(with_destiny=True),
        )
    else:
        storage = MemoryStorage()
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
    setup_dialogs(dp)

    await bot.delete_webhook()

    await set_commands(bot)

    logger.debug("Bot started")
    setup_logging()
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_bot())
