from aiogram_dialog import Window
from aiogram_dialog.widgets.markup.reply_keyboard import ReplyKeyboardFactory
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Group, SwitchTo, RequestContact
from aiogram_dialog.widgets.text import Const, Format, Multi

from .getters import get_user_profile_info
from .handlers import (
    input_last_name_handler,
    input_mid_name_handler,
    input_phone_handler,
    back_to_menu,
)
from .state import UpdateProfileSG

# основное меню, где у пользователя запрашивают, что он хочет поменять
main_menu = Window(
    Multi(
        Const("Ваш профиль"),
        Format("Имя: {name}"),
        Format("Отчество: {mid_name}"),
        Format("Фамилия: {last_name}"),
        Format("Телефон: {phone}"),
        Format("Почта: {email}"),
        Const("\nЧто хотите изменить?"),
    ),
    Group(
        SwitchTo(text=Const("Отчество"), id="edit_mid_name", state=UpdateProfileSG.input_mid_name),
        SwitchTo(text=Const("Фамилию"), id="edit_last_name", state=UpdateProfileSG.input_last_name),
        SwitchTo(text=Const("Телефон"), id="request_phone", state=UpdateProfileSG.input_phone),
        SwitchTo(text=Const("Почту"), id="edit_email", state=UpdateProfileSG.input_email),
        width=2,
    ),
    getter=get_user_profile_info,
    state=UpdateProfileSG.main_menu,
)

btn_back = Button(text=Const("Назад"), id="back_menu", on_click=back_to_menu)

mid_name_window = Window(
    Multi(Format("Текущее значение - {mid_name}"), Const("Введите новое значение")),
    btn_back,
    MessageInput(func=input_mid_name_handler, content_types=["text"]),
    getter=get_user_profile_info,
    state=UpdateProfileSG.input_mid_name,
)

last_name_window = Window(
    Multi(Format("Текущее значение - {last_name}"), Const("Введите новое значение")),
    btn_back,
    MessageInput(func=input_last_name_handler, content_types=["text"]),
    getter=get_user_profile_info,
    state=UpdateProfileSG.input_last_name,
)

phone_window = Window(
    Multi(Const("Нажмите кнопку поделиться контактом"), Format("Текущее значение - {phone}")),
    RequestContact(text=Const("Поделиться телефоном")),
    btn_back,
    MessageInput(func=input_phone_handler, content_types=["contact"]),
    markup_factory=ReplyKeyboardFactory(one_time_keyboard=True, resize_keyboard=True),
    getter=get_user_profile_info,
    state=UpdateProfileSG.input_phone,
)

email_window = Window(
    Multi(Format("Текущее значение - {email}"), Const("Введите новое значение")),
    btn_back,
    MessageInput(func=input_mid_name_handler, content_types=["text"]),
    getter=get_user_profile_info,
    state=UpdateProfileSG.input_email,
)


windows = [main_menu, mid_name_window, last_name_window, phone_window, email_window]
