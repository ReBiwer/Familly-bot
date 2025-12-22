from enum import Enum


class ScopesPermissions(str, Enum):
    USERS_READ = "users:read"
    USERS_WRITE = "users:write"
    USERS_DELETE = "users:delete"
    ADMIN = "admin"
    AI_USE = "ai:use"

DEFAULT_SCOPES: list[str] = [
    ScopesPermissions.USERS_WRITE.value,
    ScopesPermissions.USERS_READ.value,
    ScopesPermissions.USERS_DELETE.value,
]

MEMBER_FAMILLY_SCOPE = [
    ScopesPermissions.USERS_WRITE.value,
    ScopesPermissions.USERS_READ.value,
    ScopesPermissions.AI_USE.value,
]

CHILD_SCOPES = [
    ScopesPermissions.AI_USE.value
]
