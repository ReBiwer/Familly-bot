"""
Зависимости для авторизации (FastAPI dependencies).

Логика:
- Проверка JWT access_token
- Извлечение telegram_id из payload

Почему здесь (в di):
- Храним все зависимости в одном месте
- Но используем чистый FastAPI Depends (без Dishka), т.к. проверка токена не требует контейнера
"""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, SecurityScopes

from src.constants import ROLE_SCOPES_MAP, ScopesPermissions, UserRole
from src.utils import verify_token

security = HTTPBearer(auto_error=True)
logger = logging.getLogger(__name__)


async def get_current_telegram_id(
    security_scopes: SecurityScopes,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> int:
    """
    Проверяет JWT токен и требуемые scopes.

    Как работает:
    1. HTTPBearer парсит заголовок Authorization: Bearer <token>
    2. credentials.credentials содержит сам токен
    3. security_scopes.scopes содержит список требуемых scopes из эндпоинта
    4. Проверяем токен и извлекаем scopes из payload
    5. Сравниваем: есть ли у пользователя все требуемые scopes

    Args:
        security_scopes: Автоматически создаётся FastAPI, содержит требуемые scopes
        credentials: Данные из заголовка Authorization

    Returns:
        telegram_id

    Raises:
        HTTPException 401: Токен невалидный или истёк
        HTTPException 403: Не хватает прав (scopes)
    """
    token = credentials.credentials
    payload = verify_token(token)
    authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": authenticate_value},
        )

    try:
        telegram_id = int(payload.sub)
        token_scopes = payload.scopes

        logger.debug(
            "Auth check: user=%s, has_scopes=%s, required_scopes=%s",
            telegram_id,
            token_scopes,
            security_scopes.scopes,
        )

        if ScopesPermissions.ADMIN.value in token_scopes:
            logger.info("Admin %s accessing: %s", telegram_id, security_scopes.scope_str)
            return telegram_id

        for required_scope in security_scopes.scopes:
            if required_scope not in token_scopes:
                logger.warning(
                    "Access denied: user=%s, missing_scope=%s, has_scopes=%s",
                    telegram_id,
                    required_scope,
                    token_scopes,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not enough permissions. Required: {security_scopes.scopes}, Have: {token_scopes}",
                    headers={"WWW-Authenticate": authenticate_value},
                )
        return telegram_id

    except (ValueError, TypeError) as err:
        logger.error("Token payload validation error: %s", err, exc_info=err)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err


CurrentUserTelegramId = Annotated[
    int, Security(get_current_telegram_id, scopes=ROLE_SCOPES_MAP.get(UserRole.MEMBER))
]
CurrentChildTelegramId = Annotated[
    int, Security(get_current_telegram_id, scopes=ROLE_SCOPES_MAP.get(UserRole.CHILD))
]
CurrentAdminTelegramId = Annotated[
    int, Security(get_current_telegram_id, scopes=ROLE_SCOPES_MAP.get(UserRole.ADMIN))
]
