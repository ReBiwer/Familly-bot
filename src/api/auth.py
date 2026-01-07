import logging

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from src.schemas import RefreshTelegramRequest, TelegramAuthRequest, TokenPair
from src.settings import app_settings
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


if app_settings.DEBUG:
    import hashlib
    import hmac

    from pydantic import BaseModel, Field

    class DebugTelegramAuthRequest(BaseModel):
        telegram_id: int
        first_name: str
        mid_name: str | None = Field(default=None)
        last_name: str | None = Field(default=None)

        @property
        def msg(self) -> str:
            return (
                f"telegram_id={self.telegram_id}\n"
                f"name={self.first_name}\n"
                f"mid_name={self.mid_name or None}\n"
                f"last_name={self.last_name or None}"
            )

    @router.post("/hash_token")
    async def get_hash_token(request: DebugTelegramAuthRequest) -> dict[str, str]:
        signature = hmac.new(
            key=app_settings.FRONT.BOT_TOKEN.encode(),
            msg=request.msg.encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()
        return {"hash": signature}
