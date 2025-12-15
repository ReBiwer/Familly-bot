from aiogram.utils.deep_linking import create_deep_link
from fastapi import Request
from src.application.services.state_manager import URL, IStateManager
from src.settings import app_settings


class StateManager(IStateManager):
    async def state_convert(self, state, payload: str, request: Request) -> URL:
        if state == "telegram":
            bot_link = create_deep_link(
                app_settings.FRONT.BOT_USERNAME,
                link_type="start",
                payload=payload,
                encode=True,
            )
            return bot_link

        redirect_link = request.url_for(state)
        return redirect_link.path
