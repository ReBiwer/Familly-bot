from aiogram import Dispatcher
from dishka import make_async_container
from dishka.integrations.aiogram import AiogramProvider, setup_dishka

from bot.di.providers import BotProvider


def init_di_containers(dp: Dispatcher) -> None:
    container = make_async_container(
        BotProvider(),
        AiogramProvider(),
    )
    setup_dishka(container, router=dp, auto_inject=True)
