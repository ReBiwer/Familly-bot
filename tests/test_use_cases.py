import hashlib
import hmac
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException, status

from src.constants import ROLE_SCOPES_MAP, ScopesPermissions, UserRole
from src.db.models import RefreshTokenModel, UserModel
from src.db.repositories import RefreshTokenRepository, UserRepository
from src.schemas import RefreshTelegramRequest, TelegramAuthRequest, TokenPair
from src.use_cases import AuthTelegramUseCase, RefreshTokensTelegramUseCase
from src.utils import verify_token


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


# =============================================================================
# Тесты для проверки scopes в токенах
# =============================================================================


class TestAuthTelegramUseCaseWithScopes:
    """
    Тесты проверяют что токены создаются с правильными scopes
    в зависимости от роли пользователя.
    """

    async def test_auth_creates_token_with_member_scopes_for_new_user(
        self,
        auth_telegram_use_case: AuthTelegramUseCase,
        sample_telegram_auth_request: TelegramAuthRequest,
    ):
        """
        Новый пользователь получает токен со scopes для роли member.

        По умолчанию новые пользователи создаются с ролью 'member'.
        """
        # Act
        tokens = await auth_telegram_use_case(sample_telegram_auth_request)

        # Assert: декодируем токен и проверяем scopes
        payload = verify_token(tokens.access_token)
        assert payload is not None
        assert payload.scopes == ROLE_SCOPES_MAP[UserRole.MEMBER]

    async def test_auth_creates_token_with_admin_scopes(
        self,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository,
        sample_telegram_auth_request: TelegramAuthRequest,
    ):
        """
        Пользователь с ролью admin получает токен с admin scope.
        """
        # Arrange: создаём пользователя с ролью admin
        await user_repo.create(
            name=sample_telegram_auth_request.first_name,
            mid_name=sample_telegram_auth_request.mid_name,
            last_name=sample_telegram_auth_request.last_name,
            telegram_id=sample_telegram_auth_request.telegram_id,
            role="admin",
        )

        auth_use_case = AuthTelegramUseCase(user_repo, refresh_token_repo)

        # Act
        tokens = await auth_use_case(sample_telegram_auth_request)

        # Assert
        payload = verify_token(tokens.access_token)
        assert payload is not None
        assert payload.scopes == ROLE_SCOPES_MAP[UserRole.ADMIN]
        assert ScopesPermissions.ADMIN.value in payload.scopes

    async def test_auth_creates_token_with_child_scopes(
        self,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository,
        sample_telegram_auth_request: TelegramAuthRequest,
    ):
        """
        Пользователь с ролью child получает ограниченный набор scopes.
        """
        # Arrange: создаём пользователя с ролью child
        await user_repo.create(
            name=sample_telegram_auth_request.first_name,
            mid_name=sample_telegram_auth_request.mid_name,
            last_name=sample_telegram_auth_request.last_name,
            telegram_id=sample_telegram_auth_request.telegram_id,
            role="child",
        )

        auth_use_case = AuthTelegramUseCase(user_repo, refresh_token_repo)

        # Act
        tokens = await auth_use_case(sample_telegram_auth_request)

        # Assert
        payload = verify_token(tokens.access_token)
        assert payload is not None
        assert payload.scopes == ROLE_SCOPES_MAP[UserRole.CHILD]
        # У child не должно быть прав на удаление
        assert ScopesPermissions.USERS_DELETE.value not in payload.scopes
        assert ScopesPermissions.ADMIN.value not in payload.scopes


class TestRefreshTokensUseCaseWithScopes:
    """
    Тесты проверяют что при refresh токена scopes обновляются
    в соответствии с текущей ролью пользователя.
    """

    async def test_refresh_tokens_updates_scopes_if_role_changed(
        self,
        refresh_tokens_use_case: RefreshTokensTelegramUseCase,
        sample_user: UserModel,
        user_repo: UserRepository,
        refresh_token_in_db_factory: Callable[..., Awaitable[tuple[str, RefreshTokenModel]]],
    ):
        """
        Если роль пользователя изменилась, новый токен содержит обновлённые scopes.

        Сценарий:
        1. Пользователь авторизовался с ролью 'member'
        2. Админ изменил его роль на 'admin'
        3. Пользователь делает refresh токена
        4. Новый токен содержит admin scopes
        """
        # Arrange: создаём refresh_token
        old_token_hash, _ = await refresh_token_in_db_factory()

        # Изменяем роль пользователя на admin
        await user_repo.update(sample_user.id, role="admin")

        request = RefreshTelegramRequest(
            telegram_id=sample_user.telegram_id,
            refresh_token=old_token_hash,
        )

        # Act: обновляем токены
        tokens = await refresh_tokens_use_case(request)

        # Assert: новый токен содержит admin scopes
        payload = verify_token(tokens.access_token)
        assert payload is not None
        assert payload.scopes == ROLE_SCOPES_MAP[UserRole.ADMIN]
        assert ScopesPermissions.ADMIN.value in payload.scopes

    async def test_refresh_tokens_preserves_scopes_if_role_unchanged(
        self,
        refresh_tokens_use_case: RefreshTokensTelegramUseCase,
        sample_user: UserModel,
        refresh_token_in_db_factory: Callable[..., Awaitable[tuple[str, RefreshTokenModel]]],
    ):
        """
        Если роль не изменилась, scopes остаются прежними.
        """
        # Arrange
        old_token_hash, _ = await refresh_token_in_db_factory()

        request = RefreshTelegramRequest(
            telegram_id=sample_user.telegram_id,
            refresh_token=old_token_hash,
        )

        # Act
        tokens = await refresh_tokens_use_case(request)

        # Assert: scopes соответствуют роли member (из sample_user)
        payload = verify_token(tokens.access_token)
        assert payload is not None
        assert payload.scopes == ROLE_SCOPES_MAP[UserRole.MEMBER]

    async def test_refresh_tokens_downgrades_scopes_if_role_downgraded(
        self,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository,
        refresh_token_in_db_factory: Callable[..., Awaitable[tuple[str, RefreshTokenModel]]],
    ):
        """
        Если роль понижена (admin → child), scopes тоже понижаются.

        Это важно для безопасности - отозвать права можно через смену роли.
        """
        # Arrange: создаём админа
        admin_user = await user_repo.create(
            name="Админ",
            mid_name="Временный",
            last_name="Админов",
            telegram_id=999999,
            role="admin",
        )

        # Создаём refresh_token для админа
        old_token_hash = "test_refresh_token_admin"
        await refresh_token_repo.create(
            token_hash=old_token_hash,
            user_id=admin_user.id,
            expires_at=datetime.now(UTC) + timedelta(days=30),
            device_info="test",
        )

        # Понижаем роль до child
        await user_repo.update(admin_user.id, role="child")

        refresh_use_case = RefreshTokensTelegramUseCase(user_repo, refresh_token_repo)
        request = RefreshTelegramRequest(
            telegram_id=admin_user.telegram_id,
            refresh_token=old_token_hash,
        )

        # Act
        tokens = await refresh_use_case(request)

        # Assert: теперь у него child scopes (без admin)
        payload = verify_token(tokens.access_token)
        assert payload is not None
        assert payload.scopes == ROLE_SCOPES_MAP[UserRole.CHILD]
        assert ScopesPermissions.ADMIN.value not in payload.scopes
