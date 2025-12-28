"""
Тесты для FastAPI dependencies с проверкой OAuth2 scopes.

Проверяем:
- get_current_telegram_id() корректно проверяет scopes
- Админ может обходить проверки scopes
- Пользователи без нужных scopes получают 403
- Невалидные токены получают 401
"""

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, SecurityScopes

from src.constants import ScopesPermissions
from src.di.dependencies import get_current_telegram_id
from src.utils import create_access_token

# =============================================================================
# Тесты успешной авторизации
# =============================================================================


async def test_get_current_telegram_id_no_scopes_required():
    """
    Эндпоинт без требований к scopes - любой авторизованный пользователь проходит.
    """
    telegram_id = 123456
    token = create_access_token(
        telegram_id=telegram_id,
        scopes_permissions=[ScopesPermissions.USERS_READ.value],
    )

    # SecurityScopes без требуемых scopes (пустой список)
    security_scopes = SecurityScopes()
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    result = await get_current_telegram_id(security_scopes, credentials)

    assert result == telegram_id


async def test_get_current_telegram_id_with_matching_scope():
    """
    Пользователь с нужным scope проходит проверку.
    """
    telegram_id = 123456
    token = create_access_token(
        telegram_id=telegram_id,
        scopes_permissions=[
            ScopesPermissions.USERS_READ.value,
            ScopesPermissions.AI_USE.value,
        ],
    )

    # Требуется scope users:read - он есть в токене
    security_scopes = SecurityScopes(scopes=[ScopesPermissions.USERS_READ.value])
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    result = await get_current_telegram_id(security_scopes, credentials)

    assert result == telegram_id


