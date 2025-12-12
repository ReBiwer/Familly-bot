from typing import TypedDict

from bot.entities.base import BaseEntity


class Experience(TypedDict):
    id: str | int
    name: str


class VacancyEntity(BaseEntity):
    hh_id: str
    url_vacancy: str
    name: str
    experience: Experience
    description: str
    key_skills: list[dict[str, str]]
    employer_id: str

    def __str__(self):
        return (
            f"Вакансия {self.name}, описание вакансии - {self.description}, "
            f"необходимые навыки - {', '.join([value['name'] for value in self.key_skills])}\n"
        )
