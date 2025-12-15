"""
Точка входа FastAPI приложения.

Создаёт и настраивает FastAPI app с DI контейнером,
мониторингом и роутерами.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api import ai_router, auth_router, health_router, users_router
from src.di import init_di_container
from src.monitoring import setup_monitoring
from src.wsgi import Application, get_app_options


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения.

    При завершении закрывает DI контейнер для корректного
    освобождения ресурсов (соединения с БД, Redis и т.д.).
    """
    yield
    await app.state.dishka_container.close()


def create_web_app() -> FastAPI:
    """
    Создаёт и настраивает FastAPI приложение.

    Returns:
        Настроенный экземпляр FastAPI
    """
    app = FastAPI(
        title="Family Bot API",
        description="API для семейного AI-ассистента",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Мониторинг (Prometheus метрики)
    setup_monitoring(app)

    # Роутеры
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(ai_router)

    # DI контейнер
    init_di_container(app)

    return app


# Для запуска через gunicorn/uvicorn
app = create_web_app()


if __name__ == "__main__":
    from src.common import setup_logging
    from src.settings import app_settings

    setup_logging(app_settings.LOG_LEVEl)

    options = get_app_options(
        host=app_settings.HOST,
        port=app_settings.PORT,
        timeout=900,
        workers=4,
    )

    gunicorn_app = Application(
        app=app,
        options=options,
    )
    gunicorn_app.run()
