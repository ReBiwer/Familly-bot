from contextlib import asynccontextmanager

from fastapi import FastAPI
from src.infrastructure.di import init_di_container
from src.infrastructure.monitoring import setup_monitoring
from src.presentation.api.ai import router as ai_router
from src.presentation.api.auth import router as auth_router
from src.presentation.api.health import router as health_router
from src.presentation.wsgi import Application, get_app_options


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await app.state.dishka_container.close()


def create_web_app() -> FastAPI:
    app = FastAPI(
        title="AI-HR",
        description="Clean Architecture implementation for AI HR",
        lifespan=lifespan,
    )
    setup_monitoring(app)
    app.include_router(auth_router)
    app.include_router(ai_router)
    app.include_router(health_router)
    init_di_container(app)

    return app


if __name__ == "__main__":
    from src.common import setup_logging
    from src.infrastructure.settings.app import app_settings

    setup_logging(app_settings.LOG_LEVEl)

    app = create_web_app()
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
