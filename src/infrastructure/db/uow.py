import logging

from sqlalchemy.ext.asyncio import AsyncSession
from src.application.repositories.base import IUnitOfWork

logger = logging.getLogger(__name__)


class UnitOfWork(IUnitOfWork):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def __aenter__(self):
        self._transaction = self._session.begin()
        logger.debug("Begin transaction")
        await self._transaction.__aenter__()
        return self._session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._transaction.__aexit__(exc_type, exc_val, exc_tb)
        logger.debug(
            "Exit transaction with param: exc_type=%s, exc_val=%s, exc_tb=%s",
            exc_type,
            exc_val,
            exc_tb,
        )
