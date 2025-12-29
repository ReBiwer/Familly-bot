"""
Утилиты приложения.

Вспомогательные функции, которые используются в разных частях приложения.
"""

from src.utils.scopes import get_scopes_for_role, get_scopes_for_user
from src.utils.tokens import (
    TokenExpiredException,
    TokenInvalidException,
    create_access_token,
    create_refresh_token,
    verify_token,
)

__all__ = [
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "TokenExpiredException",
    "TokenInvalidException",
    "get_scopes_for_role",
    "get_scopes_for_user",
]
