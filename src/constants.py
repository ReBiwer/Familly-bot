from enum import Enum


class UserTole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"
    CHILD = "child"


class ScopesPermissions(str, Enum):
    USERS_READ = "users:read"
    USERS_WRITE = "users:write"
    USERS_DELETE = "users:delete"
    ADMIN = "admin"
    AI_USE = "ai:use"


ROLE_SCOPES_MAP: dict[UserTole, list[str]] = {
    UserTole.ADMIN: [
        ScopesPermissions.ADMIN.value,
    ],
    UserTole.MEMBER: [
        ScopesPermissions.USERS_READ.value,
        ScopesPermissions.USERS_WRITE.value,
        ScopesPermissions.USERS_DELETE.value,
        ScopesPermissions.AI_USE.value,
    ],
    UserTole.CHILD: [ScopesPermissions.USERS_READ.value, ScopesPermissions.AI_USE.value],
}


DEFAULT_SCOPES: list[str] = ROLE_SCOPES_MAP.get(UserTole.MEMBER)


MEMBER_FAMILLY_SCOPE = [
    ScopesPermissions.USERS_WRITE.value,
    ScopesPermissions.USERS_READ.value,
    ScopesPermissions.AI_USE.value,
]

CHILD_SCOPES = [ScopesPermissions.AI_USE.value]
