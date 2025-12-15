from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from src.db.models.base import BaseModel


class UserModel(BaseModel):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String, nullable=False)
    mid_name: Mapped[str] = mapped_column(String, nullable=True)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    telegram_id: Mapped[int | None] = mapped_column(Integer, unique=True, index=True, nullable=True)
