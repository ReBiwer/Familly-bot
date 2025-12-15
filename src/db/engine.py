"""
Конфигурация подключения к БД.

Создаёт engine и session_factory для SQLAlchemy.
Используется в DI провайдерах для инжекта сессии.

Почему здесь, а не в DI:
- Миграции Alembic используют engine напрямую
- Централизованное место для настроек подключения
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.settings import app_settings

# AsyncEngine — пул соединений к БД
# echo=False — не логировать SQL запросы (включи для отладки)
engine = create_async_engine(
    app_settings.DB.db_url,
    echo=False,
)

# Фабрика сессий — создаёт новые AsyncSession
# expire_on_commit=False — объекты остаются доступны после commit
# Это нужно, чтобы можно было вернуть объект из сервиса после сохранения
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
