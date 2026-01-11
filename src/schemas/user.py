"""
Схемы для работы с пользователями.

UserCreate — для регистрации нового пользователя
UserRead — для возврата данных пользователя
UserUpdate — для обновления данных (все поля опциональные)
"""

from pydantic import EmailStr, Field

from src.schemas.base import BaseReadSchema, BaseSchema


class UserCreate(BaseSchema):
    """
    Схема для создания пользователя.

    Обязательные поля: name, last_name
    Опциональные: mid_name, phone, email, telegram_id

    Example:
        ```python
        user_data = UserCreate(
            name="Владимир",
            last_name="Иванов",
            telegram_id=123456789
        )
        ```
    """

    name: str = Field(..., min_length=1, max_length=100, description="Имя")
    mid_name: str | None = Field(None, max_length=100, description="Отчество")
    last_name: str = Field(..., min_length=1, max_length=100, description="Фамилия")
    phone: str | None = Field(None, max_length=20, description="Номер телефона")
    email: EmailStr | None = Field(None, description="Email адрес")
    telegram_id: int | None = Field(None, description="Telegram ID пользователя")


class UserRead(BaseReadSchema):
    """
    Схема для чтения данных пользователя.

    Наследует id и created_at из BaseReadSchema.
    Используется для response_model в API эндпоинтах.

    Example:
        ```python
        @router.get("/users/{user_id}", response_model=UserRead)
        async def get_user(user_id: int):
            ...
        ```
    """

    name: str
    mid_name: str | None
    last_name: str
    phone: str | None
    email: str | None
    telegram_id: int | None

    @property
    def full_name(self) -> str:
        """Возвращает полное имя пользователя."""
        parts = [self.last_name, self.name]
        if self.mid_name:
            parts.append(self.mid_name)
        return " ".join(parts)


class UserUpdate(BaseSchema):
    """
    Схема для обновления данных пользователя.

    Все поля опциональные — передаются только те, которые нужно изменить.

    Example:
        ```python
        # Обновить только email
        update_data = UserUpdate(email="new@example.com")

        # Обновить несколько полей
        update_data = UserUpdate(
            phone="+7999123456",
            email="new@example.com"
        )
        ```
    """

    name: str | None = Field(None, min_length=1, max_length=100)
    mid_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
