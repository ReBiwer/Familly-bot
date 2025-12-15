"""
Роутер авторизации.

Простая JWT авторизация для семейного бота.
Пользователь авторизуется через Telegram ID.
"""

import logging
from datetime import timedelta
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Body, HTTPException, status

from src.schemas import TokenPayload, TokenRequest, TokenResponse
from src.utils import create_access_token, verify_token

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    route_class=DishkaRoute,
)

logger = logging.getLogger(__name__)


@router.post("/token", response_model=TokenResponse)
async def get_token(request: TokenRequest) -> TokenResponse:
    """
    Получение JWT токена по Telegram ID.

    Простая авторизация — любой telegram_id получает токен.
    В продакшене можно добавить проверку через Telegram Bot API.

    Args:
        request: Запрос с telegram_id

    Returns:
        TokenResponse с access_token
    """
    logger.info("Token requested for telegram_id=%s", request.telegram_id)

    expires_delta = timedelta(days=7)
    access_token = create_access_token(
        telegram_id=request.telegram_id,
        expires_delta=expires_delta,
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=int(expires_delta.total_seconds()),
    )


@router.post("/verify", response_model=TokenPayload)
async def verify(token: Annotated[str, Body(embed=True)]) -> TokenPayload:
    """
    Проверка валидности токена.

    Args:
        token: JWT токен для проверки

    Returns:
        TokenPayload если токен валиден

    Raises:
        HTTPException 401 если токен невалиден
    """
    payload = verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return payload
