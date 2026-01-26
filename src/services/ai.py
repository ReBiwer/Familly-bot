import asyncio
import logging
import random

import openai
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.messages.base import BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.services.prompts import PromptService
from src.settings import app_settings

logger = logging.getLogger(__name__)


class AIServiceState(MessagesState):
    """
    Состояние графа для AIService.

    Наследуется от MessagesState, который автоматически включает:
        messages: Annotated[list[BaseMessage], add_messages]
            - История сообщений в диалоге (HumanMessage, AIMessage, SystemMessage)
            - С встроенным reducer add_messages для автоматического добавления новых сообщений

    Дополнительные атрибуты:
        response: Последний ответ от LLM в виде строки (для удобства)
    """

    response: str


def gen_png_graph(app_obj, schema_path: str = f"{app_settings.BASE_DIR}/schema_graph.png") -> None:
    """
    Генерирует PNG-изображение графа и сохраняет его в файл.

    Args:
        app_obj: Скомпилированный объект графа
        schema_path: Имя файла для сохранения (по умолчанию "schema_graph.png" в директории проекта)
    """
    logger.debug("Generate schema graph in path='%s'", schema_path)
    with open(schema_path, "wb") as f:
        f.write(app_obj.get_graph().draw_mermaid_png())


class AIService:
    DEFAULT_SYSTEM_PROMPT_NAME = "system_default"

    def __init__(
        self,
        checkpointer: BaseCheckpointSaver,
        prompt_service: PromptService,
        create_png_graph: bool = False,
    ):
        """
        Инициализация сервиса.

        Args:
            checkpointer: Объект для сохранения состояния диалога.
                          Используй MemorySaver для тестов или PostgresSaver для продакшена.
            prompt_service: Сервис для получения промптов.
                           Промпты загружаются из YAML файла и фильтруются по настройкам.
            create_png_graph: Если True, при инициализации создаст PNG-схему графа.
                             Полезно для отладки и документации.

        Почему параметры именно такие:
        - checkpointer обязательный, т.к. без него теряется история диалога
        - prompt_service обязательный — централизованное управление промптами
        - create_png_graph по умолчанию False, т.к. требует дополнительных зависимостей
        """
        logger.debug(
            "Инициализация LLM модели: %s\nBase URL модели: %s",
            app_settings.LLM.OPENAI_MODEL,
            app_settings.LLM.BASE_URL,
        )

        self.llm = self._get_chat_llm()

        self._prompt_service = prompt_service
        self._workflow = self._build_workflow(checkpointer)

        logger.debug("The workflow is built")
        if create_png_graph:
            gen_png_graph(self._workflow)

    @staticmethod
    def _get_chat_llm() -> BaseChatModel:
        if app_settings.LLM.OLLAMA_MODEL:
            return ChatOllama(
                model=app_settings.LLM.OLLAMA_MODEL,
                temperature=app_settings.LLM.TEMPERATURE,
            )
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

    def _build_workflow(self, checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
        """
        Строит граф workflow для обработки сообщений.

        Args:
            checkpointer: Объект для персистентности состояния

        Returns:
            Скомпилированный граф, готовый к выполнению

        Архитектура графа:
        START -> generate_response -> END

        Почему такой простой граф:
        - Минимальная сложность для базового функционала
        - Легко расширить: добавить ноды для RAG, модерации, форматирования
        - Checkpointer уже подключен для сохранения истории
        """
        workflow = StateGraph(AIServiceState)
        workflow.add_node("generate_response", self._generate_response_node)

        workflow.add_edge(START, "generate_response")
        workflow.add_edge("generate_response", END)

        return workflow.compile(checkpointer=checkpointer)

    async def _request_llm(self, messages: list[BaseMessage]) -> BaseMessage | None:
        """
        Отправляет запрос к LLM с экспоненциальными retry.

        Args:
            messages: Список сообщений для отправки (системные + пользовательские)

        Returns:
            Ответ от LLM или None если все попытки исчерпаны

        Raises:
            openai.BadRequestError: Ошибка в параметрах запроса (не ретраится)
            openai.AuthenticationError: Проблема с API-ключом (не ретраится)
            openai.NotFoundError: Модель не найдена (не ретраится)
            openai.APIStatusError: HTTP ошибки < 500 (не ретраится)

        Стратегия retry:
        - Экспоненциальная задержка: 0.5s -> 1s -> 2s -> 4s -> 8s
        - Jitter (случайный разброс) для предотвращения "thundering herd"
        - Максимум 5 попыток
        - Ретраим только временные ошибки (5xx, timeout, rate limit)

        Почему именно такая стратегия:
        - Экспоненциальный backoff рекомендован OpenAI и большинством API
        - Jitter предотвращает одновременные повторные запросы от многих клиентов
        - 5 попыток — баланс между надёжностью и временем ожидания пользователя
        """
        max_attempts = 5
        base_delay = 0.5
        max_delay = 8.0

        for attempt in range(1, max_attempts + 1):
            try:
                logger.debug("LLM request attempt=%s", attempt)
                return await self.llm.ainvoke(messages)

            # Критические ошибки — не ретраим, сразу пробрасываем
            except openai.BadRequestError as e:
                logger.error(
                    "LLM отклонил запрос: вероятно, ошибка в промпте или параметрах. request_id=%s",
                    getattr(e, "request_id", None),
                    exc_info=e,
                )
                raise

            except openai.AuthenticationError as e:
                logger.critical(
                    "LLM отклонил запрос из-за авторизации. Проверь API-ключ/лимиты. request_id=%s",
                    getattr(e, "request_id", None),
                    exc_info=e,
                )
                raise

            except openai.NotFoundError as e:
                logger.error(
                    "LLM не смог найти указанный ресурс (модель или эндпоинт). request_id=%s",
                    getattr(e, "request_id", None),
                    exc_info=e,
                )
                raise

            except openai.APIStatusError as e:
                status_code = e.status_code or 0
                # 4xx ошибки — клиентские, ретраить бессмысленно
                if status_code < 500:
                    logger.error(
                        "LLM вернул контролируемый статус %s, повтор не имеет смысла. request_id=%s",
                        status_code,
                        getattr(e, "request_id", None),
                        exc_info=e,
                    )
                    raise
                # 5xx — серверные, можно попробовать ещё раз
                logger.warning(
                    "LLM вернул статус %s. Повтор запроса (attempt=%s/%s). request_id=%s",
                    status_code,
                    attempt,
                    max_attempts,
                    getattr(e, "request_id", None),
                    exc_info=e,
                )

            # Временные ошибки — ретраим
            except (
                TimeoutError,
                openai.APIConnectionError,
                openai.APITimeoutError,
                openai.RateLimitError,
            ) as e:
                logger.warning(
                    "Временный сбой при обращении к LLM. Повтор запроса (attempt=%s/%s). request_id=%s",
                    attempt,
                    max_attempts,
                    getattr(e, "request_id", None),
                    exc_info=e,
                )

            except openai.OpenAIError as e:
                logger.exception(
                    "Непредвиденная ошибка OpenAI SDK. request_id=%s",
                    getattr(e, "request_id", None),
                )
                raise

            # Проверяем, исчерпаны ли попытки
            if attempt == max_attempts:
                logger.error(
                    "LLM-запрос не удался после %s попыток. Сообщаем об ошибке наверх.",
                    max_attempts,
                )
                raise RuntimeError(f"LLM request failed after {max_attempts} attempts")

            # Расчёт задержки перед следующей попыткой
            exponential_delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            jitter = random.uniform(0, base_delay)
            sleep_for = exponential_delay + jitter
            logger.debug("Ожидаем %.2f секунд перед следующим повтором LLM-запроса", sleep_for)
            await asyncio.sleep(sleep_for)

        return None

    def _get_system_prompt(self, prompt_name: str | None = None) -> str:
        """
        Получает системный промпт из PromptService.

        Args:
            prompt_name: Имя промпта. Если None, используется DEFAULT_SYSTEM_PROMPT_NAME.

        Returns:
            Текст системного промпта
        """
        name = prompt_name or self.DEFAULT_SYSTEM_PROMPT_NAME
        prompt = self._prompt_service.get_prompt(name)
        return prompt.template

    async def _generate_response_node(self, state: AIServiceState) -> dict:
        """
        Нода графа для генерации ответа с учётом ПОЛНОЙ истории диалога.

        Args:
            state: Текущее состояние с ПОЛНОЙ историей сообщений.
                   state["messages"] содержит ВСЕ предыдущие сообщения благодаря checkpointer!

        Returns:
            Словарь с ключами:
            - "messages": BaseMessage объект с ответом (добавится к истории через reducer)
            - "response": строковое представление ответа (для удобства)

        """
        all_messages = state["messages"]

        system_prompt = self._get_system_prompt()

        messages_for_llm: list[BaseMessage] = [
            SystemMessage(content=system_prompt),
            *all_messages,
        ]

        logger.debug(
            "Отправляем в LLM %d сообщений (последнее: %s...)",
            len(messages_for_llm),
            str(all_messages[-1].content)[:50] if all_messages else "пусто",
        )
        response = await self._request_llm(messages_for_llm)

        # Извлекаем текст ответа
        response_text = response.content if response else ""
        logger.debug("Получен ответ от LLM: %s...", str(response_text)[:50])
        return {
            "messages": [response],
            "response": str(response_text),
        }

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

        new_message_state = {
            "messages": [HumanMessage(content=message)],
        }
        result: AIServiceState = await self._workflow.ainvoke(new_message_state, config=config)

        return result["response"]
