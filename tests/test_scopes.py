"""
Тесты для функций работы со scopes и ролями пользователей.

Проверяем:
- get_scopes_for_user() - определение scopes по пользователю из БД
- get_scopes_for_role() - определение scopes по роли (enum или строка)
"""

from src.constants import DEFAULT_SCOPES, ROLE_SCOPES_MAP, ScopesPermissions, UserRole
from src.utils import get_scopes_for_role, get_scopes_for_user

# =============================================================================
# Тесты get_scopes_for_user() - работа с пользователями из БД
# =============================================================================


async def test_get_scopes_for_user_admin(user_factory):
    """Администратор получает scope 'admin'."""
    admin_user = await user_factory(
        name="Админ",
        mid_name="Админович",
        last_name="Админов",
        telegram_id=100500,
        role="admin",
    )

    scopes = get_scopes_for_user(admin_user)

    assert scopes == ROLE_SCOPES_MAP[UserRole.ADMIN]
    assert ScopesPermissions.ADMIN.value in scopes


async def test_get_scopes_for_user_member(user_factory):
    """Обычный член семьи получает полный набор прав кроме admin."""
    member_user = await user_factory(
        name="Член",
        mid_name="Семьи",
        last_name="Обычный",
        telegram_id=100501,
        role="member",
    )

    scopes = get_scopes_for_user(member_user)

    assert scopes == ROLE_SCOPES_MAP[UserRole.MEMBER]
    assert ScopesPermissions.USERS_READ.value in scopes
    assert ScopesPermissions.USERS_WRITE.value in scopes
    assert ScopesPermissions.USERS_DELETE.value in scopes
    assert ScopesPermissions.AI_USE.value in scopes
    # Проверяем что админского scope нет
    assert ScopesPermissions.ADMIN.value not in scopes


async def test_get_scopes_for_user_child(user_factory):
    """Ребёнок получает ограниченный набор прав."""
    child_user = await user_factory(
        name="Ребёнок",
        mid_name="Маленький",
        last_name="Юный",
        telegram_id=100502,
        role="child",
    )

    scopes = get_scopes_for_user(child_user)

    assert scopes == ROLE_SCOPES_MAP[UserRole.CHILD]
    assert ScopesPermissions.USERS_READ.value in scopes
    assert ScopesPermissions.AI_USE.value in scopes
    # Проверяем что прав на изменение/удаление нет
    assert ScopesPermissions.USERS_WRITE.value not in scopes
    assert ScopesPermissions.USERS_DELETE.value not in scopes
    assert ScopesPermissions.ADMIN.value not in scopes


async def test_get_scopes_for_user_unknown_role(user_factory):
    """При неизвестной роли возвращаются DEFAULT_SCOPES."""
    unknown_user = await user_factory(
        name="Неизвестный",
        mid_name="Неизвестнович",
        last_name="Неизвестнов",
        telegram_id=100503,
        role="moderator",  # Несуществующая роль
    )

    scopes = get_scopes_for_user(unknown_user)

    assert scopes == DEFAULT_SCOPES


# =============================================================================
# Тесты get_scopes_for_role() - работа напрямую с ролями
# =============================================================================


def test_get_scopes_for_role_admin_enum():
    """Получение scopes для админа по enum."""
    scopes = get_scopes_for_role(UserRole.ADMIN)

    assert scopes == ROLE_SCOPES_MAP[UserRole.ADMIN]
    assert ScopesPermissions.ADMIN.value in scopes


def test_get_scopes_for_role_member_enum():
    """Получение scopes для member по enum."""
    scopes = get_scopes_for_role(UserRole.MEMBER)

    assert scopes == ROLE_SCOPES_MAP[UserRole.MEMBER]
    assert ScopesPermissions.USERS_READ.value in scopes
    assert ScopesPermissions.USERS_WRITE.value in scopes
    assert ScopesPermissions.USERS_DELETE.value in scopes
    assert ScopesPermissions.AI_USE.value in scopes
    assert ScopesPermissions.ADMIN.value not in scopes


def test_get_scopes_for_role_child_enum():
    """Получение scopes для child по enum."""
    scopes = get_scopes_for_role(UserRole.CHILD)

    assert scopes == ROLE_SCOPES_MAP[UserRole.CHILD]
    assert ScopesPermissions.USERS_READ.value in scopes
    assert ScopesPermissions.AI_USE.value in scopes
    assert ScopesPermissions.USERS_WRITE.value not in scopes
    assert ScopesPermissions.ADMIN.value not in scopes


def test_get_scopes_for_role_admin_string():
    """Получение scopes для админа по строке."""
    scopes = get_scopes_for_role("admin")

    assert scopes == ROLE_SCOPES_MAP[UserRole.ADMIN]
    assert ScopesPermissions.ADMIN.value in scopes


def test_get_scopes_for_role_member_string():
    """Получение scopes для member по строке."""
    scopes = get_scopes_for_role("member")

    assert scopes == ROLE_SCOPES_MAP[UserRole.MEMBER]


def test_get_scopes_for_role_child_string():
    """Получение scopes для child по строке."""
    scopes = get_scopes_for_role("child")

    assert scopes == ROLE_SCOPES_MAP[UserRole.CHILD]


def test_get_scopes_for_role_unknown_string():
    """При неизвестной строковой роли возвращаются DEFAULT_SCOPES."""
    scopes = get_scopes_for_role("moderator")

    assert scopes == DEFAULT_SCOPES


# =============================================================================
# Тесты иммутабельности (что возвращаются копии)
# =============================================================================


def test_get_scopes_for_role_returns_copy():
    """
    Функция get_scopes_for_role возвращает копию списка, а не ссылку.

    Это важно чтобы изменение результата не влияло на исходные данные в ROLE_SCOPES_MAP.
    """
    scopes1 = get_scopes_for_role(UserRole.MEMBER)
    scopes2 = get_scopes_for_role(UserRole.MEMBER)

    # Должны быть равны по значению
    assert scopes1 == scopes2

    # Но это разные объекты (копии)
    assert scopes1 is not scopes2

    # Изменение одного не влияет на другой
    scopes1.append("test:scope")
    assert "test:scope" not in scopes2
    # И не влияет на исходные данные
    assert "test:scope" not in ROLE_SCOPES_MAP[UserRole.MEMBER]


async def test_get_scopes_for_user_returns_copy(user_factory):
    """
    Функция get_scopes_for_user возвращает копию списка, а не ссылку.
    """
    user = await user_factory(telegram_id=999999, role="member")

    scopes1 = get_scopes_for_user(user)
    scopes2 = get_scopes_for_user(user)

    # Должны быть равны
    assert scopes1 == scopes2

    # Но это разные объекты
    assert scopes1 is not scopes2

    # Изменение одного не влияет на другой
    scopes1.append("test:scope")
    assert "test:scope" not in scopes2
    assert "test:scope" not in ROLE_SCOPES_MAP[UserRole.MEMBER]
