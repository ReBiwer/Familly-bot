from abc import ABC, abstractmethod
from typing import TypedDict

from src.domain.entities.employer import EmployerEntity
from src.domain.entities.response import ResponseToVacancyEntity
from src.domain.entities.resume import ResumeEntity
from src.domain.entities.vacancy import VacancyEntity


class GenerateResponseData(TypedDict):
    user_id: int
    vacancy: VacancyEntity
    resume: ResumeEntity
    employer: EmployerEntity | None
    user_rules: dict


class IAIService(ABC):
    @abstractmethod
    async def generate_response(self, data: GenerateResponseData) -> ResponseToVacancyEntity:
        """Метод для генерации отклика на вакансию"""
        ...

    @abstractmethod
    async def regenerate_response(
        self,
        user_id: int,
        response: str,
        user_comments: str,
        data: GenerateResponseData | None = None,
    ) -> ResponseToVacancyEntity:
        """Метод для исправления ранее сгенерированного отклика"""
        ...
