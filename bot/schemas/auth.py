from pydantic import BaseModel


class AuthRequest(BaseModel):
    telegram_id: int
    first_name: str
    mid_name: str | None = None
    last_name: str | None = None
    hash_str: str


class TokenPair(BaseModel):
    """Пара access и refresh токенов"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
