from collections.abc import AsyncGenerator

from aiogram.fsm.context import FSMContext
from dishka import Provider, Scope, provide
from dishka.integrations.aiogram import AiogramMiddlewareData
from hh_api.auth import KeyedTokenStore, OAuthConfig, RedisKeyedTokenStore
from langgraph.checkpoint.memory import BaseCheckpointSaver
from langgraph.checkpoint.redis import AsyncRedisSaver
from redis.asyncio.client import Redis
from src.application.repositories.base import IUnitOfWork
from src.application.repositories.resume import (
    IJobExperienceRepository,
    IResumeRepository,
)
from src.application.repositories.user import IUserRepository
from src.application.services.ai_service import IAIService
from src.application.services.hh_service import IHHService
from src.application.services.state_manager import IStateManager
from src.application.use_cases.auth_hh import OAuthHHUseCase
from src.application.use_cases.bot.authorization import AuthUseCase
from src.application.use_cases.generate_response import GenerateResponseUseCase
from src.application.use_cases.regenerate_response import RegenerateResponseUseCase
from src.constants.keys import StorageKeys
from src.domain.entities.resume import ResumeEntity
from src.domain.entities.user import UserEntity
from src.infrastructure.db.engine import async_session_maker
from src.infrastructure.db.repositories.resume import (
    JobExperienceRepository,
    ResumeRepository,
)
from src.infrastructure.db.repositories.user import UserRepository
from src.infrastructure.db.uow import UnitOfWork
from src.infrastructure.services.ai_service import AIService
from src.infrastructure.services.hh_service import CustomTokenManager, HHService
from src.infrastructure.services.state_manager import StateManager
from src.infrastructure.settings.app import app_settings


class ServicesProviders(Provider):
    scope = Scope.APP

    @provide
    def oauth_config(self) -> OAuthConfig:
        return OAuthConfig(
            client_id=app_settings.HH_CLIENT_ID,
            client_secret=app_settings.HH_CLIENT_SECRET,
            redirect_uri=app_settings.HH_REDIRECT_URI,
            token_url=app_settings.HH_TOKEN_URL,
        )

    @provide
    def keyed_store(self) -> KeyedTokenStore:
        redis_client = Redis.from_url(app_settings.redis_url)
        return RedisKeyedTokenStore(redis_client)

    @provide
    def custom_token_manager(
        self, config: OAuthConfig, keyed_store: KeyedTokenStore
    ) -> CustomTokenManager:
        return CustomTokenManager(
            config=config,
            store=keyed_store,
            user_agent="AI HR/1.0 (bykov100898@yandex.ru)",
        )

    @provide
    async def get_hh_service(
        self, token_manager: CustomTokenManager
    ) -> AsyncGenerator[IHHService, None]:
        hh_service = HHService(token_manager)
        try:
            yield hh_service
        finally:
            await hh_service.aclose_hh_client()

    @provide
    async def get_checkpointer(self) -> AsyncGenerator[BaseCheckpointSaver, None]:
        async with AsyncRedisSaver.from_conn_string(
            app_settings.redis_url,
            ttl={"default_ttl": app_settings.REDIS_CHECKPOINT_TTL},
        ) as checkpointer:
            await checkpointer.asetup()
            yield checkpointer
            await checkpointer.aclose()

    @provide
    def get_ai_service(self, checkpointer: BaseCheckpointSaver) -> IAIService:
        return AIService(checkpointer)

    @provide
    def get_generate_urls_service(self) -> IStateManager:
        return StateManager()


class UseCasesProviders(Provider):
    scope = Scope.REQUEST

    @provide
    def get_generate_response_use_case(
        self,
        hh_service: IHHService,
        ai_service: IAIService,
    ) -> GenerateResponseUseCase:
        return GenerateResponseUseCase(hh_service, ai_service)

    @provide
    def get_regenerate_response_use_case(
        self,
        hh_service: IHHService,
        ai_service: IAIService,
    ) -> RegenerateResponseUseCase:
        return RegenerateResponseUseCase(hh_service, ai_service)

    @provide
    def get_oauth_hh_use_case(
        self,
        hh_service: IHHService,
        state_manager: IStateManager,
        repository: type[IUserRepository],
        uow: IUnitOfWork,
    ) -> OAuthHHUseCase:
        return OAuthHHUseCase(hh_service, state_manager, repository, uow)


class RepositoriesProviders(Provider):
    scope = Scope.REQUEST

    @provide
    async def get_async_session(self) -> AsyncGenerator[IUnitOfWork, None]:
        async with async_session_maker() as session:
            yield UnitOfWork(session)

    @provide
    def get_user_repository(self) -> type[IUserRepository]:
        return UserRepository

    @provide
    def get_resume_repository(self) -> type[IResumeRepository]:
        return ResumeRepository

    @provide
    def get_job_experience_repository(self) -> type[IJobExperienceRepository]:
        return JobExperienceRepository


class BotProvider(Provider):
    scope = Scope.REQUEST

    @provide
    async def get_user_bot(self, middleware_data: AiogramMiddlewareData) -> UserEntity | None:
        state: FSMContext = middleware_data.get("state")
        data_state = await state.get_data()
        if StorageKeys.USER_INFO in data_state and data_state[StorageKeys.USER_INFO]:
            return UserEntity.model_validate_json(data_state[StorageKeys.USER_INFO])
        return None

    @provide
    async def get_resume_user_bot(
        self,
        middleware_data: AiogramMiddlewareData,
        uow: IUnitOfWork,
        class_resume_repo: type[IResumeRepository],
    ) -> ResumeEntity | None:
        state: FSMContext = middleware_data.get("state")
        data_state = await state.get_data()
        if StorageKeys.ACTIVE_RESUME_ID in data_state and data_state[StorageKeys.ACTIVE_RESUME_ID]:
            async with uow as session:
                resume_repo = class_resume_repo(session)
                resume = await resume_repo.get(id=data_state[StorageKeys.ACTIVE_RESUME_ID])
            return resume
        return None

    @provide
    async def auth_use_case(
        self,
        token_manager: CustomTokenManager,
        uow: IUnitOfWork,
        class_repo: type[IUserRepository],
    ) -> AuthUseCase:
        return AuthUseCase(token_manager, uow, class_repo)
