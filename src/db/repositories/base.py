"""
Базовый репозиторий для работы с БД.

Простая реализация паттерна Repository для типовых CRUD операций.
Каждый конкретный репозиторий наследуется от BaseRepository
и указывает свою ORM модель.

Почему такой простой подход:
- MVP проект, не нужна сложная архитектура
- Работаем напрямую с ORM моделями
- Схемы (Pydantic) используются только на границе API
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.base import BaseModel

logger = logging.getLogger(__name__)


class BaseRepository[ModelT: BaseModel]:
    """
    Базовый репозиторий с типовыми CRUD операциями.

    Attributes:
        model: Класс ORM модели (указывается в наследнике)
        session: AsyncSession для работы с БД

    Example:
        ```python
        class UserRepository(BaseRepository[UserModel]):
            model = UserModel

        repo = UserRepository(session)
        user = await repo.get_by_id(42)
        ```
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория.

        Args:
            session: Асинхронная сессия SQLAlchemy.
                     Обычно инжектится через Dishka.
        """
        self.session = session

    async def get_by_id(self, entity_id: int) -> ModelT | None:
        """
        Получает сущность по ID.

        Args:
            entity_id: Первичный ключ

        Returns:
            ORM модель или None если не найдена
        """
        logger.debug("Get %s by id=%s", self.model.__name__, entity_id)
        return await self.session.get(self.model, entity_id)

    async def get_one(self, **filters) -> ModelT | None:
        """
        Получает одну сущность по фильтрам.

        Args:
            **filters: Поля для фильтрации (field=value)

        Returns:
            ORM модель или None

        Example:
            ```python
            user = await repo.get_one(telegram_id=123456)
            ```
        """
        logger.debug("Get %s with filters=%s", self.model.__name__, filters)
        stmt = select(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_many(self, **filters) -> list[ModelT]:
        """
        Получает список сущностей по фильтрам.

        Args:
            **filters: Поля для фильтрации

        Returns:
            Список ORM моделей (может быть пустым)

        Example:
            ```python
            users = await repo.get_many(is_active=True)
            ```
        """
        logger.debug("Get many %s with filters=%s", self.model.__name__, filters)
        stmt = select(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **data) -> ModelT:
        """
        Создаёт новую сущность.

        Args:
            **data: Данные для создания (поля модели)

        Returns:
            Созданная ORM модель с заполненным id

        Example:
            ```python
            user = await repo.create(
                name="Владимир",
                last_name="Иванов",
                telegram_id=123456
            )
            print(user.id)  # ID присвоен после flush
            ```
        """
        logger.debug("Create %s with data=%s", self.model.__name__, data)
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()  # Получаем id без commit
        logger.debug("Created %s with id=%s", self.model.__name__, instance.id)
        return instance

    async def update(self, entity_id: int, **data) -> ModelT | None:
        """
        Обновляет сущность по ID.

        Args:
            entity_id: ID сущности для обновления
            **data: Поля для обновления (только переданные)

        Returns:
            Обновлённая ORM модель или None если не найдена

        Example:
            ```python
            user = await repo.update(42, email="new@example.com")
            ```
        """
        logger.debug("Update %s id=%s with data=%s", self.model.__name__, entity_id, data)
        instance = await self.get_by_id(entity_id)
        if not instance:
            logger.debug("%s with id=%s not found", self.model.__name__, entity_id)
            return None

        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        await self.session.flush()
        logger.debug("Updated %s id=%s", self.model.__name__, entity_id)
        return instance

    async def delete(self, entity_id: int) -> bool:
        """
        Удаляет сущность по ID.

        Args:
            entity_id: ID сущности для удаления

        Returns:
            True если удалено, False если не найдено

        Example:
            ```python
            deleted = await repo.delete(42)
            if not deleted:
                raise NotFoundError()
            ```
        """
        logger.debug("Delete %s id=%s", self.model.__name__, entity_id)
        instance = await self.get_by_id(entity_id)
        if not instance:
            logger.debug("%s with id=%s not found", self.model.__name__, entity_id)
            return False

        await self.session.delete(instance)
        await self.session.flush()
        logger.debug("Deleted %s id=%s", self.model.__name__, entity_id)
        return True
