import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, TelegramObject

from bot.constants.keys import StorageKeys
from bot.entities.user import UserEntity

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """
    Middleware для проверки авторизации пользователя в HH.ru.

    Пропускает команды /start и /help без проверки.
    Для остальных команд проверяет наличие валидных токенов.
    """

    # Команды, которые не требуют авторизации
    PUBLIC_COMMANDS = {"/start", "/help"}
    PRIVATE_PATTERN = {
        re.compile(
            r"(?:https?://)?(?:[\w-]+\.)*hh\.ru/vacancy/(?P<vacancy_id>\d+)(?:[/?#][^\s.,!?)]*)?"
        )
    }

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        message: Message,
        data: dict[str, Any],
    ) -> Any:
        """
        Обработчик middleware.

        Args:
            handler: Следующий обработчик в цепочке
            message: Сообщение от Telegram
            data: Данные контекста

        Returns:
            Результат выполнения handler или None, если авторизация не пройдена
        """

        logger.debug("Обработка AuthMiddleware")
        # Проверяем сообщение на приватность
        check_match_to_patterns = any(
            bool(pattern.fullmatch(message.text)) for pattern in self.PRIVATE_PATTERN
        )
        if (
            any(message.text.startswith(cmd) for cmd in self.PUBLIC_COMMANDS)
            and not check_match_to_patterns
        ):
            logger.debug("Команда или паттерн не приватный")
            return await handler(message, data)

        logger.debug("Команда или паттерны приватный. Проверка авторизации пользователя")
        # Получаем FSM context
        state: FSMContext = data.get("state")
        data_state = await state.get_data()
        if StorageKeys.USER_INFO in data_state and data_state[StorageKeys.USER_INFO]:
            data_state[StorageKeys.USER_INFO] = UserEntity.model_validate_json(
                data_state[StorageKeys.USER_INFO]
            )
            logger.debug("Пользователь авторизован")
            return await handler(message, data)

        logger.debug("Пользователь %s не авторизован", message.from_user.username)
        await message.answer("Необходимо авторизоваться.\nИспользуйте команду /start для начала.")
        return None
