from aiogram_dialog import Window
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.text import Const

from .state import AICommunicationSG

test_window = Window(
    Const("Тестовое окно"),
    Button(text=Const("Тестовая кнопка"), id="test_id"),
    state=AICommunicationSG.just_agent
)

windows: list[Window] = [test_window]
