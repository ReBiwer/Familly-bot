import json
import logging

from aiogram.dispatcher.router import Router
from aiogram.filters.command import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from dishka import FromDishka
from src.application.services.hh_service import IHHService
from src.application.use_cases.bot.authorization import AuthUseCase
from src.constants.keys import StorageKeys
from src.constants.texts_message import StartMessages
from src.domain.entities.user import UserEntity

from bot.keyboards.inline import profile_keyboard

logger = logging.getLogger(__name__)


router = Router()


@router.message(CommandStart())
async def start(
    message: Message,
    state: FSMContext,
    hh_service: FromDishka[IHHService],
    auth_use_case: FromDishka[AuthUseCase],
    user: FromDishka[UserEntity | None],
    command: CommandObject = None,
):
    """
    Обработчик команды /start.

    Args:
        message: Сообщение от пользователя
        state: FSM context для работы с данными пользователя
        hh_service: Сервис для работы с HH.ru API
        auth_use_case: Use case авторизации
        user: Если не None пользователь авторизован
        command: Объект команды с аргументами
    """
    # Проверяем, пришел ли пользователь после авторизации (с payload)
    logger.debug("Обработка команды /start")
    args = command.args
    if args:
        logger.debug("Команда пришла с payload'ом")
        try:
            logger.info("Начало авторизации пользователя %s", message.from_user.username)
            user = await auth_use_case(payload_str=args, tg_id=message.from_user.id)
            logger.info("Пользователь %s авторизован", message.from_user.username)
            await state.update_data(
                {StorageKeys.USER_INFO: user.model_dump_json(exclude_unset=True)}
            )

            await message.answer(
                StartMessages.user_authenticated(user), reply_markup=profile_keyboard()
            )
        except (json.JSONDecodeError, ValueError) as e:
            logger.critical("Ошибка обработки данных.", exc_info=e)
            await message.answer("⚠️ Ошибка обработки данных авторизации. Попробуйте заново.")
    else:
        if user:
            logger.info("Пользователь авторизован")
            await message.answer(
                StartMessages.user_back(user),
                reply_markup=profile_keyboard(),
            )
        else:
            logger.info("Пользователь не авторизован")
            auth_url = hh_service.get_auth_url("telegram")
            await message.answer(StartMessages.user_not_authenticated(auth_url))
