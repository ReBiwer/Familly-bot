import json

from aiogram.utils.payload import decode_payload
from hh_api.auth.token_manager import TokenManager
from src.application.repositories.base import ISQLRepository, IUnitOfWork
from src.domain.entities.user import UserEntity


class AuthUseCase:
    def __init__(
        self,
        token_manager: TokenManager,
        uow: IUnitOfWork,
        class_repo: type[ISQLRepository],
    ):
        self.token_manager = token_manager
        self.uow = uow
        self.class_repo = class_repo

    async def __call__(self, payload_str: str, tg_id: int) -> UserEntity:
        payload = json.loads(decode_payload(payload_str))
        id_user: int = payload.get("id")
        try:
            async with self.uow as session:
                user_repo = self.class_repo(session)
                user: UserEntity = await user_repo.get(id=id_user)
                user.telegram_id = tg_id
                await user_repo.update(user)
            return user
        except (json.JSONDecodeError, ValueError):
            raise
