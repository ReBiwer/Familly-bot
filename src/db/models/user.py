from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.db.models.base import BaseModel


class UserModel(BaseModel):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=True)
    name: Mapped[str]
    mid_name: Mapped[str | None]
    last_name: Mapped[str | None]
    phone: Mapped[str | None]
    email: Mapped[str | None]

    role: Mapped[str] = mapped_column(default="member", nullable=False)
