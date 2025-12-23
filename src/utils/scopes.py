import logging

from src.constants import DEFAULT_SCOPES, ROLE_SCOPES_MAP, UserRole
from src.db.models import UserModel

logger = logging.getLogger(__name__)


def get_scopes_for_user(user: UserModel) -> list[str]:
    """
    Определяет список scopes для пользователя на основе его роли из БД.

    Args:
        user: Модель пользователя из БД

    Returns:
        Список scopes (строки)
    """
    try:
        role = UserRole(user.role)
        scopes = ROLE_SCOPES_MAP.get(role, DEFAULT_SCOPES).copy()

        logger.info(f"User {user.telegram_id} (role={role.value}) assigned scopes: {scopes}")
        return scopes
    except ValueError:
        logger.warning(
            f"Unknown role '{user.role}' for user {user.telegram_id}. Using default scopes."
        )
        return DEFAULT_SCOPES.copy()


def get_scopes_for_role(role: UserRole | str) -> list[str]:
    """
    Получает scopes для конкретной роли.

    Args:
        role: Роль (enum UserRole или строка)

    Returns:
        Список scopes для этой роли
    """
    if isinstance(role, str):
        try:
            role = UserRole(role)
        except ValueError:
            return DEFAULT_SCOPES.copy()

    return ROLE_SCOPES_MAP.get(role, DEFAULT_SCOPES).copy()
