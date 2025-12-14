from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.infrastructure.db.models.base import BaseModel

if TYPE_CHECKING:
    from .user import UserModel


class JobExperienceModel(BaseModel):
    __tablename__ = "job_experiences"

    resume_id: Mapped[str] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), index=True)

    company: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[str] = mapped_column(String, nullable=False)
    start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=False)

    resume: Mapped["ResumeModel"] = relationship(
        back_populates="job_experience", lazy="joined", single_parent=True
    )


class ResumeModel(BaseModel):
    __tablename__ = "resumes"

    hh_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    title: Mapped[str]
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String, nullable=False)
    surname: Mapped[str] = mapped_column(String, nullable=False)

    contact_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String, nullable=True)

    skills: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    user: Mapped["UserModel"] = relationship(back_populates="resumes", lazy="joined")

    job_experience: Mapped[list[JobExperienceModel]] = relationship(
        back_populates="resume",
        cascade="all, delete-orphan",
        order_by=lambda: JobExperienceModel.start.asc(),
        lazy="selectin",
    )
