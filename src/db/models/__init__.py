"""
ORM модели SQLAlchemy.

Все модели наследуются от BaseModel, который предоставляет:
- id: первичный ключ
- created_at: дата создания
"""

from src.db.models.base import BaseModel
from src.db.models.user import UserModel

__all__ = [
    "BaseModel",
    "UserModel",
]
