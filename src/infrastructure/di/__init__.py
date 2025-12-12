from dishka import AsyncContainer, make_async_container
from dishka.integrations.fastapi import setup_dishka as fastapi_setup
from fastapi import FastAPI
from src.infrastructure.di.providers import (
    RepositoriesProviders,
    ServicesProviders,
    UseCasesProviders,
)


def container_factory() -> AsyncContainer:
    return make_async_container(ServicesProviders(), UseCasesProviders(), RepositoriesProviders())


def init_di_container(app: FastAPI) -> None:
    fastapi_setup(container_factory(), app)
