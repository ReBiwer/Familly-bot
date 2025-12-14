from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.infrastructure.db.models.base import BaseModel

if TYPE_CHECKING:
    from .employer import EmployerModel


class VacancyModel(BaseModel):
    __tablename__ = "vacancies"

    hh_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    url_vacancy: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

    # experience from domain is a TypedDict with id and name
    experience: Mapped[dict] = mapped_column(JSONB, nullable=False)

    description: Mapped[str] = mapped_column(String, nullable=False)
    key_skills: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    employer_id: Mapped[str] = mapped_column(ForeignKey("employers.id"))
    employer: Mapped["EmployerModel"] = relationship(back_populates="vacancies", lazy="selectin")
