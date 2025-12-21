"""
Утилиты для работы с JWT токенами.

Функции для создания и проверки JWT токенов авторизации.
"""

import logging
import secrets
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from src.schemas import TokenPayload
from src.settings import app_settings

logger = logging.getLogger(__name__)


def create_access_token(telegram_id: int, expires_delta: timedelta | None = None) -> str:
    """
    Создаёт JWT access token.

    Args:
        telegram_id: ID пользователя в Telegram
        expires_delta: Время жизни токена (по умолчанию 7 дней)

    Returns:
        Закодированный JWT токен

    Example:
        ```python
        token = create_access_token(telegram_id=123456)
        # или с кастомным временем жизни
        token = create_access_token(telegram_id=123456, expires_delta=timedelta(hours=1))
        ```
    """
    if expires_delta is None:
        expires_delta = timedelta(days=7)

    expire = datetime.now(UTC) + expires_delta

    payload = {
        "sub": str(telegram_id),
        "exp": expire,
    }

    return jwt.encode(
        payload,
        app_settings.AUTH.JWT_TOKEN,
        algorithm=app_settings.AUTH.JWT_ALG,
    )


def create_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def verify_token(token: str) -> TokenPayload | None:
    """
    Проверяет и декодирует JWT токен.

    Args:
        token: JWT токен для проверки

    Returns:
        TokenPayload если токен валиден, иначе None

    Example:
        ```python
        payload = verify_token(token)
        if payload:
            telegram_id = int(payload.sub)
        else:
            # Токен невалиден или истёк
            pass
        ```
    """
    try:
        payload = jwt.decode(
            token,
            app_settings.AUTH.JWT_TOKEN,
            algorithms=[app_settings.AUTH.JWT_ALG],
        )
        return TokenPayload(**payload)
    except JWTError as e:
        logger.warning("Invalid JWT token: %s", e)
        return None
