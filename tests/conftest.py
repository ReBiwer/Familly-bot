"""
Общие фикстуры для тестов.

Этот файл автоматически загружается pytest.
Фикстуры доступны во всех тестах без импорта.
"""

import hashlib
import hmac
import os
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.schemas import RefreshTelegramRequest, TelegramAuthRequest
from src.settings import app_settings
from src.use_cases import AuthTelegramUseCase, RefreshTokensTelegramUseCase

# Устанавливаем тестовые переменные окружения ДО импорта settings
# Это нужно, чтобы AppSettings не падал при загрузке
os.environ.setdefault("HOST", "localhost")
os.environ.setdefault("PORT", "8000")
os.environ.setdefault("AUTH__JWT_TOKEN", "test_jwt_secret")
os.environ.setdefault("DB__USER", "test")
os.environ.setdefault("DB__PASS", "test")
os.environ.setdefault("DB__HOST", "localhost")
os.environ.setdefault("DB__NAME", "test_db")
os.environ.setdefault("REDIS__HOST", "localhost")
os.environ.setdefault("REDIS__PORT", "6379")
os.environ.setdefault("REDIS__CHECKPOINT_NUM_DB", "0")
os.environ.setdefault("HH__CLIENT_ID", "test")
os.environ.setdefault("HH__CLIENT_SECRET", "test")
os.environ.setdefault("HH__REDIRECT_URI", "http://localhost")
os.environ.setdefault("LLM__MODEL", "test-model")
os.environ.setdefault("LLM__API_KEY", "test-key")
os.environ.setdefault("FRONT__BOT_USERNAME", "test_bot")

# Теперь можно импортировать из src
from src.db.models import BaseModel, RefreshTokenModel, UserModel  # noqa: E402
from src.db.repositories import RefreshTokenRepository, UserRepository  # noqa: E402
from src.utils import create_refresh_token  # noqa: E402


@pytest.fixture
def temp_prompts_file(tmp_path: Path) -> Path:
    """
    Создаёт временный файл промптов для тестов.

    Возвращает путь к файлу с тестовыми промптами.
    """
    prompts_content = """
prompts:
  # Системный промпт по умолчанию для AIService
  - name: "system_default"
    version: "1.0"
    status: "dev"
    description: "Системный промпт для тестов"
    input_variables: []
    template: "Ты тестовый AI-ассистент."

  - name: "test_prompt"
    version: "1.0"
    status: "prod"
    description: "Тестовый промпт"
    input_variables: []
    template: "Это тестовый промпт"

  - name: "test_with_vars"
    version: "1.0"
    status: "prod"
    description: "Промпт с переменными"
    input_variables:
      - user_name
      - topic
    template: "Привет, {user_name}! Тема: {topic}"

  - name: "dev_prompt"
    version: "1.0"
    status: "dev"
    description: "Промпт в разработке"
    input_variables: []
    template: "Dev промпт"

  - name: "versioned_prompt"
    version: "1.0"
    status: "prod"
    description: "Версия 1.0"
    input_variables: []
    template: "Версия 1.0"

  - name: "versioned_prompt"
    version: "2.0"
    status: "prod"
    description: "Версия 2.0"
    input_variables: []
    template: "Версия 2.0"
"""
    file_path = tmp_path / "test_prompts.yaml"
    file_path.write_text(prompts_content, encoding="utf-8")
    return file_path


@pytest.fixture
async def async_session() -> AsyncSession:
    """
    Создаёт in-memory SQLite сессию для тестов.

    Использует SQLite в памяти — быстро и не требует внешней БД.
    Таблицы создаются заново для каждого теста.
    """
    # SQLite в памяти для тестов
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Создаём таблицы
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    # Создаём сессию
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        yield session

    # Удаляем таблицы после теста
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)

    await engine.dispose()


# =============================================================================
# Фикстуры для UserRepository
# =============================================================================


@pytest.fixture
def user_repo(async_session: AsyncSession) -> UserRepository:
    """
    Репозиторий пользователей.

    Почему фикстура:
    - Убирает дублирование `UserRepository(async_session)` в каждом тесте
    - Единая точка создания — если конструктор изменится, правим только здесь
    """
    return UserRepository(async_session)


@pytest.fixture
async def sample_user(user_repo: UserRepository) -> UserModel:
    """
    Базовый тестовый пользователь.

    Используй когда нужен 'просто какой-то существующий пользователь'
    для тестирования операций чтения/обновления/удаления.

    НЕ используй в тестах, которые проверяют создание пользователя
    или работу с несуществующим пользователем.
    """
    return await user_repo.create(
        name="Тест",
        mid_name="Тестович",
        last_name="Тестов",
        telegram_id=100500,
        email="test@example.com",
        role="member",
    )


