"""
Общие фикстуры для тестов.

Этот файл автоматически загружается pytest.
Фикстуры доступны во всех тестах без импорта.
"""

import os
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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
        expires_at=datetime.now() + timedelta(days=7),
        device_info="test_device",
    )
