import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from dishka import FromDishka

from bot.constants import CallbackKeys, ProfileMessages, StorageKeys
from bot.entities import ResumeEntity, UserEntity
from bot.keyboards.inline import ResumeCallback, resumes_keyboard

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("profile"))
@router.callback_query(F.data == CallbackKeys.PROFILE)
async def show_profile(
    message: Message | CallbackQuery,
    user: FromDishka[UserEntity | None],
    active_resume: FromDishka[ResumeEntity | None],
):
    """
    Показывает информацию о пользователе
    """
    try:
        logger.info("Обработка команды /profile")
        text_message = ProfileMessages.profile_base(
            user, active_resume.title if active_resume else None
        )
        if isinstance(message, Message):
            await message.answer(text_message, reply_markup=resumes_keyboard(user.resumes))
            return
        await message.answer()
        await message.message.answer(text_message, reply_markup=resumes_keyboard(user.resumes))
    except Exception as e:
        logger.critical("Ошибка обработки команды.", exc_info=e)
        await message.answer(
            "⚠️ Ошибка при получении профиля\nПопробуйте авторизоваться заново: /start"
        )


@router.callback_query(ResumeCallback.filter(F.action == "active"))
async def select_active_resume(
    callback: CallbackQuery,
    callback_data: ResumeCallback,
    state: FSMContext,
    user: FromDishka[UserEntity | None],
):
    logger.info(
        "Пользователь %s выбрал резюме %s",
        callback.from_user.username,
        callback_data.title,
    )
    active_resume = ""
    for resume in user.resumes:
        if resume.id == callback_data.resume_id:
            active_resume = resume.model_dump_json()
            break
    await state.update_data(
        {
            StorageKeys.ACTIVE_RESUME: active_resume,
        }
    )
    await callback.message.edit_text(
        ProfileMessages.profile_base(user, callback_data.title),
        reply_markup=resumes_keyboard(user.resumes, callback_data.resume_id),
    )
    await callback.answer()


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
            StorageKeys.ACTIVE_RESUME: None,
        }
    )
    text_message = "👋 Вы успешно вышли из аккаунта.\n\nДля повторной работы используйте /start"
    if isinstance(message, Message):
        await message.answer(text_message)
        return
    await message.answer()
    await message.message.answer(text_message)
