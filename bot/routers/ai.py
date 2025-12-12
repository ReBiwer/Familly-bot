import logging
from re import Match

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from dishka.integrations.aiogram import FromDishka

from bot.adapters.backend import BackendAdapter
from bot.constants import AIMessages, CallbackKeys, StorageKeys
from bot.entities import ResumeEntity
from bot.keyboards.inline import send_or_regenerate_ai_response

logger = logging.getLogger(__name__)

reg_pattern = r"(?:https?://)?(?:[\w-]+\.)*hh\.ru/vacancy/(?P<vacancy_id>\d+)(?:[/?#][^\s.,!?)]*)?"

router = Router()


class RegenerateResponse(StatesGroup):
    user_comments = State()


@router.message(F.text.regexp(reg_pattern).as_("url"))
async def handler_hh_vacancy(
    message: Message,
    url: Match,
    state: FSMContext,
    resume: FromDishka[ResumeEntity | None],
    backend_adapter: FromDishka[BackendAdapter],
):
    logger.info(
        "Пришел запрос на генерацию отклика на вакансию %s пользователя %s",
        url.string,
        message.from_user.username,
    )
    if resume:
        await state.update_data({StorageKeys.CURRENT_VACANCY_URL: url.string})
        await state.update_data({StorageKeys.CURRENT_VACANCY_HH_ID: url.group("vacancy_id")})
        response = await backend_adapter.get_llm_response(message.from_user.id, url.string)
        logger.info("Сгенерированный отклик: %s", response)
        await message.answer(response, reply_markup=send_or_regenerate_ai_response())
        return
    logger.info("У пользователя %s не выбрано активное резюме", message.from_user.username)
    await message.answer(AIMessages.no_active_resume())


@router.callback_query(F.data == CallbackKeys.SEND_AI_RESPONSE)
async def send_ai_response(
    callback: CallbackQuery,
    state: FSMContext,
    resume: FromDishka[ResumeEntity],
    backend_adapter: FromDishka[BackendAdapter],
):
    await callback.answer()
    url_vacancy = await state.get_value(StorageKeys.CURRENT_VACANCY_URL)
    logger.info("Отправка отклика на резюме %s", url_vacancy)
    await backend_adapter.post_response_to_vacancy(url_vacancy, resume.id, callback.message.text)


@router.callback_query(F.data == CallbackKeys.REGENERATE_AI_RESPONSE)
async def requesting_user_edits(
    callback: CallbackQuery,
    state: FSMContext,
):
    logger.info("Пользователь решил переделать отклик")
    await callback.answer()
    await state.update_data({StorageKeys.AI_RESPONSE: callback.message.text})
    await callback.message.answer(AIMessages.request_user_comments())
    await state.set_state(RegenerateResponse.user_comments)


@router.message(RegenerateResponse.user_comments)
async def regenerate_response(
    message: Message,
    state: FSMContext,
    backend_adapter: FromDishka[BackendAdapter],
):
    url = await state.get_value(StorageKeys.CURRENT_VACANCY_URL)
    ai_response = await state.get_value(StorageKeys.AI_RESPONSE)
    user_comments = message.text
    logger.info("Исправления пользователя %s: %s", message.from_user.username, user_comments)
    response = await backend_adapter.get_llm_response(
        message.from_user.id,
        url,
        past_response=ai_response,
        user_comments=user_comments,
    )
    await state.set_state()
    return message.answer(response, reply_markup=send_or_regenerate_ai_response())
