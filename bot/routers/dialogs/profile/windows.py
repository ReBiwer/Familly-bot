from aiogram_dialog import Window
from aiogram_dialog.widgets.text import Multi, Format, Const

from .getters import get_user_profile_info
from .state import UpdateProfileSG

main_menu = Window(
    Multi(
        Const("Ваш профиль"),
        Format("Имя: {name}"),
        Format("Отчество: {mid_name}"),
        Format("Фамилия: {last_name}"),
        Format("Телефон: {phone}"),
        Format("Почта: {email}"),
    ),
    getter=get_user_profile_info,
    state=UpdateProfileSG.main_menu,
)


windows = [main_menu]