@pytest.fixture
def user_factory(user_repo: UserRepository) -> Callable[..., Awaitable[UserModel]]:
    """
    Фабрика для создания пользователей с кастомными данными.

    Почему фабрика, а не просто фикстура:
    - Некоторые тесты требуют несколько пользователей
    - Каждый пользователь может иметь уникальные данные (telegram_id, email)
    - Фикстура sample_user создаёт только одного пользователя

    Пример использования:
        async def test_something(user_factory):
            user1 = await user_factory(name="Иван", telegram_id=111)
            user2 = await user_factory(name="Пётр", telegram_id=222)

    Как работает:
    - defaults содержит обязательные поля со значениями по умолчанию
    - kwargs перезаписывает/дополняет defaults
    - Результат передаётся в repo.create()
    """

    async def _create(**kwargs) -> UserModel:
        # Значения по умолчанию для обязательных полей
        defaults = {
            "name": "Тест",
            "mid_name": "Тестович",
            "last_name": "Тестов",
        }
        # Перезаписываем/дополняем переданными значениями
        defaults.update(kwargs)
        return await user_repo.create(**defaults)

    return _create


# =============================================================================
# Фикстуры для RefreshTokenRepository
# =============================================================================


@pytest.fixture
def refresh_token_repo(async_session: AsyncSession) -> RefreshTokenRepository:
    """Репозиторий refresh-токенов."""
    return RefreshTokenRepository(async_session)


@pytest.fixture
async def sample_refresh_token(
    refresh_token_repo: RefreshTokenRepository,
    sample_user: UserModel,
) -> RefreshTokenModel:
    """
    Базовый тестовый refresh-токен.

    Автоматически создаёт sample_user (через зависимость фикстур).
    """
    return await refresh_token_repo.create(
        token_hash=create_refresh_token(),
        user_id=sample_user.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
        device_info="test_device",
    )


@pytest.fixture()
def auth_telegram_use_case(
    user_repo: UserRepository, refresh_token_repo: RefreshTokenRepository
) -> AuthTelegramUseCase:
    return AuthTelegramUseCase(user_repo, refresh_token_repo)


@pytest.fixture()
def sample_telegram_auth_request() -> TelegramAuthRequest:
    name = "Владимир"
    mid_name = "Николаевич"
    last_name = "Быков"
    telegram_id = 1111
    msg_to_hmac = (
        f"telegram_id={telegram_id}\nname={name}\nmid_name={mid_name}\nlast_name={last_name}"
    )
    hmac_hash_str = hmac.new(
        key=app_settings.FRONT.BOT_TOKEN.encode(),
        msg=msg_to_hmac.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return TelegramAuthRequest(
        first_name="Владимир",
        mid_name="Николаевич",
        last_name="Быков",
        telegram_id=1111,
        hash_str=hmac_hash_str,
    )


# =============================================================================
# Фикстуры для RefreshTokensTelegramUseCase
# =============================================================================


@pytest.fixture()
def refresh_tokens_use_case(
    user_repo: UserRepository, refresh_token_repo: RefreshTokenRepository
) -> RefreshTokensTelegramUseCase:
    """
    Use case для обновления токенов.

    Почему отдельная фикстура:
    - Тот же паттерн, что и auth_telegram_use_case
    - Внедряем те же репозитории, но другой use case
    """
    return RefreshTokensTelegramUseCase(user_repo, refresh_token_repo)


@pytest.fixture()
def sample_refresh_request_factory(
    sample_user: UserModel,
) -> Callable[[str], RefreshTelegramRequest]:
    """
    Фабрика для создания RefreshTelegramRequest.

    Почему фабрика:
    - refresh_token каждый раз разный (генерируется при авторизации)
    - Нужно передавать актуальный токен из БД

    Пример:
        request = sample_refresh_request_factory("actual_token_from_db")
    """

    def _create(refresh_token: str) -> RefreshTelegramRequest:
        return RefreshTelegramRequest(
            telegram_id=sample_user.telegram_id,
            refresh_token=refresh_token,
        )

    return _create


@pytest.fixture()
def refresh_token_in_db_factory(
    refresh_token_repo: RefreshTokenRepository,
    sample_user: UserModel,
) -> Callable[..., Awaitable[tuple[str, RefreshTokenModel]]]:
    """
    Фабрика для создания refresh_token в БД.

    Возвращает tuple (token_hash, token_record), чтобы тест мог использовать оба.

    Почему фабрика, а не простая фикстура:
    - Можно настраивать expires_at (например, для теста продления срока)
    - Некоторым тестам нужен token_record.id для проверки

    Пример:
        # С дефолтными параметрами (expires через 30 дней)
        token_hash, token_record = await refresh_token_in_db_factory()

        # С кастомным сроком
        token_hash, token_record = await refresh_token_in_db_factory(
            expires_at=datetime.now(UTC) + timedelta(days=1)
        )
    """

    async def _create(
        expires_at: datetime | None = None,
        device_info: str = "telegram",
    ) -> tuple[str, RefreshTokenModel]:
        token_hash = create_refresh_token()

        if expires_at is None:
            expires_at = datetime.now(UTC) + timedelta(days=30)

        token_record = await refresh_token_repo.create(
            token_hash=token_hash,
            user_id=sample_user.id,
            expires_at=expires_at,
            device_info=device_info,
        )
        return token_hash, token_record

    return _create
