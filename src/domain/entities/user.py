from pydantic import EmailStr
from src.domain.entities.base import BaseEntity
from src.domain.entities.resume import ResumeEntity


class UserEntity(BaseEntity):
    hh_id: str
    name: str
    mid_name: str | None = None
    last_name: str
    phone: str | None = None
    email: EmailStr | None = None
    telegram_id: int | None = None
    resumes: list[ResumeEntity]

    def __str__(self):
        mid_name = f"Отчество: {self.mid_name}\n" if self.mid_name else ""
        return (
            f"Имя: {self.name}\n"
            f"{mid_name}"
            f"Фамилия: {self.last_name}\n"
            f"Резюме: {'\n\n'.join(str(resume) for resume in self.resumes)}"
        )
