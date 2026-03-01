import logging

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver

from src.middlewares.memory import trim_messages_middleware
from src.services.prompts import PromptService
from src.settings import app_settings

logger = logging.getLogger(__name__)


class AIService:
    """
    Сервис для оркерстрации агентом(ми)
    """

    DEFAULT_SYSTEM_PROMPT_NAME = "system_default"

    def __init__(
        self,
        checkpointer: BaseCheckpointSaver,
        prompt_service: PromptService,
    ):
        """
        Инициализация сервиса.

        Args:
            checkpointer: Объект для сохранения состояния диалога.
                          Используй MemorySaver для тестов или PostgresSaver для продакшена.
            prompt_service: Сервис для получения промптов.
                           Промпты загружаются из YAML файла и фильтруются по настройкам.
        """

        self._base_agent = create_agent(
            model=self._get_chat_llm(),
            system_prompt=prompt_service.get_prompt(self.DEFAULT_SYSTEM_PROMPT_NAME).template,
            checkpointer=checkpointer,
            tools=[],
            middleware=[trim_messages_middleware],
        )

        logger.debug("The workflow is built")

    @staticmethod
    def _get_chat_llm() -> BaseChatModel:
        if app_settings.LLM.OLLAMA_MODEL:
            logger.debug("Used Ollama model: %s", app_settings.LLM.OLLAMA_MODEL)
            return ChatOllama(
                model=app_settings.LLM.OLLAMA_MODEL,
                temperature=app_settings.LLM.TEMPERATURE,
            )
        logger.debug("Used OpenAI model: %s", app_settings.LLM.OPENAI_MODEL)
        return ChatOpenAI(
            model=app_settings.LLM.OPENAI_MODEL,
            api_key=app_settings.LLM.API_KEY,
            base_url=app_settings.LLM.BASE_URL,
            temperature=app_settings.LLM.TEMPERATURE,
        )

    @staticmethod
    def _get_config(user_id: int) -> RunnableConfig:
        return RunnableConfig(
            configurable={
                "thread_id": f"user_{user_id}",
            }
        )

    async def chat(self, user_id: int, message: str) -> str:
        """
        Отправляет сообщение пользователя и получает ответ от LLM с сохранением истории.

        Args:
            user_id: ID пользователя для сохранения контекста диалога.
                     Один user_id = один поток диалога с историей.
            message: Текст сообщения от пользователя

        Returns:
            Текстовый ответ от LLM

        Raises:
            ValueError: Если message пустой
            RuntimeError: Если LLM не вернул ответ после всех попыток
        """
        if not message.strip():
            raise ValueError("Сообщение не может быть пустым")

        config = self._get_config(user_id)
        logger.info("Обрабатываем сообщение от user_id=%s", user_id)

        human_message = HumanMessage(content=message)
        result = await self._base_agent.ainvoke({"messages": [human_message]}, config=config)

        logger.debug("Length messages: %s", len(result["messages"]))
        chat_response = result["messages"][-1].content

        return chat_response
