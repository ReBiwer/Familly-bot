"""
Схемы для авторизации.
"""

from datetime import datetime

from pydantic import BaseModel


class TokenRequest(BaseModel):
    """Запрос на получение токена."""

    telegram_id: int


class TelegramAuthRequest(BaseModel):
    telegram_id: int
    first_name: str
    mid_name: str | None
    last_name: str | None
    hash_str: str

    @property
    def msg(self) -> str:
        return (
            f"telegram_id={self.telegram_id}\n"
            f"name={self.first_name}\n"
            f"mid_name={self.mid_name or None}\n"
            f"last_name={self.last_name or None}\n"

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
    scopes: list[str]
