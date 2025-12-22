"""
Зависимости для авторизации (FastAPI dependencies).

Логика:
- Проверка JWT access_token
- Извлечение telegram_id из payload

Почему здесь (в di):
- Храним все зависимости в одном месте
- Но используем чистый FastAPI Depends (без Dishka), т.к. проверка токена не требует контейнера
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.utils import verify_token

# HTTPBearer — схема авторизации для Swagger UI
# auto_error=True: если заголовок отсутствует — сразу 403
security = HTTPBearer(auto_error=True)


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> int:
    """
    Достаёт telegram_id из JWT access_token.

    Шаги:
    1. HTTPBearer вытаскивает токен из Authorization: Bearer <token>
    2. verify_token проверяет подпись/срок
    3. Возвращаем telegram_id (payload.sub)
    """
    token = credentials.credentials

    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return int(payload.sub)
    except (ValueError, TypeError) as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err


# Упрощённый алиас для сигнатур эндпоинтов
CurrentUserTelegramId = Annotated[int, Depends(get_current_user_id)]
