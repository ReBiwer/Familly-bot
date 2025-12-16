"""
Тесты для Pydantic схем.

Проверяют валидацию данных на входе и выходе API.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError
from src.schemas import UserCreate, UserRead, UserUpdate


class TestUserCreate:
    """Тесты для схемы создания пользователя."""

    def test_valid_minimal(self):
        """Создание с минимальными обязательными полями."""
        user = UserCreate(name="Владимир", last_name="Иванов")

        assert user.name == "Владимир"
        assert user.last_name == "Иванов"
        assert user.mid_name is None
        assert user.phone is None
        assert user.email is None
        assert user.telegram_id is None

    def test_valid_full(self):
        """Создание со всеми полями."""
        user = UserCreate(
            name="Владимир",
            mid_name="Петрович",
            last_name="Иванов",
            phone="+79991234567",
            email="test@example.com",
            telegram_id=123456789,
        )

        assert user.name == "Владимир"
        assert user.mid_name == "Петрович"
        assert user.last_name == "Иванов"
        assert user.phone == "+79991234567"
        assert user.email == "test@example.com"
        assert user.telegram_id == 123456789

    def test_strips_whitespace(self):
        """Проверка автоматического удаления пробелов."""
        user = UserCreate(name="  Владимир  ", last_name="  Иванов  ")

        assert user.name == "Владимир"
        assert user.last_name == "Иванов"

    def test_missing_required_name(self):
        """Ошибка при отсутствии имени."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(last_name="Иванов")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_missing_required_last_name(self):
        """Ошибка при отсутствии фамилии."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(name="Владимир")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("last_name",) for e in errors)

    def test_empty_name_fails(self):
        """Ошибка при пустом имени."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(name="", last_name="Иванов")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_invalid_email(self):
        """Ошибка при невалидном email."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(name="Владимир", last_name="Иванов", email="not-an-email")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("email",) for e in errors)

    def test_name_too_long(self):
        """Ошибка при слишком длинном имени."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(name="A" * 101, last_name="Иванов")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)


class TestUserRead:
    """Тесты для схемы чтения пользователя."""

    def test_valid_read(self):
        """Чтение с обязательными полями."""
        user = UserRead(
            id=1,
            created_at=datetime.now(),
            name="Владимир",
            mid_name=None,
            last_name="Иванов",
            phone=None,
            email=None,
            telegram_id=None,
        )

        assert user.id == 1
        assert user.name == "Владимир"

    def test_full_name_without_midname(self):
        """Полное имя без отчества."""
        user = UserRead(
            id=1,
            created_at=datetime.now(),
            name="Владимир",
            mid_name=None,
            last_name="Иванов",
            phone=None,
            email=None,
            telegram_id=None,
        )

        assert user.full_name == "Иванов Владимир"

    def test_full_name_with_midname(self):
        """Полное имя с отчеством."""
        user = UserRead(
            id=1,
            created_at=datetime.now(),
            name="Владимир",
            mid_name="Петрович",
            last_name="Иванов",
            phone=None,
            email=None,
            telegram_id=None,
        )

        assert user.full_name == "Иванов Владимир Петрович"

    def test_from_orm_model(self):
        """Создание из ORM-подобного объекта (from_attributes)."""

        class FakeORM:
            id = 1
            created_at = datetime.now()
            name = "Владимир"
            mid_name = None
            last_name = "Иванов"
            phone = None
            email = "test@example.com"
            telegram_id = 123456

        user = UserRead.model_validate(FakeORM())

        assert user.id == 1
        assert user.name == "Владимир"
        assert user.email == "test@example.com"


class TestUserUpdate:
    """Тесты для схемы обновления пользователя."""

    def test_empty_update(self):
        """Пустое обновление (все None)."""
        update = UserUpdate()

        assert update.name is None
        assert update.last_name is None
        assert update.email is None

    def test_partial_update(self):
        """Частичное обновление."""
        update = UserUpdate(email="new@example.com", phone="+79991234567")

        assert update.email == "new@example.com"
        assert update.phone == "+79991234567"
        assert update.name is None

    def test_get_update_data(self):
        """Получение только заполненных полей для update."""
        update = UserUpdate(email="new@example.com", phone="+79991234567")

        # Получаем только непустые поля
        update_data = {k: v for k, v in update.model_dump().items() if v is not None}

        assert update_data == {
            "email": "new@example.com",
            "phone": "+79991234567",
        }

    def test_invalid_email_on_update(self):
        """Ошибка при невалидном email в обновлении."""
        with pytest.raises(ValidationError):
            UserUpdate(email="not-an-email")
