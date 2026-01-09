from typing import cast

from aiogram.fsm.context import FSMContext
from aiogram.types import TelegramObject, User
from dishka import Provider, Scope, provide
from dishka.integrations.aiogram import AiogramMiddlewareData

from bot.adapters import BackendAdapter
from bot.constants import KeyState
from bot.schemas import TokenPair, UserProfile


class CommonProvider(Provider):
    """
    Провайдер для общих зависимостей, которые нужны в разных частях приложения.
    """

    scope = Scope.REQUEST

    @provide(scope=Scope.REQUEST)
    def get_fsm_context(self, middleware_data: AiogramMiddlewareData) -> FSMContext:
        """
        Извлекаем FSMContext из middleware data.

        AiogramProvider предоставляет только TelegramObject и AiogramMiddlewareData (словарь).
        FSMContext находится внутри этого словаря под ключом "state".
        Aiogram автоматически добавляет его туда через FSMContextMiddleware.
        """
        return middleware_data["state"]

    @provide(scope=Scope.REQUEST)
    def get_telegram_user(self, event: TelegramObject) -> User:
        """
        Получаем объект User из Telegram события.
        Это базовые данные пользователя из самого Telegram API.
        """
        user = getattr(event, "from_user", None)
        if not user:
            raise ValueError(f"Event {type(event)} does not have 'from_user' attribute")
        return user


class AdaptersProviders(Provider):
    scope = Scope.REQUEST

    @provide()
    async def get_profile_user(self, state: FSMContext) -> UserProfile | None:
        data = await state.get_data()
        profile_data = data.get(KeyState.USER_PROFILE, None)
        if profile_data:
            return UserProfile.model_validate_json(profile_data)
        return None

    @provide
    async def get_tokens_pair(self, state: FSMContext) -> TokenPair | None:
        data = await state.get_data()
        tokens_data = data.get(KeyState.TOKENS, None)
        if tokens_data:
            return TokenPair.model_validate_json(tokens_data)
        return None

    @provide()
    def backend_provider(
        self,
        tg_user: User,  # Базовые данные из Telegram API (всегда есть)
        user_read: UserProfile | None,  # Расширенные данные из нашей БД (может отсутствовать)
        tokens: TokenPair | None,
    ) -> BackendAdapter:
        """
        Создаём BackendAdapter с данными пользователя.

        Используем:
        - tg_user (User из Telegram) для обязательных полей (id, first_name, last_name)
        - user_read (UserRead из БД) для дополнительных полей (mid_name и т.д.)

        Это гарантирует, что адаптер создастся даже для новых пользователей.
        """
        return BackendAdapter(
            telegram_id=tg_user.id,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
            mid_name=user_read.mid_name if user_read else None,
            tokens=tokens,
        )
