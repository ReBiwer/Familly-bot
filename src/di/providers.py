"""
DI провайдеры для Dishka.

Этот модуль содержит провайдеры зависимостей для приложения.
Dishka автоматически разрешает зависимости и управляет их жизненным циклом.

Scope (область жизни):
- APP — создаётся один раз при старте приложения (singleton)
- REQUEST — создаётся на каждый HTTP запрос
- SESSION — для websocket сессий
"""

from collections.abc import AsyncGenerator

from dishka import Provider, Scope, provide
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.redis import AsyncRedisSaver
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import async_session_factory
from src.db.repositories import RefreshTokenRepository, UserRepository
from src.services.ai import AIService
from src.services.prompts import PromptService
from src.settings import app_settings
from src.use_cases import AuthTelegramUseCase, RefreshTokensTelegramUseCase


class ServicesProvider(Provider):
    """
    Провайдер сервисов приложения.

    Все сервисы создаются в scope APP — один экземпляр на всё приложение.
    Это оптимально для stateless сервисов и экономит ресурсы.
    """

    scope = Scope.APP

    @provide
    def get_prompt_service(self) -> PromptService:
        """
        Создаёт PromptService.

        PromptService загружает промпты из YAML файла один раз при создании.
        Путь к файлу и настройки (версия, статус) берутся из app_settings.

        Returns:
            PromptService: Singleton экземпляр сервиса промптов
        """
        return PromptService()

    @provide
    async def get_checkpointer(self) -> AsyncGenerator[BaseCheckpointSaver, None]:
        """
        Создаёт checkpointer для LangGraph в зависимости от режима работы.

        В DEBUG режиме:
        - Использует MemorySaver - хранит состояние в памяти
        - Быстрый старт, не требует Redis
        - История теряется при перезапуске приложения
        - Идеально для разработки и тестирования

        В PROD режиме:
        - Использует AsyncRedisSaver - хранит состояние в Redis
        - Персистентное хранение между перезапусками
        - TTL (время жизни) настраивается через app_settings.REDIS.CHECKPOINT_TTL
        - Масштабируемое решение для продакшена

        Почему AsyncGenerator:
        - AsyncRedisSaver требует async context manager для корректного закрытия
        - yield позволяет Dishka управлять жизненным циклом
        - При завершении приложения соединение корректно закрывается

        Yields:
            BaseCheckpointSaver: MemorySaver или Redis checkpointer для AIService
        """
        if app_settings.DEBUG:
            yield MemorySaver()
        else:
            # В продакшене используем Redis для персистентного хранения
            async with AsyncRedisSaver.from_conn_string(
                app_settings.REDIS.redis_url,
                ttl={"default_ttl": app_settings.REDIS.CHECKPOINT_TTL},
            ) as checkpointer:
                await checkpointer.asetup()
                yield checkpointer

    @provide
    def get_ai_service(
        self,
        checkpointer: BaseCheckpointSaver,
        prompt_service: PromptService,
    ) -> AIService:
        """
        Создаёт AIService с внедрёнными зависимостями.

        Dishka автоматически разрешает зависимости:
        - checkpointer берётся из get_checkpointer()
        - prompt_service берётся из get_prompt_service()

        Args:
            checkpointer: Redis checkpointer для сохранения диалогов
            prompt_service: Сервис для получения промптов

        Returns:
            AIService: Singleton экземпляр AI сервиса
        """
        return AIService(
            checkpointer=checkpointer,
            prompt_service=prompt_service,
        )


class DatabaseProvider(Provider):
    """
    Провайдер для работы с базой данных.

    Сессии создаются в scope REQUEST — новая сессия на каждый HTTP запрос.
    Это обеспечивает изоляцию транзакций между запросами.

    Репозитории также в scope REQUEST, т.к. зависят от сессии.
    """

    @provide(scope=Scope.REQUEST)
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Создаёт AsyncSession для работы с БД.

        Жизненный цикл:
        1. Создаётся новая сессия из фабрики
        2. yield — сессия используется в обработчике запроса
        3. commit() — если не было исключений
        4. rollback() — если было исключение
        5. close() — всегда закрываем сессию

        Yields:
            AsyncSession: Сессия SQLAlchemy для текущего запроса
        """
        async with async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @provide(scope=Scope.REQUEST)
    def get_user_repository(self, session: AsyncSession) -> UserRepository:
        """
        Создаёт UserRepository с инжектированной сессией.

        Args:
            session: AsyncSession из get_session()

        Returns:
            UserRepository для работы с пользователями
        """
        return UserRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_refresh_token_repository(self, session: AsyncSession) -> RefreshTokenRepository:
        return RefreshTokenRepository(session)


class UseCasesProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_auth_telegram_use_case(
        self, user_repo: UserRepository, refresh_token_repo: RefreshTokenRepository
    ) -> AuthTelegramUseCase:
        return AuthTelegramUseCase(user_repo, refresh_token_repo)

    @provide(scope=Scope.REQUEST)
    def get_refresh_tokens_telegram_use_case(
        self, user_repo: UserRepository, refresh_token_repo: RefreshTokenRepository
    ) -> RefreshTokensTelegramUseCase:
        return RefreshTokensTelegramUseCase(user_repo, refresh_token_repo)
