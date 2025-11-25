import asyncio
import logging
import random
from typing import TypedDict

import openai
from langchain.prompts import PromptTemplate
from langchain_core.messages import HumanMessage
from langchain_core.messages.base import BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from source.application.services.ai_service import GenerateResponseData, IAIService
from source.domain.entities.employer import EmployerEntity
from source.domain.entities.response import ResponseToVacancyEntity
from source.domain.entities.resume import ResumeEntity
from source.domain.entities.vacancy import VacancyEntity
from source.infrastructure.settings.app import app_settings

logger = logging.getLogger(__name__)


class AIServiceState(TypedDict):
    vacancy: VacancyEntity
    resume: ResumeEntity
    employer: EmployerEntity
    user_rules: dict
    response: str | None
    user_comments: str | None


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


class AIService(IAIService):
    def __init__(self, checkpointer: BaseCheckpointSaver, create_png_graph: bool = False):
        logger.debug(
            "Инициализация LLM модели: %s\nBase URL модели: %s",
            app_settings.OPENAI_MODEL,
            app_settings.OPENROUTER_BASE_URL,
        )
        self.llm = ChatOpenAI(
            model=app_settings.OPENAI_MODEL,
            temperature=0.7,
            api_key=app_settings.OPENROUTER_API_KEY,  # pyright: ignore[reportArgumentType]
            base_url=app_settings.OPENROUTER_BASE_URL,
        )
        self._workflow = self._build_workflow(checkpointer)
        logger.debug("The workflow is built")
        if create_png_graph:
            gen_png_graph(self._workflow)

    @staticmethod
    def _get_config(user_id: int) -> RunnableConfig:
        return RunnableConfig(
            configurable={
                "thread_id": f"user_{user_id}",
            }
        )

    def _build_workflow(self, checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
        workflow = StateGraph(AIServiceState)  # type: ignore
        workflow.add_node("fake_node", lambda x: x)  # type: ignore
        workflow.add_node("generate_response", self._generate_response_node)
        workflow.add_node("regenerate_response", self._regenerate_response_node)

        workflow.add_conditional_edges(
            "fake_node",
            self._check_exist_response,
            {
                "generate_response": "generate_response",
                "regenerate_response": "regenerate_response",
            },
        )
        workflow.add_edge(START, "fake_node")
        workflow.add_edge("generate_response", END)
        workflow.add_edge("regenerate_response", END)
        return workflow.compile(checkpointer=checkpointer)

    @staticmethod
    def _check_exist_response(state: AIServiceState) -> str:
        if "response" in state and "user_comments" in state:
            return "regenerate_response"
        return "generate_response"

    async def _request_llm(self, messages: list[BaseMessage]) -> BaseMessage | None:
        """
        Отправляет запрос к LLM с экспоненциальными ретраями и,
        где это возможно, восстанавливается после временных сбоев.
        """
        max_attempts = 5
        base_delay = 0.5
        max_delay = 8.0

        for attempt in range(1, max_attempts + 1):
            try:
                logger.debug("LLM request attempt=%s", attempt)
                return await self.llm.ainvoke(messages)
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
                if status_code < 500:
                    logger.error(
                        "LLM вернул контролируемый статус %s, повтор не имеет смысла. "
                        "request_id=%s",
                        status_code,
                        getattr(e, "request_id", None),
                        exc_info=e,
                    )
                    raise
                logger.warning(
                    "LLM вернул статус %s. Повтор запроса (attempt=%s/%s). request_id=%s",
                    status_code,
                    attempt,
                    max_attempts,
                    getattr(e, "request_id", None),
                    exc_info=e,
                )
            except (
                TimeoutError,
                openai.APIConnectionError,
                openai.APITimeoutError,
                openai.RateLimitError,
            ) as e:
                logger.warning(
                    "Временный сбой при обращении к LLM. Повтор запроса "
                    "(attempt=%s/%s). request_id=%s",
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

            if attempt == max_attempts:
                logger.error(
                    "LLM-запрос не удался после %s попыток. Сообщаем об ошибке наверх.",
                    max_attempts,
                )
                raise

            exponential_delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            jitter = random.uniform(0, base_delay)
            sleep_for = exponential_delay + jitter
            logger.debug("Ожидаем %.2f секунд перед следующим повтором LLM-запроса", sleep_for)
            await asyncio.sleep(sleep_for)

        return None

    async def _generate_response_node(self, state: AIServiceState) -> dict[str, str]:
        prompt = PromptTemplate(
            input_variables=[
                "vacancy",
                "resume",
                "employer",
                "user_rules",
            ],
            template="""
            Ты мой помощник в написании сопроводительных писем.
            Тебе нужно составить сопроводительное письмо к этой вакансии: {vacancy}\n
            Письмо составляй учитывая следующую информацию: \n

            1. мое резюме {resume};\n
            2. описание работодателя если оно есть {employer}\n
            3. мои правила по составлению сопроводительного {user_rules};\n

            Также в конце нужно обязательно добавить абзац про мою мотивацию работы у работодателя
            опираясь на информацию из вакансии и описание работодателя (если оно есть).
            """,
        )
        message = HumanMessage(content=prompt.format(**state))
        logger.debug("Prompt formatted: %s", message.content[:50])
        response = await self._request_llm([message])
        return {"response": response.content}

    async def _regenerate_response_node(self, state: AIServiceState) -> dict[str, str]:
        prompt = PromptTemplate(
            input_variables=[
                "vacancy",
                "resume",
                "employer",
                "user_rules",
                "response",
                "user_comments",
            ],
            template="""
            Ты мой помощник в написании сопроводительных писем.
            Скорректируй этот ответ: {response}\n
            В исправлении учитывай следующую информацию: \n

            1. мои замечания {user_comments}\n
            2. описание вакансии {vacancy}\n
            3. мое резюме {resume};\n
            4. описание работодателя если оно есть {employer}\n
            5. мои правила по составлению сопроводительного {user_rules};\n
            """,
        )
        message = HumanMessage(content=prompt.format(**state))
        logger.debug("Prompt formatted: %s", message.content[:50])
        response = await self._request_llm([message])
        return {"response": response.content}

    async def generate_response(self, data: GenerateResponseData) -> ResponseToVacancyEntity:
        start_state = AIServiceState(**data)
        config = self._get_config(data["user_id"])
        logger.debug("Generate response to vacancy=%s", start_state["vacancy"].name)
        result: AIServiceState = await self._workflow.ainvoke(start_state, config=config)  # type: ignore
        logger.debug("Generated response: %s", result["response"])
        return ResponseToVacancyEntity(
            url_vacancy=result["vacancy"].url_vacancy,
            vacancy_hh_id=result["vacancy"].hh_id,
            resume_hh_id=result["resume"].hh_id,
            message=result["response"],
        )

    async def regenerate_response(
        self,
        user_id: int,
        response: str,
        user_comments: str,
        data: GenerateResponseData | None = None,
    ) -> ResponseToVacancyEntity:
        config = self._get_config(user_id)
        if not data:
            state = await self._workflow.aget_state(config)

            if not state.values:
                logger.warning("Not saved state for user: id=%s", user_id)
                raise ValueError(
                    "Не найдено сохраненного состояния. Необходимо собрать актуальную информацию"
                )
            state_data = state.values
        else:
            state_data = AIServiceState(**data)

        state_data.update({"response": response, "user_comments": user_comments})
        logger.debug("Regenerate response to vacancy with user comments: %s", user_comments)
        result: AIServiceState = await self._workflow.ainvoke(state_data, config)
        logger.debug("Regenerated response: %s", result["response"])
        return ResponseToVacancyEntity(
            url_vacancy=result["vacancy"].url_vacancy,
            vacancy_hh_id=result["vacancy"].hh_id,
            resume_hh_id=result["resume"].hh_id,
            message=result["response"],
        )
