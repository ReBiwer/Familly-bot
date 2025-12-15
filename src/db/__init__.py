"""
Модуль для работы с базой данных.

Содержит:
- engine.py — подключение к БД
- models/ — ORM модели SQLAlchemy
- repositories/ — репозитории для доступа к данным
- migrations/ — миграции Alembic
"""

from src.db.engine import async_session_factory, engine

__all__ = [
    "engine",
    "async_session_factory",
]
