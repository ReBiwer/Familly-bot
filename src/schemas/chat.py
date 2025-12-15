"""
Схемы для работы с AI чатом.
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Запрос на отправку сообщения."""

    user_id: int = Field(..., description="ID пользователя (telegram_id)")
    message: str = Field(..., min_length=1, max_length=4000, description="Текст сообщения")


class ChatResponse(BaseModel):
    """Ответ от AI."""

    user_id: int
    message: str
    response: str
