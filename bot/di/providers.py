from aiogram.fsm.context import FSMContext
from dishka import Provider, Scope, provide
from dishka.integrations.aiogram import AiogramMiddlewareData

from bot.adapters.backend import BackendAdapter
from bot.constants.keys import StorageKeys
from bot.entities.user import ResumeEntity, UserEntity
from bot.settings import bot_settings
from bot.use_cases import AuthUseCase


class BotProvider(Provider):
    scope = Scope.REQUEST

    @provide
    async def get_user(self, middleware_data: AiogramMiddlewareData) -> UserEntity | None:
        state: FSMContext = middleware_data.get("state")
        data_state = await state.get_data()
        if StorageKeys.USER_INFO in data_state and data_state[StorageKeys.USER_INFO]:
            return UserEntity.model_validate_json(data_state[StorageKeys.USER_INFO])
        return None

    @provide
    async def get_resume(self, middleware_data: AiogramMiddlewareData) -> ResumeEntity | None:
        state: FSMContext = middleware_data.get("state")
        data_state = await state.get_data()
        if StorageKeys.ACTIVE_RESUME in data_state and data_state[StorageKeys.ACTIVE_RESUME]:
            return ResumeEntity.model_validate_json(data_state[StorageKeys.ACTIVE_RESUME])
        return None

    @provide
    async def backend_provider(self) -> BackendAdapter:
        return BackendAdapter(bot_settings.BACKEND_BASE_URL)

    @provide
    async def auth_use_case(self, back_adapter: BackendAdapter) -> AuthUseCase:
        return AuthUseCase(back_adapter)
