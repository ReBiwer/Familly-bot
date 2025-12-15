"""
Схемы для авторизации.
"""

from datetime import datetime

from pydantic import BaseModel


class TokenRequest(BaseModel):
    """Запрос на получение токена."""

    telegram_id: int


class TokenResponse(BaseModel):
    """Ответ с токеном."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Время жизни в секундах


class TokenPayload(BaseModel):
    """Payload JWT токена."""

    sub: str  # Subject — telegram_id
    exp: datetime  # Expiration time
