import logging
from aiogram.types import (
    CallbackQuery,
    Message,
)
from aiogram.utils.keyboard import KeyboardButton, ReplyKeyboardBuilder, ReplyKeyboardMarkup
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from bot.adapters import BackendAdapter
from bot.constants import KeyState
from bot.schemas import UserProfile, UserUpdate

from .state import UpdateProfileSG


logger = logging.getLogger(__name__)


async def _update_profile_in_state(data: UserProfile, dialog_manager: DialogManager):
    state = dialog_manager.middleware_data.get("state")
    await state.update_data({KeyState.USER_PROFILE: data.model_dump_json()})
    await dialog_manager.switch_to(UpdateProfileSG.main_menu)


def _get_request_contact_kbd() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(*[KeyboardButton(text="Поделиться телефоном", request_contact=True)])
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


@inject
async def input_mid_name_handler(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    # в обработчиках очень важен порядок, иначе dishka будет не корректно инжектится
    backend_adapter: FromDishka[BackendAdapter],
    **kwargs,
):
    logger.debug("Обработка отчества")
    mid_name = message.text
    update_data = UserUpdate(mid_name=mid_name)
    updated_profile = await backend_adapter.update_user(update_data)
    logger.debug("Обновление профиля в стейте")
    await _update_profile_in_state(updated_profile, dialog_manager)


@inject
async def input_last_name_handler(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    backend_adapter: FromDishka[BackendAdapter],
    **kwargs,
):
    last_name = message.text
    update_data = UserUpdate(last_name=last_name)
    updated_profile = await backend_adapter.update_user(update_data)
    await _update_profile_in_state(updated_profile, dialog_manager)


@inject
async def request_phone_handler(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    **kwargs
):
    await callback.answer()
    logger.debug("Запрос контакта пользователя через клавиатуру")
    await callback.message.answer(
        "Нажмите кнопку поделиться контактом",
        reply_markup=_get_request_contact_kbd(),
    )
    await dialog_manager.start(UpdateProfileSG.input_phone)


@inject
async def input_phone_handler(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    backend_adapter: FromDishka[BackendAdapter],
    **kwargs,
):
    logger.debug("Контакт получен, обновление данных...")
    phone = message.contact.phone_number
    update_date = UserUpdate(phone=phone)
    updated_profile = await backend_adapter.update_user(update_date)
    await _update_profile_in_state(updated_profile, dialog_manager)
    await dialog_manager.start(UpdateProfileSG.main_menu)
