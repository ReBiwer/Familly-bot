"""
Схемы для авторизации.
"""

from datetime import datetime

from pydantic import BaseModel


class TokenRequest(BaseModel):
    """Запрос на получение токена."""

    telegram_id: int


class TelegramAuthRequest(BaseModel):
    name: str
    mid_name: str
    last_name: str
    telegram_id: int
    hash_str: str

    @property
    def msg(self) -> str:
        return (
            f"name={self.name}\n"
            f"mid_name={self.mid_name}\n"
            f"last_name={self.last_name}\n"
            f"telegram_id={self.telegram_id}"
        )

class RefreshTelegramRequest(BaseModel):
    telegram_id: int
    refresh_token: str


class TokenPair(BaseModel):
    """Пара access и refresh токенов"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    """Payload JWT токена."""

    sub: str  # Subject — telegram_id
    exp: datetime  # Expiration time
