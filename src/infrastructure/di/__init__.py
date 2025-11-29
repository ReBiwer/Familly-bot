from aiogram import Dispatcher
from dishka import AsyncContainer, make_async_container
from dishka.integrations.aiogram import AiogramProvider
from dishka.integrations.aiogram import setup_dishka as aiogram_setup
from dishka.integrations.fastapi import setup_dishka as fastapi_setup
from fastapi import FastAPI
from src.infrastructure.di.providers import (
    BotProvider,
    RepositoriesProviders,
    ServicesProviders,
    UseCasesProviders,
)


def container_factory() -> AsyncContainer:
    return make_async_container(ServicesProviders(), UseCasesProviders(), RepositoriesProviders())


def bot_container_factory() -> AsyncContainer:
    return make_async_container(
        ServicesProviders(),
        UseCasesProviders(),
        RepositoriesProviders(),
        BotProvider(),
        AiogramProvider(),
    )


def init_di_container(app: FastAPI) -> None:
    fastapi_setup(container_factory(), app)


def init_di_container_bot(dp: Dispatcher) -> None:
    aiogram_setup(bot_container_factory(), router=dp, auto_inject=True)
