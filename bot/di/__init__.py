from aiogram import Dispatcher
from dishka import AsyncContainer, make_async_container
from dishka.integrations.aiogram import AiogramProvider, setup_dishka

from .providers import AdaptersProviders, CommonProvider


def _container_factory() -> AsyncContainer:
    return make_async_container(
        AiogramProvider(),
        CommonProvider(),
        AdaptersProviders(),
    )


def init_di_container(dp: Dispatcher) -> None:
    setup_dishka(
        container=_container_factory(),
        router=dp,
        auto_inject=True,  # Автоматически внедряем зависимости в хендлеры
    )
