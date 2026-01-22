from aiogram_dialog import DialogManager


async def getter_welcome_message(dialog_manager: DialogManager, **kwargs):
    welcome_data = dialog_manager.dialog_data
    if "welcome" not in welcome_data:
        welcome_data["welcome"] = True
        return {
            "welcome_message": True,
            "llm_response": False,
        }
    else:
        return {
            "welcome_message": False if welcome_data["welcome"] else True,
            "llm_response": True if welcome_data["welcome"] else False,
        }
