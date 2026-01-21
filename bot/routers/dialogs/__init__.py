from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode

from bot.constants import ProfileActionsData, AIAgentChoice
from .profile import UpdateProfileSG, dialog as profile_dialog
from .ai import AICommunicationSG, dialog as ai_dialog

router = Router()


@router.callback_query(F.data == ProfileActionsData.UPDATE)
async def choice_update_profile(callback: CallbackQuery, dialog_manager: DialogManager):
    await dialog_manager.start(UpdateProfileSG.main_menu, mode=StartMode.RESET_STACK)


@router.callback_query(F.data == AIAgentChoice.JUST_AGENT)
async def start_communication_with_just_agent(callback: CallbackQuery, dialog_manager: DialogManager):
    await dialog_manager.start(AICommunicationSG.just_agent, mode=StartMode.RESET_STACK)


__all__ = ["router", "profile_dialog", "UpdateProfileSG", "ai_dialog", "AICommunicationSG"]
