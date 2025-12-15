"""
API роутеры приложения.

Содержит все HTTP эндпоинты для взаимодействия с сервисами.
"""

from src.api.ai import router as ai_router
from src.api.auth import router as auth_router
from src.api.health import router as health_router
from src.api.users import router as users_router

__all__ = [
    "ai_router",
    "auth_router",
    "health_router",
    "users_router",
]
