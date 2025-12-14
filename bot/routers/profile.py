import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from dishka import FromDishka

from bot.constants import CallbackKeys, ProfileMessages, StorageKeys
from bot.entities import UserEntity

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("profile"))
@router.callback_query(F.data == CallbackKeys.PROFILE)
async def show_profile(
    message: Message | CallbackQuery,
    user: FromDishka[UserEntity | None],
):
    """
    Показывает информацию о пользователе
    """
    try:
        logger.info("Обработка команды /profile")
        text_message = ProfileMessages.profile_base(user)
        if isinstance(message, Message):
            await message.answer(text_message)
            return
        await message.answer()
        await message.message.answer(text_message)
    except Exception as e:
        logger.critical("Ошибка обработки команды.", exc_info=e)
        await message.answer(
            "⚠️ Ошибка при получении профиля\nПопробуйте авторизоваться заново: /start"
        )


@router.message(Command("logout"))
@router.callback_query(F.data == CallbackKeys.LOGOUT)
async def logout(message: Message | CallbackQuery, state: FSMContext):
    """
    Выход из аккаунта (очистка информации о пользователе их FSMContext).
    """
    logger.info("Пользователь %s выполнил logout", message.from_user.username)
    await state.set_data(
        {
            StorageKeys.USER_INFO: None,
        }
    )
    text_message = "👋 Вы успешно вышли из аккаунта.\n\nДля повторной работы используйте /start"
    if isinstance(message, Message):
        await message.answer(text_message)
        return
    await message.answer()
    await message.message.answer(text_message)
