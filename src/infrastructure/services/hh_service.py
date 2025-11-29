import asyncio
import logging
from typing import Any

import httpx
from hh_api.auth import TokenPair
from hh_api.client import HHClient, Subject, TokenManager
from hh_api.exceptions import HHAPIError, HHAuthError, HHNetworkError
from httpx import Response
from src.application.services.ai_service import GenerateResponseData
from src.application.services.hh_service import AuthTokens, IHHService
from src.domain.entities.employer import EmployerEntity
from src.domain.entities.response import ResponseToVacancyEntity
from src.domain.entities.resume import ResumeEntity
from src.domain.entities.user import UserEntity
from src.domain.entities.vacancy import VacancyEntity

logger = logging.getLogger(__name__)


class CustomHHClient(HHClient):
    async def get_employer(
        self, employer_id: str, *, subject: Subject | None = None
    ) -> dict[str, Any]:
        return (
            await self._request(
                "GET",
                f"/employers/{employer_id}",
                subject=subject,
            )
        ).json()

    @staticmethod
    def _check_status_code_response(response: Response) -> None:
        """Проверяет наличие ошибок в запросе"""
        # авторизационные ошибки пробрасываем как HHAuthError
        if response.status_code in (401, 403):
            # У многих интеграций это значит «нужно переавторизовать пользователя».
            logger.error(
                "Пользователь не авторизован. Пользователю нужно выполнить авторизацию на hh.ru"
            )
            raise HHAuthError(response.status_code, response.text)

        if response.status_code >= 400:
            logger.error(
                "Ошибка при обращении к API hh.ru code=%s. %s",
                response.status_code,
                response.text,
            )
            raise HHAPIError(response.status_code, response.text)

        response.raise_for_status()

    async def authorization(self, tokens: TokenPair) -> dict[str, Any]:
        url_user = f"{self.base_url}/me"
        url_resumes = f"{self.base_url}/resumes/mine"
        last_exc: Exception | None = None
        req_headers = {
            "Authorization": f"Bearer {tokens.access_token}",
            "User-Agent": self.user_agent,
        }
        for attempt in range(1, self.retries + 1):
            try:
                logger.debug(
                    "Авторизация пользователя HH. Попытка %s/%s",
                    attempt,
                    self.retries,
                )
                # TODO Запрос информации о пользователе и запрос резюме можно выполнять параллельно через gather
                # Получаем информацию о пользователе
                resp_user = await self._client.request(
                    "GET",
                    url_user,
                    headers=req_headers,
                )
                self._check_status_code_response(resp_user)
                user_data = resp_user.json()
                logger.debug(
                    "Информация о пользователе получена. hh_id=%s",
                    user_data.get("id"),
                )

                # Получаем список резюме пользователя
                resp_resumes_user = await self._client.request(
                    "GET",
                    url_resumes,
                    headers=req_headers,
                )
                self._check_status_code_response(resp_resumes_user)
                resumes_items = resp_resumes_user.json()["items"]
                logger.debug(
                    "Получен список резюме пользователя. Количество=%s",
                    len(resumes_items),
                )
                # Запрашиваем детальную информацию по каждому резюме
                resumes_data: list[Response] = await asyncio.gather(
                    *[
                        self._client.request(
                            "GET",
                            f"{self.base_url}/resumes/{data['id']}",
                            headers=req_headers,
                        )
                        for data in resumes_items
                    ]
                )
                for response in resumes_data:
                    self._check_status_code_response(response)
                # Добавляем информацию о резюме к общей инфе о пользователе
                user_data["resumes_data"] = [resume.json() for resume in resumes_data]
                logger.info(
                    "Пользователь hh_id=%s успешно авторизован. Резюме загружено=%s",
                    user_data.get("id"),
                    len(user_data["resumes_data"]),
                )
                return user_data

            except httpx.RequestError as e:
                logger.warning("Ошибка отправки запроса: %s", e)
                last_exc = e
                if attempt < self.retries:
                    logger.warning(
                        "Повторная попытка отправки через %s сек.",
                        self.backoff_base * (2 ** (attempt - 1)),
                    )
                    await asyncio.sleep(self.backoff_base * (2 ** (attempt - 1)))
                    continue
                logger.error("HHNetworkError: %s", e)
                raise HHNetworkError(str(e)) from e

            except HHAPIError as e:
                logger.warning("HHAPIError: %s", e)
                if getattr(e, "status_code", None):
                    logger.debug(
                        "Ответ HH API c ошибкой. status_code=%s, попытка=%s/%s",
                        e.status_code,
                        attempt,
                        self.retries,
                    )
                last_exc = e
                # 5xx — можно попробовать повторить
                if 500 <= getattr(e, "status_code", 0) < 600 and attempt < self.retries:
                    logger.warning(
                        "Повторная попытка отправки через %s сек.",
                        self.backoff_base * (2 ** (attempt - 1)),
                    )
                    await asyncio.sleep(self.backoff_base * (2 ** (attempt - 1)))
                    continue
                raise

        assert last_exc is not None
        raise last_exc

    async def get_me(self, subject: Subject | None = None) -> dict[str, Any]:
        logger.debug("Запрос профиля HH. subject=%s", subject)
        return (
            await self._request(
                "GET",
                "/me",
                subject=subject,
            )
        ).json()

    async def get_resumes_from_url(
        self, url: str, subject: Subject | None = None
    ) -> dict[str, Any]:
        logger.debug("Запрос списка резюме HH. subject=%s, url=%s", subject, url)
        return (
            await self._request(
                "GET",
                url,
                subject=subject,
            )
        ).json()

    async def get_vacancies(self, subject: Subject | None, **filter_query) -> dict[str, Any]:
        logger.debug(
            "Запрос вакансий HH. subject=%s, фильтры=%s",
            subject,
            filter_query,
        )
        return (
            await self._request("GET", path="/vacancies", subject=subject, params=filter_query)
        ).json()


