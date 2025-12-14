import logging

from aiogram import Router
from aiogram.fsm.state import State, StatesGroup

logger = logging.getLogger(__name__)

reg_pattern = r"(?:https?://)?(?:[\w-]+\.)*hh\.ru/vacancy/(?P<vacancy_id>\d+)(?:[/?#][^\s.,!?)]*)?"

router = Router()


class RegenerateResponse(StatesGroup):
    user_comments = State()
