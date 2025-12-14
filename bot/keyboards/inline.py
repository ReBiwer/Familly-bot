from typing import Literal

from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup
from pydantic import Field

from bot.constants import CallbackKeys
from bot.entities import ResumeEntity


class ResumeCallback(CallbackData, prefix="resume"):
    action: Literal["active", "deactive"] = Field(default="active")
    resume_id: int
    title: str


def profile_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="profile", callback_data=CallbackKeys.PROFILE)
    builder.button(text="logout", callback_data=CallbackKeys.LOGOUT)
    builder.adjust(2, 1)
    return builder.as_markup()


def resumes_keyboard(
    resumes: list[ResumeEntity], exclude_resume_id: int | None = None
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for resume in resumes:
        if resume.id == exclude_resume_id:
            continue
        builder.button(
            text=resume.title,
            callback_data=ResumeCallback(
                action="active",
                resume_id=resume.id,
                title=resume.title,
            ),
        )
    builder.adjust(2)
    return builder.as_markup()


def send_or_regenerate_ai_response() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Переделать", callback_data=CallbackKeys.REGENERATE_AI_RESPONSE)
    builder.button(text="Отправить", callback_data=CallbackKeys.SEND_AI_RESPONSE)
    builder.adjust(1)
    return builder.as_markup()
