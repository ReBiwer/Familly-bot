from pydantic import EmailStr

from bot.entities.base import BaseEntity


class UserEntity(BaseEntity):
    name: str
    mid_name: str | None = None
    last_name: str
    phone: str | None = None
    email: EmailStr | None = None
    telegram_id: int | None = None

    def __str__(self):
        mid_name = f"Отчество: {self.mid_name}\n" if self.mid_name else ""
        return f"Имя: {self.name}\n{mid_name}Фамилия: {self.last_name}\n"
