"""
Репозитории для работы с БД.

Репозитории инкапсулируют логику доступа к данным.
Используют AsyncSession из SQLAlchemy.
"""

from src.db.repositories.base import BaseRepository
from src.db.repositories.user import UserRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
]
