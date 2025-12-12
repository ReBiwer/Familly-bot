import json
import logging

from aiogram.utils.payload import decode_payload

from bot.adapters.backend import BackendAdapter
from bot.entities import UserEntity

logger = logging.getLogger(__name__)


class AuthUseCase:
    def __init__(self, back_adapter: BackendAdapter):
        self._adapter = back_adapter

    async def __call__(self, payload_str: str) -> UserEntity:
        try:
            payload = json.loads(decode_payload(payload_str))
            id_user: int = payload.get("id")
            user = await self._adapter.get_user(id_user)
            return user
        except (json.JSONDecodeError, ValueError):
            logger.error("Ошибка обработки")
            raise
