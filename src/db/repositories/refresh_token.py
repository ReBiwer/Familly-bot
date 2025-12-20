import logging

from src.db.models import RefreshTokenModel
from src.db.repositories import BaseRepository

logger = logging.getLogger(__name__)


class RefreshTokenRepository(BaseRepository):
    model = RefreshTokenModel

    async def get_by_user_id(self, user_id: int) -> RefreshTokenModel | None:
        logger.debug("Get refresh token by user_id=%s", user_id)
        return await self.get_one(user_id=user_id)
