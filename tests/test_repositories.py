"""
Тесты для репозиториев.

Используют in-memory SQLite для изоляции тестов.
Фикстуры (user_repo, sample_user, user_factory и др.) определены в conftest.py.
"""

from datetime import datetime, timedelta

from src.db.models import UserModel
from src.db.repositories import UserRepository
from src.utils import create_refresh_token


class TestUserRepository:
    """
    Тесты для UserRepository.

    Используемые фикстуры:
    - user_repo: экземпляр UserRepository
    - sample_user: готовый пользователь для тестов чтения/обновления/удаления
    - user_factory: фабрика для создания пользователей с кастомными данными
    """

    async def test_create_user(self, user_repo: UserRepository):
        """
        Создание пользователя.

        Не используем sample_user — тест проверяет именно создание.
        """
        user = await user_repo.create(
            name="Владимир",
            mid_name="Николаевич",
            last_name="Иванов",
            telegram_id=123456,
        )

        assert user.id is not None
        assert user.name == "Владимир"
        assert user.last_name == "Иванов"
        assert user.telegram_id == 123456

    async def test_get_by_id(self, user_repo: UserRepository, sample_user: UserModel):
        """Получение пользователя по ID."""
        user = await user_repo.get_by_id(sample_user.id)

        assert user is not None
        assert user.id == sample_user.id
        assert user.name == sample_user.name

    async def test_get_by_id_not_found(self, user_repo: UserRepository):
        """
        Получение несуществующего пользователя.

        Не используем sample_user — намеренно проверяем пустую БД.
        """
        user = await user_repo.get_by_id(99999)

        assert user is None

    async def test_get_by_telegram_id(self, user_repo: UserRepository, sample_user: UserModel):
        """Получение пользователя по Telegram ID."""
        user = await user_repo.get_by_telegram_id(sample_user.telegram_id)

        assert user is not None
        assert user.telegram_id == sample_user.telegram_id

    async def test_get_by_telegram_id_not_found(self, user_repo: UserRepository):
        """Telegram ID не найден."""
        user = await user_repo.get_by_telegram_id(99999)

        assert user is None

    async def test_get_or_create_creates_new(self, user_repo: UserRepository):
        """
        get_or_create создаёт нового пользователя.

        Не используем sample_user — проверяем создание нового.
        """
        user, created = await user_repo.get_or_create_by_telegram(
            telegram_id=111222,
            name="Новый",
            mid_name="Новович",
            last_name="Пользователь",
        )

        assert created is True
        assert user.telegram_id == 111222
        assert user.name == "Новый"

    async def test_get_or_create_returns_existing(
        self, user_repo: UserRepository, sample_user: UserModel
    ):
        """get_or_create возвращает существующего пользователя."""
        # Пытаемся создать с тем же telegram_id
        user, created = await user_repo.get_or_create_by_telegram(
            telegram_id=sample_user.telegram_id,
            name="Другое имя",  # Это будет проигнорировано
            mid_name="Другое",
            last_name="Другая фамилия",
        )

        assert created is False
        assert user.name == sample_user.name  # Старое имя сохранилось

    async def test_update_user(self, user_repo: UserRepository, sample_user: UserModel):
        """Обновление пользователя."""
        updated = await user_repo.update(
            sample_user.id,
            name="Новое",
            email="new@example.com",
        )

        assert updated is not None
        assert updated.name == "Новое"
        assert updated.email == "new@example.com"
        assert updated.last_name == sample_user.last_name  # Не изменилось

    async def test_update_nonexistent(self, user_repo: UserRepository):
        """Обновление несуществующего пользователя."""
        updated = await user_repo.update(99999, name="Тест")

        assert updated is None

    async def test_delete_user(self, user_repo: UserRepository, sample_user: UserModel):
        """Удаление пользователя."""
        deleted = await user_repo.delete(sample_user.id)

        assert deleted is True

        # Проверяем, что удалён
        found = await user_repo.get_by_id(sample_user.id)
        assert found is None

    async def test_delete_nonexistent(self, user_repo: UserRepository):
        """Удаление несуществующего пользователя."""
        deleted = await user_repo.delete(99999)

        assert deleted is False

    async def test_get_one_with_filters(self, user_repo: UserRepository, user_factory):
        """Получение одного пользователя по фильтрам."""
        await user_factory(name="Иван", email="ivan@test.com")
        await user_factory(name="Пётр", email="petr@test.com")

        # Ищем по email
        user = await user_repo.get_one(email="ivan@test.com")

        assert user is not None
        assert user.name == "Иван"

    async def test_get_many(self, user_repo: UserRepository, user_factory):
        """Получение списка пользователей."""
        # Создаём пользователей с одинаковой фамилией
        await user_factory(name="Иван", last_name="Иванов")
        await user_factory(name="Пётр", last_name="Иванов")
        await user_factory(name="Сидор", last_name="Сидоров")

        # Получаем всех Ивановых
        users = await user_repo.get_many(last_name="Иванов")

        assert len(users) == 2
        assert all(u.last_name == "Иванов" for u in users)

    async def test_get_many_empty(self, user_repo: UserRepository):
        """Пустой список при отсутствии результатов."""
        users = await user_repo.get_many(last_name="Несуществующий")

        assert users == []


