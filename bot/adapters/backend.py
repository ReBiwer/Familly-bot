import hashlib
import hmac

from httpx import AsyncClient

from bot.schemas import AuthRequest, TokenPair, UserProfile, UserUpdate
from bot.settings import bot_settings


class BackendAdapter:
    def __init__(
        self,
        telegram_id: int,
        first_name: str,
        mid_name: str | None = None,
        last_name: str | None = None,
        tokens: TokenPair | None = None,
    ):
        self.telegram_id = telegram_id
        self.first_name = first_name
        self.mid_name = mid_name
        self.last_name = last_name
        self._client = AsyncClient(base_url=bot_settings.BACKEND.PATH)
        self._tokens: TokenPair | None = tokens

    @property
    def _msg_str(self) -> str:
        return (
            f"telegram_id={self.telegram_id}\n"
            f"name={self.first_name}\n"
            f"mid_name={self.mid_name or None}\n"
            f"last_name={self.last_name or None}"
        )

    @property
    def headers(self) -> dict | None:
        if self._tokens:
            headers = {"Authorization": f"Bearer {self._tokens.access_token}"}
            return headers
        return None

    async def auth(self) -> TokenPair:
        signature_str = hmac.new(
            key=bot_settings.BOT_TOKEN.encode(),
            msg=self._msg_str.encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()
        data = AuthRequest.model_validate(
            {
                "telegram_id": self.telegram_id,
                "first_name": self.first_name,
                "mid_name": self.mid_name,
                "last_name": self.last_name,
                "hash_str": signature_str,
            }
        )
        response = await self._client.post("/auth/telegram", json=data.model_dump())
        response.raise_for_status()
        self._tokens = TokenPair.model_validate(response.json())
        return self._tokens

    async def refresh(self) -> TokenPair:
        data = {"telegram_id": self.telegram_id, "refresh_token": self._tokens.refresh_token}
        response = await self._client.post("/auth/telegram/refresh", json=data)
        response.raise_for_status()
        return TokenPair.model_validate(response.json())

    async def get_me(self) -> UserProfile:
        if self.headers is None:
            await self.auth()
        response = await self._client.get("/users/me", headers=self.headers)
        response.raise_for_status()
        return UserProfile.model_validate(response.json())

    async def update_user(self, data: UserUpdate) -> UserProfile:
        if self.headers is None:
            await self.auth()
        response = await self._client.patch(
            "/users/telegram",
            json=data.model_dump(),
            headers=self.headers,
        )
        response.raise_for_status()
        return UserProfile.model_validate(response.json())
