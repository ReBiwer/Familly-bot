from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.infrastructure.db.models.base import BaseModel

if TYPE_CHECKING:
    from .resume import ResumeModel


class UserModel(BaseModel):
    __tablename__ = "users"

    hh_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    mid_name: Mapped[str] = mapped_column(String, nullable=True)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    telegram_id: Mapped[int | None] = mapped_column(Integer, unique=True, index=True, nullable=True)

    resumes: Mapped[list["ResumeModel"]] = relationship(
        back_populates="user",
        passive_deletes=True,
        cascade="all, delete-orphan",
        lazy="selectin",
        single_parent=True,
    )
