"""
Тесты для репозиториев.

Используют in-memory SQLite для изоляции тестов.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import UserModel
from src.db.repositories import UserRepository


class TestUserRepository:
    """Тесты для UserRepository."""

    async def test_create_user(self, async_session: AsyncSession):
        """Создание пользователя."""
        repo = UserRepository(async_session)

        user = await repo.create(
            name="Владимир",
            last_name="Иванов",
            telegram_id=123456,
        )

        assert user.id is not None
        assert user.name == "Владимир"
        assert user.last_name == "Иванов"
        assert user.telegram_id == 123456

    async def test_get_by_id(self, async_session: AsyncSession):
        """Получение пользователя по ID."""
        repo = UserRepository(async_session)

        # Создаём пользователя
        created = await repo.create(name="Тест", last_name="Тестов")

        # Получаем по ID
        user = await repo.get_by_id(created.id)

        assert user is not None
        assert user.id == created.id
        assert user.name == "Тест"

    async def test_get_by_id_not_found(self, async_session: AsyncSession):
        """Получение несуществующего пользователя."""
        repo = UserRepository(async_session)

        user = await repo.get_by_id(99999)

        assert user is None

    async def test_get_by_telegram_id(self, async_session: AsyncSession):
        """Получение пользователя по Telegram ID."""
        repo = UserRepository(async_session)

        # Создаём пользователя
        await repo.create(
            name="Тест",
            last_name="Тестов",
            telegram_id=777888,
        )

        # Получаем по telegram_id
        user = await repo.get_by_telegram_id(777888)

        assert user is not None
        assert user.telegram_id == 777888

    async def test_get_by_telegram_id_not_found(self, async_session: AsyncSession):
        """Telegram ID не найден."""
        repo = UserRepository(async_session)

        user = await repo.get_by_telegram_id(99999)

        assert user is None

    async def test_get_or_create_creates_new(self, async_session: AsyncSession):
        """get_or_create создаёт нового пользователя."""
        repo = UserRepository(async_session)

        user, created = await repo.get_or_create_by_telegram(
            telegram_id=111222,
            name="Новый",
            last_name="Пользователь",
        )

        assert created is True
        assert user.telegram_id == 111222
        assert user.name == "Новый"

    async def test_get_or_create_returns_existing(self, async_session: AsyncSession):
        """get_or_create возвращает существующего пользователя."""
        repo = UserRepository(async_session)

        # Создаём пользователя
        await repo.create(
            name="Существующий",
            last_name="Пользователь",
            telegram_id=333444,
        )

        # Пытаемся создать с тем же telegram_id
        user, created = await repo.get_or_create_by_telegram(
            telegram_id=333444,
            name="Другое имя",  # Это будет проигнорировано
            last_name="Другая фамилия",
        )

        assert created is False
        assert user.name == "Существующий"  # Старое имя сохранилось

    async def test_update_user(self, async_session: AsyncSession):
        """Обновление пользователя."""
        repo = UserRepository(async_session)

        # Создаём пользователя
        user = await repo.create(
            name="Старое",
            last_name="Имя",
            email=None,
        )

        # Обновляем
        updated = await repo.update(
            user.id,
            name="Новое",
            email="new@example.com",
        )

        assert updated is not None
        assert updated.name == "Новое"
        assert updated.email == "new@example.com"
        assert updated.last_name == "Имя"  # Не изменилось

    async def test_update_nonexistent(self, async_session: AsyncSession):
        """Обновление несуществующего пользователя."""
        repo = UserRepository(async_session)

        updated = await repo.update(99999, name="Тест")

        assert updated is None

    async def test_delete_user(self, async_session: AsyncSession):
        """Удаление пользователя."""
        repo = UserRepository(async_session)

        # Создаём пользователя
        user = await repo.create(name="Удалить", last_name="Меня")

        # Удаляем
        deleted = await repo.delete(user.id)

        assert deleted is True

        # Проверяем, что удалён
        found = await repo.get_by_id(user.id)
        assert found is None

    async def test_delete_nonexistent(self, async_session: AsyncSession):
        """Удаление несуществующего пользователя."""
        repo = UserRepository(async_session)

        deleted = await repo.delete(99999)

        assert deleted is False

    async def test_get_one_with_filters(self, async_session: AsyncSession):
        """Получение одного пользователя по фильтрам."""
        repo = UserRepository(async_session)

        # Создаём пользователей
        await repo.create(name="Иван", last_name="Иванов", email="ivan@test.com")
        await repo.create(name="Пётр", last_name="Петров", email="petr@test.com")

        # Ищем по email
        user = await repo.get_one(email="ivan@test.com")

        assert user is not None
        assert user.name == "Иван"

    async def test_get_many(self, async_session: AsyncSession):
        """Получение списка пользователей."""
        repo = UserRepository(async_session)

        # Создаём пользователей с одинаковой фамилией
        await repo.create(name="Иван", last_name="Иванов")
        await repo.create(name="Пётр", last_name="Иванов")
        await repo.create(name="Сидор", last_name="Сидоров")

        # Получаем всех Ивановых
        users = await repo.get_many(last_name="Иванов")

        assert len(users) == 2
        assert all(u.last_name == "Иванов" for u in users)

    async def test_get_many_empty(self, async_session: AsyncSession):
        """Пустой список при отсутствии результатов."""
        repo = UserRepository(async_session)

        users = await repo.get_many(last_name="Несуществующий")

        assert users == []

