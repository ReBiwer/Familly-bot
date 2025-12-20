"""
Тесты для API эндпоинта /auth/telegram.

Используем:
- httpx.AsyncClient для async тестов FastAPI
- Dishka с тестовым провайдером (подменяем реальную БД на in-memory SQLite)

Почему не TestClient:
- TestClient из starlette синхронный
- httpx.AsyncClient позволяет делать async тесты, что лучше для async FastAPI
"""

import hashlib
import hmac
from collections.abc import AsyncGenerator

import pytest
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api import auth_router
from src.db.models import BaseModel
from src.db.repositories import RefreshTokenRepository, UserRepository
from src.settings import app_settings
from src.use_cases import AuthTelegramUseCase


class MockDatabaseProvider(Provider):
    """
    Тестовый провайдер БД.

    Подменяет реальную PostgreSQL на in-memory SQLite.
    Каждый тест получает чистую БД.

    Почему отдельный Provider:
    - Изолируем тестовую конфигурацию от продакшн
    - Можно легко подменить на мок при необходимости
    - Dishka сам управляет жизненным циклом сессии

    Почему не TestDatabaseProvider:
    - pytest пытается собрать классы с префиксом Test* как тестовые
    """

    def __init__(self, session: AsyncSession):
        """
        Args:
            session: Готовая AsyncSession (создаётся в фикстуре async_session)
        """
        super().__init__()
        self._session = session

    @provide(scope=Scope.REQUEST)
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Возвращает тестовую сессию.

        Используем yield, потому что Dishka ожидает генератор для REQUEST scope.
        После yield Dishka закроет scope и освободит ресурсы.
        """
        yield self._session

    @provide(scope=Scope.REQUEST)
    def get_user_repository(self, session: AsyncSession) -> UserRepository:
        return UserRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_refresh_token_repository(self, session: AsyncSession) -> RefreshTokenRepository:
        return RefreshTokenRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_auth_telegram_use_case(
        self,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository,
    ) -> AuthTelegramUseCase:
        return AuthTelegramUseCase(user_repo, refresh_token_repo)


def create_test_app() -> FastAPI:
    """
    Создаёт минимальное FastAPI приложение для тестов.

    Включает только auth_router — не нужно тащить всё приложение.
    Это ускоряет тесты и изолирует тестируемый функционал.
    """
    app = FastAPI()
    app.include_router(auth_router)
    return app


@pytest.fixture
async def test_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Создаёт in-memory SQLite сессию для тестов API.

    Почему отдельная от conftest.py:
    - API тесты требуют полную изоляцию
    - Каждый API тест получает свою чистую БД
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def test_client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Создаёт httpx.AsyncClient с тестовым DI контейнером.

    Как работает:
    1. Создаём FastAPI app без DI
    2. Создаём тестовый контейнер с TestDatabaseProvider
    3. Подключаем контейнер к app через setup_dishka
    4. Создаём AsyncClient с ASGITransport

    Почему ASGITransport:
    - Позволяет тестировать ASGI app напрямую без запуска сервера
    - Быстрее и надёжнее, чем запуск реального HTTP сервера
    """
    app = create_test_app()

    # Создаём тестовый контейнер с подменённой БД
    container = make_async_container(MockDatabaseProvider(test_session))
    setup_dishka(container, app)

    # httpx AsyncClient с ASGI транспортом
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    # Закрываем контейнер
    await container.close()


