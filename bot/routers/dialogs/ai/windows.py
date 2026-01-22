from aiogram_dialog import Window
from aiogram_dialog.widgets.kbd import SwitchTo, Button
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.text import Const, Format

from .state import AgentChoiceSG
from .handlers import chat_default_agent, back_to_choice_agent
from .getters import getter_welcome_message


choice_window = Window(
    Const("Выберите агента с которым хотите общаться"),
    SwitchTo(text=Const("Обычный агент"), id="default_agent", state=AgentChoiceSG.default_agent),
    state=AgentChoiceSG.choice_agent,
)

btn_back = Button(text=Const("Меню выбора"), id="back_to_choice", on_click=back_to_choice_agent)

default_agent_window = Window(
    Const(text="Введите ваш запрос", when="welcome_message"),
    Format("{dialog_data[llm_response]}", when="llm_response"),
    MessageInput(func=chat_default_agent),
    btn_back,
    getter=getter_welcome_message,
    state=AgentChoiceSG.default_agent,
)

windows: list[Window] = [choice_window, default_agent_window]
