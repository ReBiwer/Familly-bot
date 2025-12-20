import hashlib
import hmac
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from src.db.repositories import RefreshTokenRepository, UserRepository
from src.schemas import TelegramAuthRequest, TokenPair
from src.settings import app_settings
from src.utils import create_access_token, create_refresh_token


class AuthTelegramUseCase:
    def __init__(self, user_repo: UserRepository, refresh_token_repo: RefreshTokenRepository):
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo

    async def __call__(self, request: TelegramAuthRequest) -> TokenPair:
        signature = hmac.new(
            key=app_settings.FRONT.BOT_TOKEN.encode(),
            msg=request.msg.encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()
        if signature != request.hash_str:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        expires_delta = timedelta(days=7)
        access_token = create_access_token(
            telegram_id=request.telegram_id,
            expires_delta=expires_delta,
        )

        user, _ = await self._user_repo.get_or_create_by_telegram(
            telegram_id=request.telegram_id,
            name=request.name,
            mid_name=request.mid_name,
            last_name=request.last_name,
        )
        refresh_token = create_refresh_token()
        refresh_expires_at = datetime.now(UTC) + timedelta(days=30)
        await self._refresh_token_repo.create(
            token_hash=refresh_token,
            user_id=user.id,
            expires_at=refresh_expires_at,
        )
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(expires_delta.total_seconds()),
        )
