"""
Репозиторий для работы с пользователями.

Наследует базовые CRUD операции и добавляет специфичные методы.
"""

import logging

from src.db.models.user import UserModel
from src.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[UserModel]):
    """
    Репозиторий пользователей.

    Наследует от BaseRepository:
    - get_by_id(id) -> UserModel | None
    - get_one(**filters) -> UserModel | None
    - get_many(**filters) -> list[UserModel]
    - create(**data) -> UserModel
    - update(id, **data) -> UserModel | None
    - delete(id) -> bool

    Добавляет специфичные методы для работы с пользователями.

    Example:
        ```python
        repo = UserRepository(session)

        # Создание
        user = await repo.create(name="Вова", last_name="Иванов", telegram_id=123)

        # Поиск по telegram_id
        user = await repo.get_by_telegram_id(123456)

        # Обновление
        user = await repo.update(user.id, email="new@mail.ru")
        ```
    """

    model = UserModel

    async def get_by_telegram_id(self, telegram_id: int) -> UserModel | None:
        """
        Получает пользователя по Telegram ID.

        Args:
            telegram_id: ID пользователя в Telegram

        Returns:
            UserModel или None если не найден

        Почему отдельный метод:
        - Часто используется для авторизации через бота
        - telegram_id уникален (есть индекс в БД)
        """
        logger.debug("Get user by telegram_id=%s", telegram_id)
        return await self.get_one(telegram_id=telegram_id)

    async def get_or_create_by_telegram(
        self,
        telegram_id: int,
        **default_data,
    ) -> tuple[UserModel, bool]:
        """
        Получает пользователя по Telegram ID или создаёт нового.

        Args:
            telegram_id: ID пользователя в Telegram
            **default_data: Данные для создания (если не существует)

        Returns:
            Tuple[UserModel, bool]: (пользователь, создан_ли_новый)

        Example:
            ```python
            user, created = await repo.get_or_create_by_telegram(
                telegram_id=123456,
                name="Владимир",
                last_name="Иванов"
            )
            if created:
                print("Новый пользователь!")
            ```
        """
        existing = await self.get_by_telegram_id(telegram_id)
        if existing:
            logger.debug("User with telegram_id=%s already exists", telegram_id)
            return existing, False

        logger.debug("Creating new user with telegram_id=%s", telegram_id)
        user = await self.create(telegram_id=telegram_id, **default_data)
        return user, True
