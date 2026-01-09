from pydantic import EmailStr, Field

from bot.schemas.base import BaseReadSchema, BaseSchema


class UserProfile(BaseReadSchema):
    """
    Схема для чтения данных пользователя.
    """

    name: str
    last_name: str
    mid_name: str | None
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
    """

    name: str | None = Field(None, min_length=1, max_length=100)
    mid_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
