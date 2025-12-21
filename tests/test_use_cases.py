import hashlib
import hmac
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException, status

from src.db.models import RefreshTokenModel, UserModel
from src.db.repositories import RefreshTokenRepository, UserRepository
from src.schemas import RefreshTelegramRequest, TelegramAuthRequest, TokenPair
from src.use_cases import AuthTelegramUseCase, RefreshTokensTelegramUseCase


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


class TestRefreshTokensTelegramUseCase:
    """
    Тесты для RefreshTokensTelegramUseCase.

    Use case обновляет пару токенов:
    - Проверяет существование refresh_token в БД
    - Генерирует новый access_token
    - Обновляет refresh_token в БД
    - Возвращает новую пару токенов
    """

    async def test_refresh_tokens_success(
        self,
        refresh_tokens_use_case: RefreshTokensTelegramUseCase,
        sample_user: UserModel,
        refresh_token_in_db_factory: Callable[..., Awaitable[tuple[str, RefreshTokenModel]]],
    ):
        """
        Успешное обновление токенов.

        Сценарий:
        1. Создаём refresh_token в БД для пользователя
        2. Вызываем use case с этим токеном
        3. Получаем новую пару токенов
        """
        # Arrange
        old_token_hash, _ = await refresh_token_in_db_factory()

        request = RefreshTelegramRequest(
            telegram_id=sample_user.telegram_id,
            refresh_token=old_token_hash,
        )

        # Act
        tokens = await refresh_tokens_use_case(request)

        # Assert
        assert tokens is not None
        assert isinstance(tokens, TokenPair)
        assert len(tokens.access_token) > 0
        assert len(tokens.refresh_token) > 0
        # Новый refresh_token должен отличаться от старого
        assert tokens.refresh_token != old_token_hash

    async def test_refresh_tokens_updates_db(
        self,
        refresh_tokens_use_case: RefreshTokensTelegramUseCase,
        sample_user: UserModel,
        refresh_token_repo: RefreshTokenRepository,
        refresh_token_in_db_factory: Callable[..., Awaitable[tuple[str, RefreshTokenModel]]],
    ):
        """
        Проверяем, что токен обновляется в БД.

        После вызова use case:
        - Старый token_hash больше не существует
        - Новый token_hash записан в ту же запись
        """
        # Arrange
        old_token_hash, token_record = await refresh_token_in_db_factory()
        original_id = token_record.id

        request = RefreshTelegramRequest(
            telegram_id=sample_user.telegram_id,
            refresh_token=old_token_hash,
        )

        # Act
        tokens = await refresh_tokens_use_case(request)

        # Assert: старый токен не найден
        old_token_in_db = await refresh_token_repo.get_one(token_hash=old_token_hash)
        assert old_token_in_db is None

        # Assert: новый токен записан
        new_token_in_db = await refresh_token_repo.get_one(token_hash=tokens.refresh_token)
        assert new_token_in_db is not None
        # Это та же запись (обновление, не создание новой)
        assert new_token_in_db.id == original_id

    async def test_refresh_tokens_not_found(
        self,
        refresh_tokens_use_case: RefreshTokensTelegramUseCase,
        sample_user: UserModel,
    ):
        """
        Если refresh_token не найден в БД — возвращаем 404.

        Это может произойти если:
        - Токен никогда не существовал
        - Токен был отозван (удалён)
        - Токен уже был использован и заменён на новый
        """
        request = RefreshTelegramRequest(
            telegram_id=sample_user.telegram_id,
            refresh_token="nonexistent_token_that_does_not_exist",
        )

        with pytest.raises(HTTPException) as exc_info:
            await refresh_tokens_use_case(request)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    async def test_refresh_tokens_returns_valid_expires_in(
        self,
        refresh_tokens_use_case: RefreshTokensTelegramUseCase,
        sample_user: UserModel,
        refresh_token_in_db_factory: Callable[..., Awaitable[tuple[str, RefreshTokenModel]]],
    ):
        """
        Проверяем, что expires_in соответствует ожидаемому значению.

        expires_in должен быть равен 7 дней в секундах.
        """
        # Arrange
        old_token_hash, _ = await refresh_token_in_db_factory()

        request = RefreshTelegramRequest(
            telegram_id=sample_user.telegram_id,
            refresh_token=old_token_hash,
        )

        # Act
        tokens = await refresh_tokens_use_case(request)

        # Assert: 7 дней = 604800 секунд
        expected_expires_in = int(timedelta(days=7).total_seconds())
        assert tokens.expires_in == expected_expires_in

    async def test_refresh_tokens_extends_expiration(
        self,
        refresh_tokens_use_case: RefreshTokensTelegramUseCase,
        sample_user: UserModel,
        refresh_token_repo: RefreshTokenRepository,
        refresh_token_in_db_factory: Callable[..., Awaitable[tuple[str, RefreshTokenModel]]],
    ):
        """
        Проверяем, что срок действия токена продлевается.

        При обновлении expires_at должен сдвинуться на +30 дней от текущего момента.
        """
        # Arrange: создаём токен с коротким сроком (например, истекает через 1 день)
        old_expires_at = datetime.now(UTC) + timedelta(days=1)
        old_token_hash, _ = await refresh_token_in_db_factory(expires_at=old_expires_at)

        request = RefreshTelegramRequest(
            telegram_id=sample_user.telegram_id,
            refresh_token=old_token_hash,
        )

        # Act
        tokens = await refresh_tokens_use_case(request)

        # Assert: новый срок больше старого (продлён)
        new_token_in_db = await refresh_token_repo.get_one(token_hash=tokens.refresh_token)
        # SQLite может вернуть naive или aware datetime в зависимости от драйвера
        # Приводим оба к naive для безопасного сравнения
        new_expires = new_token_in_db.expires_at
        if new_expires.tzinfo is not None:
            new_expires = new_expires.replace(tzinfo=None)
        old_expires = old_expires_at.replace(tzinfo=None)
        assert new_expires > old_expires
