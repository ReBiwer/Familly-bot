from sqlalchemy import select
from src.application.repositories.user import IUserRepository
from src.domain.entities.user import UserEntity
from src.infrastructure.db.models.user import UserModel
from src.infrastructure.db.repositories.base import SQLAlchemyRepository


class UserRepository[ET: UserEntity, DBModel: UserModel](SQLAlchemyRepository, IUserRepository):
    model_class = UserModel
    entity_class = UserEntity

    async def _check_exist_entity(self, data: ET) -> DBModel | None:
        entity_hh_id = getattr(data, "hh_id", None)
        if entity_hh_id is None:
            return None

        exists_stmt = select(self.model_class).where(self.model_class.hh_id == data.hh_id)
        result = await self.session.scalar(exists_stmt)
        return result
