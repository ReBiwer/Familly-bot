import logging

import httpx
from aiogram import Router
from aiogram.filters.command import Command, CommandStart, Message
from aiogram.fsm.context import FSMContext
from dishka.integrations.aiogram import FromDishka

from bot.adapters import BackendAdapter
from bot.constants import CommonMessages, KeyState
from bot.schemas import UserProfile
from bot.keyboards import get_actions_profile

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
            await message.answer(CommonMessages.start_message(user))
        else:
            await message.answer(CommonMessages.start_message(user_profile))
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            await message.answer("Ошибка авторизации. Попробуйте перезапустить бота /start")
        else:
            await message.answer(f"Ошибка сервера: {e.response.status_code}")
            logger.warning(
                "Ошибка сервера: %s. Детали ошибки: %s",
                e.response.status_code,
                e.response.content,
                exc_info=e,
            )
    except Exception as e:
        logger.error("Произошла непредвиденная ошибка", exc_info=e)
        await message.answer("Произошла непредвиденная ошибка")


@router.message(Command("profile"))
async def profile(message: Message, user_profile: FromDishka[UserProfile | None]):
    if user_profile:
        await message.answer(
            CommonMessages.profile_message(user_profile),
            reply_markup=get_actions_profile(),
        )
        return
    await message.answer(CommonMessages.not_auth_user())


@router.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(CommonMessages.help_message())
