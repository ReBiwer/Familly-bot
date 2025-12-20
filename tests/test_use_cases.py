import hashlib
import hmac

import pytest
from fastapi import HTTPException, status

from src.db.repositories import UserRepository, RefreshTokenRepository
from src.schemas import TelegramAuthRequest, TokenPair
from src.use_cases import AuthTelegramUseCase


class TestAuthTelegramUseCase:
    async def test_async_call_use_case(
        self,
        auth_telegram_use_case: AuthTelegramUseCase,
        sample_telegram_auth_request: TelegramAuthRequest,
    ):
        tokens = await auth_telegram_use_case(sample_telegram_auth_request)

        assert tokens is not None
        assert isinstance(tokens, TokenPair)

    async def test_raise_http_exceptions(
        self,
        auth_telegram_use_case: AuthTelegramUseCase,
        sample_telegram_auth_request: TelegramAuthRequest,
    ):
        another_hash_str = hmac.new(
            key=b"kjdsflkjshd90",
            msg=sample_telegram_auth_request.msg.encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()
        sample_telegram_auth_request.hash_str = another_hash_str

        with pytest.raises(HTTPException) as exc_info:
            await auth_telegram_use_case(sample_telegram_auth_request)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_exist_user(
        self,
        auth_telegram_use_case: AuthTelegramUseCase,
        sample_telegram_auth_request: TelegramAuthRequest,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository,
    ):
        await auth_telegram_use_case(sample_telegram_auth_request)
        user = await user_repo.get_by_telegram_id(sample_telegram_auth_request.telegram_id)
        refresh_token = await refresh_token_repo.get_by_user_id(user.id)

        assert refresh_token is not None
        assert user is not None
