import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, BotCommandScopeDefault

from bot.di import init_di_containers
from bot.middlewares import AuthMiddleware
from bot.routers import main_router
from bot.settings import bot_settings

logger = logging.getLogger(__name__)


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🚀 Старт / Авторизация"),
        BotCommand(command="help", description="❓ Помощь"),
        BotCommand(command="profile", description="👤 Мой профиль HH"),
        BotCommand(command="vacancies", description="💼 Поиск вакансий"),
        BotCommand(command="logout", description="🚪 Выход"),
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())
    logger.debug("Commands bot's set")


def create_storage():
    # Проверяем, настроен ли Redis
    if bot_settings.REDIS.HOST and bot_settings.REDIS.PORT:
        storage = RedisStorage.from_url(
            bot_settings.REDIS.redis_url,
        )
        logger.debug("Redis storage created")
        return storage
    else:
        return MemoryStorage()


async def run_bot():
    bot = Bot(
        token=bot_settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Создаем хранилище
    storage = create_storage()

    # Создаем dispatcher с хранилищем
    dp = Dispatcher(storage=storage)

    # Удаляем webhook, если он был установлен ранее
    # Это важно при переключении с webhook на polling
    await bot.delete_webhook()

    # Подключаем роутеры
    # Порядок важен! Первые роутеры обрабатываются раньше
    dp.include_router(main_router)
    dp.message.middleware(AuthMiddleware())
    init_di_containers(dp)

    # Устанавливаем команды бота
    await set_commands(bot)

    # Запускаем polling
    # skip_updates=True - пропускаем сообщения, которые пришли пока бот был оффлайн
    logger.debug("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_bot())
