"""
Pydantic схемы для валидации данных API.

Схемы разделены по назначению:
- *Create — данные для создания сущности
- *Read — данные для чтения (включают id, created_at)
- *Update — данные для обновления (все поля опциональные)

Использование:
    from src.schemas import UserCreate, UserRead, ChatRequest

    @router.post("/users", response_model=UserRead)
    async def create_user(data: UserCreate):
        ...
"""

from src.schemas.auth import (
    RefreshTelegramRequest,
    TelegramAuthRequest,
    TokenPair,
    TokenPayload,
    TokenRequest,
)
from src.schemas.chat import ChatRequest, ChatResponse
from src.schemas.user import UserCreate, UserRead, UserUpdate

__all__ = [
    # User
    "UserCreate",
    "UserRead",
    "UserUpdate",
    # Auth
    "TokenRequest",
    "TelegramAuthRequest",
    "RefreshTelegramRequest",
    "TokenPair",
    "TokenPayload",
    # Chat
    "ChatRequest",
    "ChatResponse",
]
