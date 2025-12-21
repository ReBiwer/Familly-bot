import logging

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from src.schemas import TelegramAuthRequest, RefreshTelegramRequest, TokenPair
from src.use_cases import AuthTelegramUseCase, RefreshTokensTelegramUseCase

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    route_class=DishkaRoute,
)

logger = logging.getLogger(__name__)


@router.post("/telegram")
async def auth_telegram(
    request: TelegramAuthRequest,
    auth_use_case: FromDishka[AuthTelegramUseCase],
) -> TokenPair:
    tokens = await auth_use_case(request)
    return tokens

@router.post("/telegram/refresh")
async def refresh_telegram_tokens(
    request: RefreshTelegramRequest,
    refresh_use_case: FromDishka[RefreshTokensTelegramUseCase],
) -> TokenPair:
    new_tokens = await refresh_use_case(request)
    return new_tokens
