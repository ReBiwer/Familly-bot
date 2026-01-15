from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from aiogram_dialog import DialogManager

from bot.schemas.user import UserProfile

@inject
async def get_user_profile_info(dialog_manager: DialogManager, user_profile: FromDishka[UserProfile | None], **kwargs) -> dict:
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