async def test_get_current_telegram_id_with_multiple_matching_scopes():
    """
    Пользователь со всеми требуемыми scopes проходит проверку.
    """
    telegram_id = 123456
    token = create_access_token(
        telegram_id=telegram_id,
        scopes_permissions=[
            ScopesPermissions.USERS_READ.value,
            ScopesPermissions.USERS_WRITE.value,
            ScopesPermissions.AI_USE.value,
        ],
    )

    # Требуются два scope - оба есть
    security_scopes = SecurityScopes(
        scopes=[
            ScopesPermissions.USERS_READ.value,
            ScopesPermissions.USERS_WRITE.value,
        ]
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    result = await get_current_telegram_id(security_scopes, credentials)

    assert result == telegram_id


# =============================================================================
# Тесты админского bypass
# =============================================================================


async def test_get_current_telegram_id_admin_bypass_all_checks():
    """
    Админ с scope 'admin' проходит любые проверки scopes.
    """
    telegram_id = 999999
    token = create_access_token(
        telegram_id=telegram_id,
        scopes_permissions=[ScopesPermissions.ADMIN.value],
    )

    # Требуется scope которого у админа НЕТ явно
    security_scopes = SecurityScopes(scopes=[ScopesPermissions.USERS_DELETE.value])
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    result = await get_current_telegram_id(security_scopes, credentials)

    # Админ проходит несмотря на отсутствие users:delete
    assert result == telegram_id


async def test_get_current_telegram_id_admin_with_multiple_required_scopes():
    """
    Админ проходит даже если требуется несколько scopes.
    """
    telegram_id = 999999
    token = create_access_token(
        telegram_id=telegram_id,
        scopes_permissions=[ScopesPermissions.ADMIN.value],
    )

    # Требуются много scopes
    security_scopes = SecurityScopes(
        scopes=[
            ScopesPermissions.USERS_READ.value,
            ScopesPermissions.USERS_WRITE.value,
            ScopesPermissions.USERS_DELETE.value,
            ScopesPermissions.AI_USE.value,
        ]
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    result = await get_current_telegram_id(security_scopes, credentials)

    assert result == telegram_id


# =============================================================================
# Тесты отказа в доступе (403)
# =============================================================================


async def test_get_current_telegram_id_missing_required_scope():
    """
    Пользователь без нужного scope получает 403.
    """
    telegram_id = 123456
    token = create_access_token(
        telegram_id=telegram_id,
        scopes_permissions=[ScopesPermissions.USERS_READ.value],  # Только read
    )

    # Требуется write - его нет
    security_scopes = SecurityScopes(scopes=[ScopesPermissions.USERS_WRITE.value])
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_telegram_id(security_scopes, credentials)

    assert exc_info.value.status_code == 403
    assert "Not enough permissions" in exc_info.value.detail


async def test_get_current_telegram_id_missing_one_of_multiple_scopes():
    """
    Пользователь без одного из требуемых scopes получает 403.
    """
    telegram_id = 123456
    token = create_access_token(
        telegram_id=telegram_id,
        scopes_permissions=[
            ScopesPermissions.USERS_READ.value,
            # Нет USERS_WRITE
        ],
    )

    # Требуются оба scope - одного нет
    security_scopes = SecurityScopes(
        scopes=[
            ScopesPermissions.USERS_READ.value,
            ScopesPermissions.USERS_WRITE.value,
        ]
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_telegram_id(security_scopes, credentials)

    assert exc_info.value.status_code == 403


async def test_get_current_telegram_id_empty_scopes_but_required():
    """
    Пользователь без scopes не может получить доступ к защищённым эндпоинтам.
    """
    telegram_id = 123456
    token = create_access_token(
        telegram_id=telegram_id,
        scopes_permissions=[],  # Пустой список
    )

    # Требуется хотя бы один scope
    security_scopes = SecurityScopes(scopes=[ScopesPermissions.USERS_READ.value])
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_telegram_id(security_scopes, credentials)

    assert exc_info.value.status_code == 403


# =============================================================================
# Тесты невалидных токенов (401)
# =============================================================================


async def test_get_current_telegram_id_invalid_token():
    """
    Невалидный токен возвращает 401.
    """
    security_scopes = SecurityScopes()
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.token.here")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_telegram_id(security_scopes, credentials)

    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in exc_info.value.detail


async def test_get_current_telegram_id_malformed_token():
    """
    Неправильно сформированный токен возвращает 401.
    """
    security_scopes = SecurityScopes()
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not-a-jwt")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_telegram_id(security_scopes, credentials)

    assert exc_info.value.status_code == 401


async def test_get_current_telegram_id_expired_token():
    """
    Истёкший токен возвращает 401.
    """
    from datetime import timedelta

    telegram_id = 123456
    # Создаём токен который уже истёк (отрицательное время)
    token = create_access_token(
        telegram_id=telegram_id,
        expires_delta=timedelta(seconds=-1),
        scopes_permissions=[ScopesPermissions.USERS_READ.value],
    )

    security_scopes = SecurityScopes()
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_telegram_id(security_scopes, credentials)

    assert exc_info.value.status_code == 401


# =============================================================================
# Тесты WWW-Authenticate заголовка
# =============================================================================


async def test_get_current_telegram_id_401_includes_www_authenticate():
    """
    401 ошибка включает заголовок WWW-Authenticate.
    """
    security_scopes = SecurityScopes(scopes=[ScopesPermissions.USERS_READ.value])
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.token")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_telegram_id(security_scopes, credentials)

    assert exc_info.value.status_code == 401
    assert "WWW-Authenticate" in exc_info.value.headers
    assert "Bearer" in exc_info.value.headers["WWW-Authenticate"]


async def test_get_current_telegram_id_403_includes_www_authenticate():
    """
    403 ошибка включает заголовок WWW-Authenticate с требуемыми scopes.
    """
    telegram_id = 123456
    token = create_access_token(
        telegram_id=telegram_id,
        scopes_permissions=[ScopesPermissions.USERS_READ.value],
    )

    security_scopes = SecurityScopes(scopes=[ScopesPermissions.USERS_DELETE.value])
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_telegram_id(security_scopes, credentials)

    assert exc_info.value.status_code == 403
    assert "WWW-Authenticate" in exc_info.value.headers
    assert "Bearer" in exc_info.value.headers["WWW-Authenticate"]
    # Должны быть указаны требуемые scopes
    assert "users:delete" in exc_info.value.headers["WWW-Authenticate"]
