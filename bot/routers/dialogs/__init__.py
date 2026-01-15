from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode

from bot.constants import ProfileActionsData

from .profile import UpdateProfileSG
from .profile import dialog as profile_dialog

router = Router()


@router.callback_query(F.data == ProfileActionsData.UPDATE)
async def choice_update_profile(callback: CallbackQuery, dialog_manager: DialogManager):
    await dialog_manager.start(UpdateProfileSG.main_menu, mode=StartMode.RESET_STACK)


__all__ = ["profile_dialog", "UpdateProfileSG", "router"]
