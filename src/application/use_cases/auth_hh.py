import logging
from collections.abc import Mapping
from typing import Any

from src.application.repositories.base import IUnitOfWork
from src.application.repositories.user import IUserRepository
from src.application.services.hh_service import AuthTokens, IHHService
from src.application.services.state_manager import URL, IStateManager
from src.domain.entities.user import UserEntity

logger = logging.getLogger(__name__)


class OAuthHHUseCase:
    def __init__(
        self,
        hh_service: IHHService,
        state_manager: IStateManager,
        class_repo: type[IUserRepository[UserEntity]],
        uow: IUnitOfWork,
    ):
        self.hh_service = hh_service
        self.state_manager = state_manager
        self.uow = uow
        self.class_repo = class_repo

    async def __call__(
        self, code: str, state: str, request: Mapping[str, Any], subject
    ) -> tuple[URL, AuthTokens]:
        user, tokens = await self.hh_service.auth(code)
        logger.debug("Get user from hh.ru: name=%s, last_name=%s", user.name, user.last_name)
        async with self.uow as session:
            repo = self.class_repo(session)
            payload = await repo.create(user)
            logger.debug("User added to DB")

        converted_payload = payload.model_dump_json(include={"id", "hh_id"})
        redirect_url = await self.state_manager.state_convert(state, converted_payload, request)
        logger.debug("Redirect url created: %s", redirect_url)
        return redirect_url, tokens
