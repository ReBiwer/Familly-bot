from abc import ABC

from src.application.repositories.base import ISQLRepository
from src.domain.entities.user import UserEntity


class IUserRepository[ET: UserEntity](ISQLRepository[UserEntity], ABC): ...
