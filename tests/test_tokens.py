"""
Тесты для работы с JWT токенами и scopes.

Проверяем:
- create_access_token() создаёт токены с правильными scopes
- verify_token() корректно парсит scopes из токена
- TokenPayload схема валидирует scopes
"""

from datetime import timedelta

import pytest
from jose import jwt

from src.constants import DEFAULT_SCOPES, ScopesPermissions
from src.schemas import TokenPayload
from src.settings import app_settings
from src.utils import TokenInvalidException, create_access_token, verify_token

# =============================================================================
# Тесты create_access_token()
# =============================================================================


def test_create_access_token_with_custom_scopes():
    """Создание токена с явно указанными scopes."""
    telegram_id = 123456
    custom_scopes = [ScopesPermissions.ADMIN.value]

    token = create_access_token(
        telegram_id=telegram_id,
        scopes_permissions=custom_scopes,
    )

    # Декодируем токен и проверяем payload
    payload = jwt.decode(
        token,
        app_settings.AUTH.JWT_TOKEN,
        algorithms=[app_settings.AUTH.JWT_ALG],
    )

    assert payload["sub"] == str(telegram_id)
    assert payload["scopes"] == custom_scopes
    assert ScopesPermissions.ADMIN.value in payload["scopes"]


def test_create_access_token_with_default_scopes():
    """Создание токена без явных scopes использует DEFAULT_SCOPES."""
    telegram_id = 123456

    token = create_access_token(telegram_id=telegram_id)

    payload = jwt.decode(
        token,
        app_settings.AUTH.JWT_TOKEN,
        algorithms=[app_settings.AUTH.JWT_ALG],
    )

    assert payload["sub"] == str(telegram_id)
    assert payload["scopes"] == DEFAULT_SCOPES


def test_create_access_token_with_multiple_scopes():
    """Создание токена с несколькими scopes."""
    telegram_id = 123456
    multiple_scopes = [
        ScopesPermissions.USERS_READ.value,
        ScopesPermissions.USERS_WRITE.value,
        ScopesPermissions.AI_USE.value,
    ]

    token = create_access_token(
        telegram_id=telegram_id,
        scopes_permissions=multiple_scopes,
    )

    payload = jwt.decode(
        token,
        app_settings.AUTH.JWT_TOKEN,
        algorithms=[app_settings.AUTH.JWT_ALG],
    )

    assert payload["scopes"] == multiple_scopes
    assert len(payload["scopes"]) == 3


def test_create_access_token_with_empty_scopes():
    """Создание токена с пустым списком scopes."""
    telegram_id = 123456
    empty_scopes = []

    token = create_access_token(
        telegram_id=telegram_id,
        scopes_permissions=empty_scopes,
    )

    payload = jwt.decode(
        token,
        app_settings.AUTH.JWT_TOKEN,
        algorithms=[app_settings.AUTH.JWT_ALG],
    )

    assert payload["scopes"] == []


def test_create_access_token_custom_expiration():
    """Создание токена с кастомным временем жизни."""
    telegram_id = 123456
    custom_delta = timedelta(hours=1)

    token = create_access_token(
        telegram_id=telegram_id,
        expires_delta=custom_delta,
        scopes_permissions=[ScopesPermissions.USERS_READ.value],
    )

    # Проверяем что токен создан
    assert len(token) > 0

    # Проверяем что можем декодировать
    payload = jwt.decode(
        token,
        app_settings.AUTH.JWT_TOKEN,
        algorithms=[app_settings.AUTH.JWT_ALG],
    )
    assert "exp" in payload
    assert payload["scopes"] == [ScopesPermissions.USERS_READ.value]


# =============================================================================
# Тесты verify_token()
# =============================================================================


def test_verify_token_includes_scopes():
    """verify_token корректно извлекает scopes из токена."""
    telegram_id = 123456
    test_scopes = [
        ScopesPermissions.USERS_READ.value,
        ScopesPermissions.AI_USE.value,
    ]

    token = create_access_token(
        telegram_id=telegram_id,
        scopes_permissions=test_scopes,
    )

    payload = verify_token(token)

    assert payload is not None
    assert payload.sub == str(telegram_id)
    assert payload.scopes == test_scopes


def test_verify_token_admin_scope():
    """verify_token корректно извлекает admin scope."""
    telegram_id = 999999
    admin_scopes = [ScopesPermissions.ADMIN.value]

    token = create_access_token(
        telegram_id=telegram_id,
        scopes_permissions=admin_scopes,
    )

    payload = verify_token(token)

    assert payload is not None
    assert ScopesPermissions.ADMIN.value in payload.scopes


def test_verify_token_invalid_returns_none():
    """verify_token возвращает None для невалидного токена."""
    invalid_token = "this.is.invalid"

    with pytest.raises(TokenInvalidException) as exc_info:
        verify_token(invalid_token)

    assert exc_info.value.status_code == 401
    assert "Invalid token" in exc_info.value.detail


def test_verify_token_empty_scopes():
    """verify_token корректно обрабатывает пустой список scopes."""
    telegram_id = 123456

    token = create_access_token(
        telegram_id=telegram_id,
        scopes_permissions=[],
    )

    payload = verify_token(token)

    assert payload is not None
    assert payload.scopes == []


# =============================================================================
# Тесты TokenPayload схемы
# =============================================================================


def test_token_payload_schema_with_scopes():
    """TokenPayload корректно валидирует данные с scopes."""
    from datetime import UTC, datetime

    payload_data = {
        "sub": "123456",
        "exp": datetime.now(UTC),
        "scopes": [ScopesPermissions.USERS_READ.value, ScopesPermissions.AI_USE.value],
    }

    payload = TokenPayload(**payload_data)

    assert payload.sub == "123456"
    assert len(payload.scopes) == 2
    assert ScopesPermissions.USERS_READ.value in payload.scopes


def test_token_payload_schema_empty_scopes():
    """TokenPayload корректно валидирует пустой список scopes."""
    from datetime import UTC, datetime

    payload_data = {
        "sub": "123456",
        "exp": datetime.now(UTC),
        "scopes": [],
    }

    payload = TokenPayload(**payload_data)

    assert payload.scopes == []


def test_token_payload_schema_admin_scope():
    """TokenPayload корректно валидирует admin scope."""
    from datetime import UTC, datetime

    payload_data = {
        "sub": "999999",
        "exp": datetime.now(UTC),
        "scopes": [ScopesPermissions.ADMIN.value],
    }

    payload = TokenPayload(**payload_data)

    assert ScopesPermissions.ADMIN.value in payload.scopes


# =============================================================================
# Тесты иммутабельности
# =============================================================================


def test_token_scopes_not_mutated():
    """
    Изменение scopes после создания токена не влияет на токен.

    Это проверяет что create_access_token делает копию списка scopes.
    """
    telegram_id = 123456
    original_scopes = [ScopesPermissions.USERS_READ.value]

    token = create_access_token(
        telegram_id=telegram_id,
        scopes_permissions=original_scopes,
    )

    # Мутируем исходный список
    original_scopes.append(ScopesPermissions.ADMIN.value)

    # Проверяем что токен не изменился
    payload = verify_token(token)
    assert payload.scopes == [ScopesPermissions.USERS_READ.value]
    assert ScopesPermissions.ADMIN.value not in payload.scopes