class TestAuthTelegramEndpoint:
    """Тесты для POST /auth/telegram."""

    def _create_valid_request_data(self) -> dict:
        """
        Создаёт валидные данные для запроса.

        HMAC подпись вычисляется так же, как на клиенте —
        это гарантирует, что запрос пройдёт проверку в use case.
        """
        name = "Владимир"
        mid_name = "Николаевич"
        last_name = "Быков"
        telegram_id = 123456

        msg = f"name={name}\nmid_name={mid_name}\nlast_name={last_name}\ntelegram_id={telegram_id}"
        hash_str = hmac.new(
            key=app_settings.FRONT.BOT_TOKEN.encode(),
            msg=msg.encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()

        return {
            "name": name,
            "mid_name": mid_name,
            "last_name": last_name,
            "telegram_id": telegram_id,
            "hash_str": hash_str,
        }

    async def test_auth_telegram_success(self, test_client: AsyncClient):
        """
        Успешная авторизация через Telegram.

        Проверяем:
        - Статус 200
        - Наличие access_token и refresh_token в ответе
        - expires_in > 0
        """
        data = self._create_valid_request_data()

        response = await test_client.post("/auth/telegram", json=data)

        assert response.status_code == status.HTTP_200_OK

        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert "expires_in" in body
        assert body["expires_in"] > 0
        assert len(body["access_token"]) > 0
        assert len(body["refresh_token"]) > 0

    async def test_auth_telegram_invalid_signature(self, test_client: AsyncClient):
        """
        Авторизация с невалидной подписью должна вернуть 401.

        Это защита от подделки запросов — если hash_str не совпадает
        с вычисленным на сервере, запрос отклоняется.
        """
        data = self._create_valid_request_data()
        data["hash_str"] = "invalid_hash_string_that_will_not_match"

        response = await test_client.post("/auth/telegram", json=data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_auth_telegram_missing_fields(self, test_client: AsyncClient):
        """
        Запрос без обязательных полей должен вернуть 422 (Validation Error).

        FastAPI/Pydantic автоматически валидирует входные данные
        и возвращает 422 если схема не соответствует.
        """
        # Отправляем пустой JSON
        response = await test_client.post("/auth/telegram", json={})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_auth_telegram_partial_fields(self, test_client: AsyncClient):
        """
        Запрос с частичными данными должен вернуть 422.
        """
        data = {
            "name": "Владимир",
            "telegram_id": 123456,
            # Нет hash_str и других полей
        }

        response = await test_client.post("/auth/telegram", json=data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_auth_telegram_creates_user(self, test_client: AsyncClient, test_session: AsyncSession):
        """
        Проверяем, что авторизация создаёт пользователя в БД.

        После успешной авторизации должен появиться пользователь
        с указанным telegram_id.
        """
        data = self._create_valid_request_data()

        response = await test_client.post("/auth/telegram", json=data)
        assert response.status_code == status.HTTP_200_OK

        # Проверяем, что пользователь создан
        user_repo = UserRepository(test_session)
        user = await user_repo.get_by_telegram_id(data["telegram_id"])

        assert user is not None
        assert user.name == data["name"]
        assert user.telegram_id == data["telegram_id"]

    async def test_auth_telegram_existing_user(self, test_client: AsyncClient, test_session: AsyncSession):
        """
        Повторная авторизация существующего пользователя.

        Должен вернуть новые токены, но не создавать дубликат пользователя.
        """
        data = self._create_valid_request_data()

        # Первая авторизация
        response1 = await test_client.post("/auth/telegram", json=data)
        assert response1.status_code == status.HTTP_200_OK

        # Вторая авторизация того же пользователя
        response2 = await test_client.post("/auth/telegram", json=data)
        assert response2.status_code == status.HTTP_200_OK

        # Проверяем, что пользователь только один
        user_repo = UserRepository(test_session)
        users = await user_repo.get_many(telegram_id=data["telegram_id"])

        assert len(users) == 1

    async def test_auth_telegram_response_schema(self, test_client: AsyncClient):
        """
        Проверяем, что ответ соответствует схеме TokenPair.

        Это важно для контракта API — клиент ожидает определённую структуру.
        """
        data = self._create_valid_request_data()

        response = await test_client.post("/auth/telegram", json=data)
        body = response.json()

        # Проверяем типы полей
        assert isinstance(body["access_token"], str)
        assert isinstance(body["refresh_token"], str)
        assert isinstance(body["expires_in"], int)
        assert isinstance(body["token_type"], str)

        # Проверяем, что нет лишних полей
        expected_keys = {"access_token", "refresh_token", "expires_in", "token_type"}
        assert set(body.keys()) == expected_keys

        # Проверяем значение token_type
        assert body["token_type"] == "bearer"

