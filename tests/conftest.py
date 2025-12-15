"""
Общие фикстуры для тестов.

Этот файл автоматически загружается pytest.
Фикстуры доступны во всех тестах без импорта.
"""

import os
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
from src.db.models import BaseModel  # noqa: E402


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

