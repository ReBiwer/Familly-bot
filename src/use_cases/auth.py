import hashlib
import hmac
import logging
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from src.db.models import RefreshTokenModel
from src.db.repositories import RefreshTokenRepository, UserRepository
from src.schemas import RefreshTelegramRequest, TelegramAuthRequest, TokenPair
from src.settings import app_settings
from src.utils import create_access_token, create_refresh_token, get_scopes_for_user

logger = logging.getLogger(__name__)


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

        user, _ = await self._user_repo.get_or_create_by_telegram(
            telegram_id=request.telegram_id,
            name=request.name,
            mid_name=request.mid_name,
            last_name=request.last_name,
        )

        scopes = get_scopes_for_user(user)

        expires_delta = timedelta(days=7)
        access_token = create_access_token(
            telegram_id=request.telegram_id,
            expires_delta=expires_delta,
            scopes_permissions=scopes,
        )

        refresh_token = create_refresh_token()
        refresh_expires_at = datetime.now(UTC) + timedelta(days=30)
        await self._refresh_token_repo.create(
            token_hash=refresh_token,
            user_id=user.id,
            expires_at=refresh_expires_at,
            device_info="telegram",
        )
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(expires_delta.total_seconds()),
        )


class RefreshTokensTelegramUseCase:
    def __init__(self, user_repo: UserRepository, refresh_token_repo: RefreshTokenRepository):
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo

    async def __call__(self, request: RefreshTelegramRequest) -> TokenPair:
        # Получаем refresh токен из БД
        exist: RefreshTokenModel = await self._refresh_token_repo.get_one(
            token_hash=request.refresh_token
        )
        if exist is None:
            logger.warning("Refresh token not found: %s", request.refresh_token[:10])
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid refresh token",
            )

        # КРИТИЧЕСКИ ВАЖНО: Проверяем срок действия refresh токена
        # Если не проверять - злоумышленник может использовать старый украденный токен
        now = datetime.now(UTC)

        # Приводим дату из БД к aware UTC, если она naive (для совместимости с SQLite в тестах)
        expires_at = exist.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        if expires_at < now:
            logger.warning(
                "Refresh token expired: token_id=%s, expired_at=%s, now=%s",
                exist.id,
                exist.expires_at,
                now,
            )
            # Удаляем истекший токен из БД для безопасности
            await self._refresh_token_repo.delete(exist.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired. Please log in again.",
            )

        user = await self._user_repo.get_by_telegram_id(request.telegram_id)
        if not user:
            logger.warning("User %s not found", request.telegram_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {request.telegram_id} not found",
            )
        scopes = get_scopes_for_user(user)

        expires_delta = timedelta(days=7)
        access_token = create_access_token(
            telegram_id=request.telegram_id, expires_delta=expires_delta, scopes_permissions=scopes
        )

        new_refresh_token = create_refresh_token()
        new_refresh_expires_at = datetime.now(UTC) + timedelta(days=30)
        await self._refresh_token_repo.update(
            exist.id,
            token_hash=new_refresh_token,
            expires_at=new_refresh_expires_at,
            device_info="telegram",
        )
        return TokenPair(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=int(expires_delta.total_seconds()),
        )
