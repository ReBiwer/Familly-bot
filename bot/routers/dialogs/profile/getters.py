from aiogram.fsm.context import FSMContext
from dishka.integrations.aiogram_dialog import inject
from aiogram_dialog import DialogManager

from bot.constants import KeyState
from bot.schemas.user import UserProfile

@inject
async def get_user_profile_info(dialog_manager: DialogManager, **kwargs) -> dict:
    state: FSMContext = dialog_manager.middleware_data.get("state")
    state_data = await state.get_data()
    profile_data = state_data.get(KeyState.USER_PROFILE)
    user_profile = UserProfile.model_validate_json(profile_data)

    if not user_profile:
        return {
            "has_profile": False,
            "error_message": "Профиль не найден. Повторите вход. /start"
        }
    return {
        "has_profile": True,
        "name": user_profile.name or "не найдено",
        "mid_name": user_profile.mid_name or "не найдено",
        "last_name": user_profile.last_name or "не найдено",
        "phone": user_profile.phone or "не найдено",
        "email": user_profile.email or "не найдено",
    }
