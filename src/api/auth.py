import logging

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from src.schemas import RefreshTelegramRequest, TelegramAuthRequest, TokenPair
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


@router.post("/hash_token")
async def get_hash_token(request: TelegramAuthRequest) -> dict[str, str]:
    import hashlib
    import hmac

    from src.settings import app_settings

    signature = hmac.new(
        key=app_settings.FRONT.BOT_TOKEN.encode(),
        msg=request.msg.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return {"hash": signature}
