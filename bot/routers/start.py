import logging

import httpx
from aiogram import Router
from aiogram.filters.command import CommandStart, Message
from aiogram.fsm.context import FSMContext
from dishka.integrations.aiogram import FromDishka

from bot.adapters import BackendAdapter
from bot.constants import KeyState, StartMessages
from bot.schemas import UserProfile

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def start(
    message: Message,
    state: FSMContext,
    backend_adapter: FromDishka[BackendAdapter],
    user_profile: FromDishka[UserProfile | None],
):
    try:
        if user_profile is None:
            user = await backend_adapter.get_me()
            await state.update_data(
                {KeyState.USER_PROFILE: user.model_dump_json()},
            )
            await message.answer(StartMessages.hello_auth_user(user))
        else:
            await message.answer(StartMessages.hello_auth_user(user_profile))
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            await message.answer("Ошибка авторизации. Попробуйте перезапустить бота /start")
        else:
            await message.answer(f"Ошибка сервера: {e.response.status_code}")
            logger.warning("Ошибка сервера: %s. Детали ошибки: %s", e.response.status_code, e.response.content, exc_info=e)
    except Exception:
        await message.answer("Произошла непредвиденная ошибка")
