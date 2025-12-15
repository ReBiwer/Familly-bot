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
from langgraph.checkpoint.redis import AsyncRedisSaver
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import async_session_factory
from src.db.repositories import UserRepository
from src.services.ai import AIService
from src.services.prompts import PromptService
from src.settings import app_settings


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
        Создаёт Redis checkpointer для LangGraph.

        Checkpointer сохраняет состояние диалогов в Redis.
        TTL (время жизни) настраивается через app_settings.REDIS.CHECKPOINT_TTL.

        Почему AsyncGenerator:
        - AsyncRedisSaver требует async context manager для корректного закрытия
        - yield позволяет Dishka управлять жизненным циклом
        - При завершении приложения соединение корректно закрывается

        Yields:
            BaseCheckpointSaver: Redis checkpointer для AIService
        """
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
