"""
Инициализация DI контейнера Dishka.

Dishka — легковесный DI фреймворк для Python с поддержкой async.
Интегрируется с FastAPI через setup_dishka.

Использование:
    from src.di import init_di_container

    app = FastAPI()
    init_di_container(app)
"""

from dishka import AsyncContainer, make_async_container
from dishka.integrations.fastapi import setup_dishka as fastapi_setup
from fastapi import FastAPI

from src.di.providers import DatabaseProvider, ServicesProvider, UseCasesProvider
from src.di.dependencies import CurrentUserTelegramId

__all__ = [
    "CurrentUserTelegramId",
]


def container_factory() -> AsyncContainer:
    """
    Создаёт DI контейнер со всеми провайдерами.

    Returns:
        AsyncContainer: Готовый контейнер для внедрения зависимостей
    """
    return make_async_container(
        ServicesProvider(),
        DatabaseProvider(),
        UseCasesProvider(),
    )


def init_di_container(app: FastAPI) -> None:
    """
    Инициализирует DI контейнер и подключает его к FastAPI.

    После вызова этой функции можно использовать Dishka в эндпоинтах:

    ```python
    from dishka.integrations.fastapi import FromDishka

    @router.post("/chat")
    async def chat(
        ai_service: FromDishka[AIService],
        message: str,
    ):
        return await ai_service.chat(user_id=1, message=message)
    ```

    Args:
        app: Экземпляр FastAPI приложения
    """
    fastapi_setup(container_factory(), app)
