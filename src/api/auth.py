import logging

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from src.schemas import TelegramAuthRequest, TokenPair
from src.use_cases import AuthTelegramUseCase

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
