"""
Утилиты для работы с JWT токенами.

Функции для создания и проверки JWT токенов авторизации.
"""

import logging
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from jose import ExpiredSignatureError, JWTError, jwt

from src.constants import DEFAULT_SCOPES
from src.schemas import TokenPayload
from src.settings import app_settings

logger = logging.getLogger(__name__)


class TokenExpiredException(HTTPException):
    """
    Исключение для истекшего токена.

    Почему отдельный класс:
    - Клиент должен знать, что токен истек, а не просто невалидный
    - Клиент может автоматически запросить refresh
    - HTTP 401 с конкретным detail помогает в дебаге
    """

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={
                "WWW-Authenticate": 'Bearer error="invalid_token", error_description="Token expired"'
            },
        )


class TokenInvalidException(HTTPException):
    """
    Исключение для невалидного токена.

    Почему отдельно от TokenExpiredException:
    - Невалидный токен = подделка, ошибка подписи, битые данные
    - Клиент НЕ должен пытаться refresh - нужна новая авторизация
    """

    def __init__(self, detail: str = "Invalid token"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_access_token(
    telegram_id: int,
    expires_delta: timedelta | None = None,
    scopes_permissions: list[str] | None = None,
) -> str:
    """
    Создаёт JWT access token.

    Args:
        telegram_id: ID пользователя в Telegram
        expires_delta: Время жизни токена (по умолчанию 7 дней)
        scopes_permissions: Доступы пользователя

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

    if scopes_permissions is None:
        scopes_permissions = DEFAULT_SCOPES.copy()

    expire = datetime.now(UTC) + expires_delta

    payload = {"sub": str(telegram_id), "exp": expire, "scopes": scopes_permissions}

    return jwt.encode(
        payload,
        app_settings.AUTH.JWT_TOKEN,
        algorithm=app_settings.AUTH.JWT_ALG,
    )


def create_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def verify_token(token: str) -> TokenPayload:
    """
    Проверяет и декодирует JWT токен.

    Важно: эта функция теперь ВЫБРАСЫВАЕТ исключения вместо возврата None.
    Почему так лучше:
    - Клиент получает конкретную причину ошибки (истек vs невалиден)
    - Клиент может автоматически обновить токен при TokenExpiredException
    - Не нужно проверять на None в каждом месте использования

    Args:
        token: JWT токен для проверки

    Returns:
        TokenPayload с данными токена

    Raises:
        TokenExpiredException: Срок действия токена истек
        TokenInvalidException: Токен невалидный (подделка, неверная подпись)

    Example:
        ```python
        try:
            payload = verify_token(token)
            telegram_id = int(payload.sub)
        except TokenExpiredException:
            # Клиент должен обновить токен через /auth/telegram/refresh
            pass
        except TokenInvalidException:
            # Клиент должен авторизоваться заново
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
    except ExpiredSignatureError as e:
        # Токен истек - клиент может обновить его через refresh
        logger.info("Token expired: %s", e)
        raise TokenExpiredException() from e
    except JWTError as e:
        # Токен невалидный - подделка или ошибка
        logger.warning("Invalid JWT token: %s", e)
        raise TokenInvalidException(detail=f"Invalid token: {str(e)}") from e
