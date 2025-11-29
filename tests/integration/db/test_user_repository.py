from src.domain.entities.user import UserEntity
from src.infrastructure.db.repositories.user import UserRepository


async def test_create_user(user_repo: UserRepository, test_user_entity: UserEntity):
    result = await user_repo.create(test_user_entity)
    assert result
    assert isinstance(result, UserEntity)


async def test_duplicate_create_user(user_repo: UserRepository, test_user_entity: UserEntity):
    new_user = await user_repo.create(test_user_entity)
    duple_user = await user_repo.create(test_user_entity)
    assert new_user.id == duple_user.id
    assert new_user.hh_id == duple_user.hh_id


async def test_get_user(user_repo: UserRepository, test_user_entity: UserEntity):
    new_user = await user_repo.create(test_user_entity)
    result = await user_repo.get(id=new_user.id)
    assert result
    assert isinstance(result, UserEntity)


async def test_update_user(user_repo: UserRepository, test_user_entity: UserEntity):
    new_user: UserEntity = await user_repo.create(test_user_entity)
    test_user_entity.id = new_user.id
    test_user_entity.name = "Vladimir"
    test_user_entity.resumes = new_user.resumes
    updated_user: UserEntity = await user_repo.update(test_user_entity)
    assert updated_user
    assert updated_user.name == "Vladimir"
    assert new_user != updated_user


async def test_delete_user(user_repo: UserRepository, test_user_entity: UserEntity):
    user = await user_repo.create(test_user_entity)
    await user_repo.delete(user.id)
    check = await user_repo.get(id=user.id)
    assert check is None
