import re
from abc import ABC, abstractmethod
from typing import TypedDict

from src.application.services.ai_service import GenerateResponseData
from src.domain.entities.employer import EmployerEntity
from src.domain.entities.response import ResponseToVacancyEntity
from src.domain.entities.resume import JobExperienceEntity, ResumeEntity
from src.domain.entities.user import UserEntity
from src.domain.entities.vacancy import Experience, VacancyEntity


class AuthTokens(TypedDict):
    access_token: str
    refresh_token: str


class IHHService(ABC):
    @staticmethod
    def extract_vacancy_id_from_url(url: str) -> str:
        pattern = r"\/vacancy\/(?P<id>\d+)(?=[\/?#]|$)"
        match = re.search(pattern, url)
        return match.group(1)

    def _serialize_data_user(self, data: dict) -> UserEntity:
        """
        Сериализация данных пользователя возвращаемых из API hh.ru
        :param data: пример возвращаемых данных можно посмотреть тут: https://api.hh.ru/openapi/redoc#tag/Informaciya-o-soiskatele
        :return: UserEntity
        """
        user_data = {
            "hh_id": data["id"],
            "name": data["first_name"],
            "mid_name": data["mid_name"],
            "last_name": data["last_name"],
            "phone": data["phone"],
            "email": data["email"] if data["email"] else None,
            "resumes": [self._serialize_data_resume(data) for data in data["resumes_data"]],
        }
        return UserEntity.model_validate(user_data)

    @staticmethod
    def _serialize_data_vacancy(data: dict) -> VacancyEntity:
        """
        Сериализация данных возвращаемых из API hh.ru
        :param data: пример возвращаемых данных можно посмотреть тут: https://api.hh.ru/openapi/redoc#tag/Vakansii
        :return: VacancyEntity
        """
        vacancy_data = {
            "hh_id": data["id"],
            "url_vacancy": data["alternate_url"],
            "name": data["name"],
            "experience": Experience(id=data["experience"]["id"], name=data["experience"]["name"]),
            "description": data["description"],
            "key_skills": data["key_skills"],
            "employer_id": data["employer"]["id"],
        }
        return VacancyEntity.model_validate(vacancy_data)

    @staticmethod
    def _serialize_data_employer(data: dict) -> EmployerEntity:
        """
        Сериализация данных возвращаемых из API hh.ru
        :param data: пример возвращаемых данных можно посмотреть тут: https://api.hh.ru/openapi/redoc#tag/Podskazki/operation/get-registered-companies-suggests
        :return: EmployerEntity
        """
        employer_data = {
            "hh_id": data["id"],
            "name": data["name"],
            "description": data["description"],
        }
        return EmployerEntity.model_validate(employer_data)

    @staticmethod
    def _serialize_data_resume(data: dict) -> ResumeEntity:
        """
        Сериализация данных возвращаемых из API hh.ru
        :param data: пример возвращаемых данных можно посмотреть тут: https://api.hh.ru/openapi/redoc#tag/Rezyume.-Prosmotr-informacii/operation/get-resume
        :return: ResumeEntity
        """
        contact_map = {"phone": "contact_phone", "email": "contact_email"}
        contact_dict = {
            contact_map[contact["kind"]]: contact["contact_value"]
            for contact in data["contact"]
            if contact_map.get(contact["kind"])
        }

        resume_data = {
            "hh_id": data["id"],
            "title": data["title"],
            "name": data["first_name"],
            "surname": data["last_name"],
            "job_experience": [
                JobExperienceEntity.model_validate(experience) for experience in data["experience"]
            ],
            "skills": data["skill_set"],
        }
        resume_data.update(contact_dict)
        return ResumeEntity.model_validate(resume_data)

    @staticmethod
    def _serialize_data_response_to_vacancy(data: dict) -> ResponseToVacancyEntity:
        """
        Сериализация данных возвращаемых из API hh.ru
        :param data: пример возвращаемых данных можно посмотреть тут: https://api.hh.ru/openapi/redoc#tag/Perepiska-(otklikipriglasheniya)-dlya-soiskatelya/operation/get-negotiations
        :return:
        """
        response_data = {
            "hh_id": data["id"],
            "url_vacancy": data["url"],
            "vacancy_id": data["id"],
            "resume_id": data["resume"]["id"],
            # ключ-значение message было добавлено отдельно
            # схема получения находится тут
            # https://api.hh.ru/openapi/redoc#tag/Perepiska-(otklikipriglasheniya)-dlya-soiskatelya/operation/get-negotiation-messages
            "message": data["message"] if data["message"] else "",
            "quality": True,
        }
        return ResponseToVacancyEntity.model_validate(response_data)

    @abstractmethod
    def get_auth_url(self, state: str) -> str:
        """Метод для получения url для OAuth авторизации"""
        ...

    @abstractmethod
    async def auth(self, code: str) -> tuple[UserEntity, AuthTokens]:
        """Метод для авторизации, принимает код полученный после редиректа
        возвращает словарь с access и refresh токенами"""
        ...

    @abstractmethod
    async def get_me(self, subject: int | str) -> UserEntity:
        """Метод возвращает информацию о залогиненным пользователе"""
        ...

    @abstractmethod
    async def get_vacancies(self, subject: int | str, **filter_query) -> list[VacancyEntity]:
        """Метод для поиска вакансий по фильтрам"""
        ...

    @abstractmethod
    async def get_vacancy_data(self, subject: int | str, vacancy_id: str) -> VacancyEntity:
        """Метод для получения информации о вакансии"""
        ...

    @abstractmethod
    async def get_employer_data(self, subject: int | str, employer_id: str) -> EmployerEntity:
        """Метод для получения информации о работодателе"""
        ...

    @abstractmethod
    async def get_resume_data(self, subject: int | str, resume_id: str) -> ResumeEntity:
        """Метод для получения информации из резюме авторизованного пользователя"""
        ...

    @abstractmethod
    async def get_user_rules(self) -> dict:
        """Метод для получения правил пользователя для формирования отклика"""
        ...

    @abstractmethod
    async def data_collect_for_llm(
        self,
        subject: int | str,
        user_id: int,
        vacancy_id: str,
        resume_id: str,
    ) -> GenerateResponseData:
        """Метод для сбора всех данных для отправки в llm для генерации отклика"""
        ...

    @abstractmethod
    async def send_response_to_vacancy(self, response: ResponseToVacancyEntity) -> bool:
        """Метод для отправки отклика на вакансию"""
        ...
