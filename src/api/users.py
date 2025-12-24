"""
Роутер для работы с пользователями.

CRUD операции для управления пользователями семейного бота.
"""

import logging

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, HTTPException, status

from src.db.repositories import UserRepository
from src.di import CurrentUserTelegramId
from src.schemas import UserCreate, UserRead, UserUpdate

router = APIRouter(
    prefix="/users",
    tags=["users"],
    route_class=DishkaRoute,
)

logger = logging.getLogger(__name__)


@router.get("/me", response_model=UserRead)
async def get_current_user_info(
    telegram_id: CurrentUserTelegramId,
    user_repo: FromDishka[UserRepository],
) -> UserRead:
    """
    Получение информации о текущем авторизованном пользователе.

    Этот эндпоинт защищён — требует валидный JWT токен в заголовке:
    ```
    Authorization: Bearer <access_token>
    ```

    Как работает:
    1. FastAPI видит зависимость `CurrentUserTelegramId`
    2. Вызывает `get_current_user_id` dependency
    3. Dependency проверяет токен и возвращает telegram_id
    4. Если токен невалиден — возвращает 401
    5. Загружаем пользователя из БД по telegram_id
    6. Возвращаем данные пользователя

    Returns:
        Данные текущего пользователя

    Raises:
        HTTPException 401: Если токен невалиден
        HTTPException 404: Если пользователь не найден
    """
    user = await user_repo.get_by_telegram_id(telegram_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserRead.model_validate(user)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    user_repo: FromDishka[UserRepository],
) -> UserRead:
    """
    Создание нового пользователя.

    Args:
        data: Данные для создания пользователя
        user_repo: Репозиторий пользователей

    Returns:
        Созданный пользователь

    Raises:
        HTTPException 409 если пользователь с таким telegram_id уже существует
    """
    logger.info("Creating user: %s %s", data.name, data.last_name)

    # Проверяем, нет ли уже пользователя с таким telegram_id
    if data.telegram_id:
        existing = await user_repo.get_by_telegram_id(data.telegram_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with telegram_id={data.telegram_id} already exists",
            )

    user = await user_repo.create(**data.model_dump())
    logger.info("User created with id=%s", user.id)

    return UserRead.model_validate(user)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    user_repo: FromDishka[UserRepository],
) -> UserRead:
    """
    Получение пользователя по ID.

    Args:
        user_id: ID пользователя
        user_repo: Репозиторий пользователей

    Returns:
        Данные пользователя

    Raises:
        HTTPException 404 если пользователь не найден
    """
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id={user_id} not found",
        )

    return UserRead.model_validate(user)


@router.get("/telegram/{telegram_id}", response_model=UserRead)
async def get_user_by_telegram(
    telegram_id: int,
    user_repo: FromDishka[UserRepository],
) -> UserRead:
    """
    Получение пользователя по Telegram ID.

    Args:
        telegram_id: ID пользователя в Telegram
        user_repo: Репозиторий пользователей

    Returns:
        Данные пользователя

    Raises:
        HTTPException 404 если пользователь не найден
    """
    user = await user_repo.get_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with telegram_id={telegram_id} not found",
        )

    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    data: UserUpdate,
    user_repo: FromDishka[UserRepository],
) -> UserRead:
    """
    Обновление данных пользователя.

    Args:
        user_id: ID пользователя
        data: Данные для обновления (только заполненные поля)
        user_repo: Репозиторий пользователей

    Returns:
        Обновлённый пользователь

    Raises:
        HTTPException 404 если пользователь не найден
    """
    # Получаем только непустые поля для обновления
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}

    if not update_data:
        # Если нечего обновлять, просто возвращаем текущего пользователя
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id={user_id} not found",
            )
        return UserRead.model_validate(user)

    logger.info("Updating user id=%s with data=%s", user_id, update_data)

    user = await user_repo.update(user_id, **update_data)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id={user_id} not found",
        )

    return UserRead.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    user_repo: FromDishka[UserRepository],
) -> None:
    """
    Удаление пользователя.

    Args:
        user_id: ID пользователя
        user_repo: Репозиторий пользователей

    Raises:
        HTTPException 404 если пользователь не найден
    """
    logger.info("Deleting user id=%s", user_id)

    deleted = await user_repo.delete(user_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id={user_id} not found",
        )


@router.post("/telegram/{telegram_id}/register", response_model=UserRead)
async def register_or_get_user(
    telegram_id: int,
    data: UserCreate,
    user_repo: FromDishka[UserRepository],
) -> UserRead:
    """
    Регистрация пользователя или получение существующего.

    Удобный эндпоинт для Telegram бота:
    - Если пользователь существует — возвращает его
    - Если нет — создаёт нового

    Args:
        telegram_id: ID пользователя в Telegram
        data: Данные для создания (если пользователь новый)
        user_repo: Репозиторий пользователей

    Returns:
        Пользователь (новый или существующий)
    """
    user, created = await user_repo.get_or_create_by_telegram(
        telegram_id=telegram_id,
        **data.model_dump(exclude={"telegram_id"}),
    )

    if created:
        logger.info("New user registered: telegram_id=%s", telegram_id)
    else:
        logger.info("Existing user found: telegram_id=%s", telegram_id)

    return UserRead.model_validate(user)
