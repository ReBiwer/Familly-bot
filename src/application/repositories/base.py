from abc import ABC, abstractmethod
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.entities.base import BaseEntity


class IRepository[ET: BaseEntity](ABC):
    @abstractmethod
    async def get(self, **filters) -> ET | None: ...

    @abstractmethod
    async def create(self, entity: ET) -> ET: ...

    @abstractmethod
    async def update(self, entity: ET) -> ET: ...

    @abstractmethod
    async def delete(self, id_entity: int) -> None: ...


class ISQLRepository[ET: BaseEntity](IRepository, ABC):
    def __init__(self, session: AsyncSession):
        self.session = session


class IUnitOfWork(Protocol):
    async def __aenter__(self): ...

    async def __aexit__(self, exc_type, exc_val, exc_tb): ...
