from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup, InlineKeyboardButton

from bot.constants import ProfileActionsData

def get_actions_profile() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        *[
            InlineKeyboardButton(text="Обновить резюме", callback_data=ProfileActionsData.UPDATE),
        ]
    )
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)