class CustomTokenManager(TokenManager):
    async def exchange_auth_code(self, code: str) -> TokenPair:
        """Метод для обменя exchange token'а на access_token и refresh_token"""
        data = {
            "grant_type": "authorization_code",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": code,
            "redirect_uri": self.config.redirect_uri,
        }
        headers = {"User-Agent": self.user_agent}
        logger.debug("Request to exchange code on tokens")
        resp = await self._post_with_retry(self.config.token_url, data=data, headers=headers)
        payload = resp.json()
        tokens = self._tokenpair_from_payload(payload)
        logger.debug("Tokens received")
        return tokens

    async def save_tokens(self, subject: Subject, tokens: TokenPair) -> None:
        await self.store.set_tokens(subject, tokens)
        logger.debug("Tokens are saved")


class HHService(IHHService):
    def __init__(self, token_manager: CustomTokenManager):
        self._hh_tm = token_manager
        self.hh_client = CustomHHClient(self._hh_tm)

    def get_auth_url(self, state: str):
        logger.debug("Генерация auth URL для state=%s", state)
        return self._hh_tm.authorization_url(state)

    async def aclose_hh_client(self):
        logger.debug("Закрытие HTTP-клиента HH")
        await self.hh_client.aclose()

    async def auth(self, code: str) -> tuple[UserEntity, AuthTokens]:
        logger.info("Начало авторизации пользователя через HH")
        tokens = await self._hh_tm.exchange_auth_code(code)
        logger.debug("Токены получены, запрос профиля пользователя HH")
        resp = await self.hh_client.authorization(tokens)
        auth_user = self._serialize_data_user(resp)
        await self._hh_tm.save_tokens(auth_user.hh_id, tokens)
        logger.info("Пользователь hh_id=%s успешно авторизован", auth_user.hh_id)
        return auth_user, AuthTokens(
            access_token=tokens.access_token, refresh_token=tokens.refresh_token
        )

    async def get_me(self, subject: Subject | None) -> UserEntity:
        user_data = await self.hh_client.get_me(subject=subject)
        logger.debug("Request user hh profile (hh_id=%s)", subject)

        resumes_data = await self.hh_client.get_resumes_from_url("/resumes/mine", subject=subject)
        # отдельный запрос делается, для подгрузки description
        # почему-то при загрузке всех резюме этого поля нет
        logger.debug("Request info about resumes user's")
        valid_resumes_data = await asyncio.gather(
            *[
                self.hh_client.get_resume(data["id"], subject=subject)
                for data in resumes_data["items"]
            ]
        )
        logger.debug(
            "Загружено %s резюме пользователя hh_id=%s",
            len(valid_resumes_data),
            subject,
        )
        user_data["resumes_data"] = valid_resumes_data
        return self._serialize_data_user(user_data)

    async def get_vacancies(self, subject: Subject | None, **filter_query) -> list[VacancyEntity]:
        logger.info(
            "Получение списка вакансий пользователя hh_id=%s с фильтрами=%s",
            subject,
            filter_query,
        )
        vacancies = await self.hh_client.get_vacancies(subject, **filter_query)
        logger.debug(
            "Получено %s записей вакансий. Начинаем детальную загрузку",
            len(vacancies.get("items", [])),
        )
        result = await asyncio.gather(
            *[self.get_vacancy_data(subject, vacancy["id"]) for vacancy in vacancies["items"]]
        )
        logger.info("Загружены вакансии пользователя hh_id=%s", subject)
        return result

    async def get_vacancy_data(self, subject: Subject | None, vacancy_id: str) -> VacancyEntity:
        logger.debug(
            "Запрос детальной информации по вакансии vacancy_id=%s (subject=%s)",
            vacancy_id,
            subject,
        )
        data = await self.hh_client.get_vacancy(vacancy_id, subject=subject)
        return self._serialize_data_vacancy(data)

    async def get_employer_data(self, subject: Subject | None, employer_id: str) -> EmployerEntity:
        logger.debug(
            "Запрос информации о работодателе employer_id=%s (subject=%s)",
            employer_id,
            subject,
        )
        data = await self.hh_client.get_employer(employer_id, subject=subject)
        return self._serialize_data_employer(data)

    async def get_resume_data(self, subject: Subject | None, resume_id: str) -> ResumeEntity:
        logger.debug(
            "Запрос резюме resume_id=%s (subject=%s)",
            resume_id,
            subject,
        )
        data = await self.hh_client.get_resume(resume_id, subject=subject)
        return self._serialize_data_resume(data)

    async def get_user_rules(self) -> dict:
        logger.debug("Получение пользовательских правил ответа")
        rules = {
            "rule_1": "Длина отклика не более 800 символов. Допускается отклонение +- 20 символов"
        }
        return rules

    async def data_collect_for_llm(
        self,
        subject: Subject | None,
        user_id: int,
        vacancy_id: str,
        resume_id: str,
    ) -> GenerateResponseData:
        logger.info(
            "Сбор данных для генерации отклика. user_id=%s, vacancy_id=%s, resume_id=%s",
            user_id,
            vacancy_id,
            resume_id,
        )
        vacancy_data = await self.get_vacancy_data(subject, vacancy_id)
        tasks = [
            self.get_employer_data(subject, vacancy_data.employer_id),
            self.get_resume_data(subject, resume_id),
            self.get_user_rules(),
        ]
        result = await asyncio.gather(*tasks)
        logger.debug(
            "Данные для генерации отклика собраны. employer_id=%s",
            vacancy_data.employer_id,
        )
        return GenerateResponseData(
            user_id=user_id,
            vacancy=vacancy_data,
            employer=result[0],
            resume=result[1],
            user_rules=result[2],
        )

    async def send_response_to_vacancy(self, response: ResponseToVacancyEntity) -> bool:
        logger.info(
            "Отправка отклика на вакансию vacancy_hh_id=%s через резюме resume_hh_id=%s",
            response.vacancy_hh_id,
            response.resume_hh_id,
        )
        return await self.hh_client.apply_to_vacancy(
            resume_id=response.resume_hh_id,
            vacancy_id=response.vacancy_hh_id,
            message=response.message,
        )
