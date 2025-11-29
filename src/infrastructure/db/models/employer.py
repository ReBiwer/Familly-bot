from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.infrastructure.db.models.base import BaseModel

if TYPE_CHECKING:
    from .vacancy import VacancyModel


class EmployerModel(BaseModel):
    __tablename__ = "employers"

    hh_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)

    vacancies: Mapped[list["VacancyModel"]] = relationship(
        back_populates="employer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
