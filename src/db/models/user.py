from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.db.models.base import BaseModel


class UserModel(BaseModel):
    __tablename__ = "users"

    name: Mapped[str]
    mid_name: Mapped[str]
    last_name: Mapped[str]
    phone: Mapped[str | None]
    email: Mapped[str | None]
    telegram_id: Mapped[int | None] = mapped_column(Integer, unique=True, index=True, nullable=True)
