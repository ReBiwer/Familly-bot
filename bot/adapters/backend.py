import logging

import httpx

from bot.constants import BackendUrls
from bot.entities import ResumeEntity, UserEntity

logger = logging.getLogger(__name__)


class BackendAdapter:
    def __init__(self, base_url: str):
        self._client = httpx.AsyncClient(base_url=base_url)

    async def _request_get(self, uri: str, /, **kwargs) -> httpx.Response:
        return await self._client.get(uri, params=kwargs)

    async def _request_post(self, uri: str, /, **kwargs) -> httpx.Response:
        return await self._client.post(uri, data=kwargs)

    async def get_auth_url(self, state: str) -> str:
        result = await self._request_get(BackendUrls.GET_AUTH_URL, state=state)
        data = result.json()
        return data.get("result", "")

    async def get_user(self, user_id: int) -> UserEntity:
        result = await self._request_get(BackendUrls.GET_USER, user_id=user_id)
        return UserEntity.model_validate_json(result.content)

    async def get_resume(self, resume_id: int) -> ResumeEntity:
        result = await self._request_get(BackendUrls.GET_RESUME, resume_id=resume_id)
        return ResumeEntity.model_validate_json(result.content)

    async def get_llm_response(
        self,
        telegram_id: int,
        url_vacancy: str,
        past_response: str | None = None,
        user_comments: str | None = None,
    ) -> str:
        data = {
            "telegram_id": telegram_id,
            "url_vacancy": url_vacancy,
        }
        if past_response and user_comments:
            data.update(past_response=past_response, user_comments=user_comments)
        result = await self._request_get(BackendUrls.GET_LLM_RESPONSE, telegram_id=telegram_id)
        data = result.json()
        return data.get("result", "")

    async def post_response_to_vacancy(self, url_vacancy: str, resume_id: int, text: str) -> None:
        await self._request_post(
            BackendUrls.POST_RESPONSE_TO_VACANCY,
            resume_id=resume_id,
            url_vacancy=url_vacancy,
            text=text,
        )