class TestRefreshTokenRepository:
    """
    Тесты для RefreshTokenRepository.

    Используемые фикстуры:
    - refresh_token_repo: экземпляр RefreshTokenRepository
    - sample_user: пользователь-владелец токена
    - sample_refresh_token: готовый токен для тестов
    """

    # =========================================================================
    # Тесты создания (CREATE)
    # =========================================================================

    async def test_create_refresh_token(
        self,
        refresh_token_repo,
        sample_user,
    ):
        """
        Создание refresh-токена.

        Не используем sample_refresh_token — тест проверяет именно создание.
        """
        expires_at_token = datetime.now() + timedelta(days=7)
        token_hash = create_refresh_token()

        token = await refresh_token_repo.create(
            token_hash=token_hash,
            user_id=sample_user.id,
            expires_at=expires_at_token,
            device_info="telegram",
        )

        assert token.id is not None
        assert token.token_hash == token_hash
        assert token.user_id == sample_user.id
        assert token.device_info == "telegram"

    async def test_create_token_without_device_info(
        self,
        refresh_token_repo,
        sample_user,
    ):
        """Создание токена без информации об устройстве (nullable поле)."""
        token = await refresh_token_repo.create(
            token_hash=create_refresh_token(),
            user_id=sample_user.id,
            expires_at=datetime.now() + timedelta(days=7),
            device_info=None,
        )

        assert token.id is not None
        assert token.device_info is None

    # =========================================================================
    # Тесты чтения (READ)
    # =========================================================================

    async def test_get_by_id(self, refresh_token_repo, sample_refresh_token):
        """Получение токена по ID."""
        token = await refresh_token_repo.get_by_id(sample_refresh_token.id)

        assert token is not None
        assert token.id == sample_refresh_token.id
        assert token.token_hash == sample_refresh_token.token_hash

    async def test_get_by_id_not_found(self, refresh_token_repo):
        """Получение несуществующего токена по ID."""
        token = await refresh_token_repo.get_by_id(99999)

        assert token is None

    async def test_get_by_user_id(
        self,
        refresh_token_repo,
        sample_user,
        sample_refresh_token,
    ):
        """Получение токена по user_id."""
        token = await refresh_token_repo.get_by_user_id(sample_user.id)

        assert token is not None
        assert token.id == sample_refresh_token.id
        assert token.user_id == sample_user.id

    async def test_get_by_user_id_not_found(self, refresh_token_repo):
        """Получение токена для несуществующего пользователя."""
        token = await refresh_token_repo.get_by_user_id(99999)

        assert token is None

    async def test_get_one_by_token_hash(
        self,
        refresh_token_repo,
        sample_refresh_token,
    ):
        """
        Получение токена по хешу.

        Важный кейс: при валидации refresh-токена клиент присылает хеш,
        и мы ищем токен в БД по этому хешу.
        """
        token = await refresh_token_repo.get_one(token_hash=sample_refresh_token.token_hash)

        assert token is not None
        assert token.id == sample_refresh_token.id

    async def test_get_one_by_token_hash_not_found(self, refresh_token_repo):
        """Поиск по несуществующему хешу."""
        token = await refresh_token_repo.get_one(token_hash="nonexistent_hash")

        assert token is None

    async def test_get_many_by_user_id(
        self,
        refresh_token_repo,
        sample_user,
    ):
        """
        Получение всех токенов пользователя.

        Сценарий: пользователь залогинен с нескольких устройств,
        у каждого свой refresh-токен.
        """
        # Создаём несколько токенов для одного пользователя
        await refresh_token_repo.create(
            token_hash=create_refresh_token(),
            user_id=sample_user.id,
            expires_at=datetime.now() + timedelta(days=7),
            device_info="mobile",
        )
        await refresh_token_repo.create(
            token_hash=create_refresh_token(),
            user_id=sample_user.id,
            expires_at=datetime.now() + timedelta(days=7),
            device_info="desktop",
        )
        await refresh_token_repo.create(
            token_hash=create_refresh_token(),
            user_id=sample_user.id,
            expires_at=datetime.now() + timedelta(days=7),
            device_info="tablet",
        )

        tokens = await refresh_token_repo.get_many(user_id=sample_user.id)

        assert len(tokens) == 3
        assert all(t.user_id == sample_user.id for t in tokens)
        devices = {t.device_info for t in tokens}
        assert devices == {"mobile", "desktop", "tablet"}

    async def test_get_many_empty(self, refresh_token_repo):
        """Пустой список при отсутствии токенов."""
        tokens = await refresh_token_repo.get_many(user_id=99999)

        assert tokens == []

    # =========================================================================
    # Тесты обновления (UPDATE)
    # =========================================================================

    async def test_update_device_info(
        self,
        refresh_token_repo,
        sample_refresh_token,
    ):
        """Обновление информации об устройстве."""
        updated = await refresh_token_repo.update(
            sample_refresh_token.id,
            device_info="updated_device",
        )

        assert updated is not None
        assert updated.device_info == "updated_device"
        # Остальные поля не изменились
        assert updated.token_hash == sample_refresh_token.token_hash
        assert updated.user_id == sample_refresh_token.user_id

    async def test_update_expires_at(
        self,
        refresh_token_repo,
        sample_refresh_token,
    ):
        """
        Обновление времени истечения токена.

        Сценарий: продление сессии при активности пользователя.
        """
        new_expires = datetime.now() + timedelta(days=30)

        updated = await refresh_token_repo.update(
            sample_refresh_token.id,
            expires_at=new_expires,
        )

        assert updated is not None
        # Сравниваем с точностью до секунды (избегаем проблем с микросекундами)
        assert updated.expires_at.replace(microsecond=0) == new_expires.replace(microsecond=0)

    async def test_update_nonexistent(self, refresh_token_repo):
        """Обновление несуществующего токена."""
        updated = await refresh_token_repo.update(99999, device_info="test")

        assert updated is None

    # =========================================================================
    # Тесты удаления (DELETE)
    # =========================================================================

    async def test_delete_token(self, refresh_token_repo, sample_refresh_token):
        """
        Удаление токена.

        Сценарий: пользователь нажал "Выйти" на устройстве.
        """
        deleted = await refresh_token_repo.delete(sample_refresh_token.id)

        assert deleted is True

        # Проверяем, что токен удалён
        found = await refresh_token_repo.get_by_id(sample_refresh_token.id)
        assert found is None

    async def test_delete_nonexistent(self, refresh_token_repo):
        """Удаление несуществующего токена."""
        deleted = await refresh_token_repo.delete(99999)

        assert deleted is False

    # =========================================================================
    # Бизнес-сценарии
    # =========================================================================

    async def test_token_rotation(
        self,
        refresh_token_repo,
        sample_user,
    ):
        """
        Ротация токена (refresh token rotation).

        Сценарий безопасности: при использовании refresh-токена
        старый удаляется и создаётся новый. Это защищает от replay-атак.

        Не используем sample_refresh_token, чтобы избежать проблем
        с кэшированием SQLAlchemy сессии после delete.
        """
        old_token_hash = create_refresh_token()

        # Создаём "старый" токен
        old_token = await refresh_token_repo.create(
            token_hash=old_token_hash,
            user_id=sample_user.id,
            expires_at=datetime.now() + timedelta(days=7),
            device_info="mobile",
        )

        # Удаляем старый токен
        await refresh_token_repo.delete(old_token.id)

        # Создаём новый с другим хешем
        new_token_hash = create_refresh_token()
        new_token = await refresh_token_repo.create(
            token_hash=new_token_hash,
            user_id=sample_user.id,
            expires_at=datetime.now() + timedelta(days=7),
            device_info="mobile",
        )

        # Старый токен недоступен по хешу
        old_by_hash = await refresh_token_repo.get_one(token_hash=old_token_hash)
        assert old_by_hash is None

        # Новый токен существует и доступен по хешу
        new_by_hash = await refresh_token_repo.get_one(token_hash=new_token_hash)
        assert new_by_hash is not None
        assert new_by_hash.id == new_token.id

    async def test_logout_all_devices(
        self,
        refresh_token_repo,
        sample_user,
    ):
        """
        Выход со всех устройств.

        Сценарий: пользователь нажал "Выйти везде" или сменил пароль.
        Все refresh-токены должны быть удалены.
        """
        # Создаём токены для нескольких устройств
        for device in ["mobile", "desktop", "tablet"]:
            await refresh_token_repo.create(
                token_hash=create_refresh_token(),
                user_id=sample_user.id,
                expires_at=datetime.now() + timedelta(days=7),
                device_info=device,
            )

        # Получаем все токены пользователя
        tokens = await refresh_token_repo.get_many(user_id=sample_user.id)
        assert len(tokens) == 3

        # Удаляем все токены
        for token in tokens:
            await refresh_token_repo.delete(token.id)

        # Проверяем, что токенов больше нет
        remaining = await refresh_token_repo.get_many(user_id=sample_user.id)
        assert remaining == []
