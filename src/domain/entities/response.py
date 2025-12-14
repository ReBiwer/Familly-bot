from src.domain.entities.base import BaseEntity


class ResponseToVacancyEntity(BaseEntity):
    url_vacancy: str
    vacancy_hh_id: str
    resume_hh_id: str
    message: str
    quality: bool | None = None

    def __str__(self):
        return (
            f"Сообщение отклика: {self.message}\n"
            f"Релевантность отклика: {'релевантный' if self.quality else 'не релевантный'}"
        )
