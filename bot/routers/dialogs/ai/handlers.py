import logging
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import MessageInput
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from bot.schemas import DefaultAgentRequest
from bot.adapters import BackendAdapter
from .state import AgentChoiceSG

logger = logging.getLogger(__name__)


@inject
async def back_to_choice_agent(
    callback: CallbackQuery,
    widget: MessageInput,
    dialog_manager: DialogManager,
    **kwargs,
):
    await dialog_manager.start(AgentChoiceSG.choice_agent)


@inject
async def chat_default_agent(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    backend_adapter: FromDishka[BackendAdapter],
    **kwargs,
):
    logger.debug("Получено сообщение от пользователя: %s", message.text)
    data = DefaultAgentRequest(user_id=message.from_user.id, message=message.text)
    llm_response = await backend_adapter.chat_with_default_agent(data)
    dialog_manager.dialog_data["llm_response"] = llm_response.response
