"""
Тесты для AIService.

Используют моки для LLM и checkpointer.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

from src.services.ai import AIService
from src.services.prompts import PromptService


@pytest.fixture
def prompt_service(temp_prompts_file: Path) -> PromptService:
    """Создаёт PromptService с тестовыми промптами."""
    return PromptService(prompts_file_path=temp_prompts_file)


@pytest.fixture
def memory_checkpointer() -> MemorySaver:
    """Создаёт in-memory checkpointer для тестов."""
    return MemorySaver()


@pytest.fixture
def mock_llm_response():
    """Мок ответа от LLM."""
    response = MagicMock(spec=AIMessage)
    response.content = "Тестовый ответ от LLM"
    return response


class TestAIService:
    """Тесты для AIService."""

    def test_init(self, memory_checkpointer: MemorySaver, prompt_service: PromptService):
        """Успешная инициализация сервиса."""
        with patch("src.services.ai.ChatOpenAI"):
            service = AIService(
                checkpointer=memory_checkpointer,
                prompt_service=prompt_service,
            )

        assert service._prompt_service is prompt_service
        assert service._workflow is not None

    def test_get_config(self):
        """Проверка создания конфигурации."""
        config = AIService._get_config(user_id=42)

        assert config["configurable"]["thread_id"] == "user_42"

    def test_get_system_prompt(
        self,
        memory_checkpointer: MemorySaver,
        prompt_service: PromptService,
    ):
        """Получение системного промпта."""
        with patch("src.services.ai.ChatOpenAI"):
            service = AIService(
                checkpointer=memory_checkpointer,
                prompt_service=prompt_service,
            )

        # Получаем системный промпт по умолчанию (system_default)
        # В conftest.py есть system_default со статусом dev
        prompt = service._get_system_prompt()

        assert "Ты тестовый AI-ассистент" in prompt

    async def test_chat_success(
        self,
        memory_checkpointer: MemorySaver,
        prompt_service: PromptService,
        mock_llm_response,
    ):
        """Успешный чат с LLM."""
        with patch("src.services.ai.ChatOpenAI") as mock_chat:
            # Настраиваем мок
            mock_instance = MagicMock()
            mock_instance.ainvoke = AsyncMock(return_value=mock_llm_response)
            mock_chat.return_value = mock_instance

            service = AIService(
                checkpointer=memory_checkpointer,
                prompt_service=prompt_service,
            )

            response = await service.chat(user_id=1, message="Привет!")

        assert response == "Тестовый ответ от LLM"

    async def test_chat_empty_message(
        self,
        memory_checkpointer: MemorySaver,
        prompt_service: PromptService,
    ):
        """Ошибка при пустом сообщении."""
        with patch("src.services.ai.ChatOpenAI"):
            service = AIService(
                checkpointer=memory_checkpointer,
                prompt_service=prompt_service,
            )

        with pytest.raises(ValueError, match="не может быть пустым"):
            await service.chat(user_id=1, message="")

    async def test_chat_whitespace_message(
        self,
        memory_checkpointer: MemorySaver,
        prompt_service: PromptService,
    ):
        """Ошибка при сообщении из пробелов."""
        with patch("src.services.ai.ChatOpenAI"):
            service = AIService(
                checkpointer=memory_checkpointer,
                prompt_service=prompt_service,
            )

        with pytest.raises(ValueError, match="не может быть пустым"):
            await service.chat(user_id=1, message="   ")

    async def test_different_users_isolated(
        self,
        memory_checkpointer: MemorySaver,
        prompt_service: PromptService,
        mock_llm_response,
    ):
        """Разные пользователи имеют изолированные диалоги."""
        with patch("src.services.ai.ChatOpenAI") as mock_chat:
            mock_instance = MagicMock()
            mock_instance.ainvoke = AsyncMock(return_value=mock_llm_response)
            mock_chat.return_value = mock_instance

            service = AIService(
                checkpointer=memory_checkpointer,
                prompt_service=prompt_service,
            )

            # Чат с двумя разными пользователями
            response1 = await service.chat(user_id=1, message="Сообщение от пользователя 1")
            response2 = await service.chat(user_id=2, message="Сообщение от пользователя 2")

        # Оба получают ответ (изолированные сессии)
        assert response1 == "Тестовый ответ от LLM"
        assert response2 == "Тестовый ответ от LLM"

        # LLM вызывался дважды (для каждого пользователя)
        assert mock_instance.ainvoke.call_count == 2


class TestAIServiceRetry:
    """Тесты механизма retry."""

    async def test_retry_on_timeout(
        self,
        memory_checkpointer: MemorySaver,
        prompt_service: PromptService,
        mock_llm_response,
    ):
        """Повтор при timeout."""
        import openai

        with patch("src.services.ai.ChatOpenAI") as mock_chat:
            mock_instance = MagicMock()
            # Первый вызов — timeout, второй — успех
            mock_instance.ainvoke = AsyncMock(
                side_effect=[
                    openai.APITimeoutError(request=MagicMock()),
                    mock_llm_response,
                ]
            )
            mock_chat.return_value = mock_instance

            service = AIService(
                checkpointer=memory_checkpointer,
                prompt_service=prompt_service,
            )

            # Патчим sleep чтобы тест был быстрым
            with patch("src.services.ai.asyncio.sleep", new_callable=AsyncMock):
                response = await service.chat(user_id=1, message="Тест")

        assert response == "Тестовый ответ от LLM"
        assert mock_instance.ainvoke.call_count == 2

    async def test_no_retry_on_auth_error(
        self,
        memory_checkpointer: MemorySaver,
        prompt_service: PromptService,
    ):
        """Без повтора при ошибке авторизации."""
        import openai

        with patch("src.services.ai.ChatOpenAI") as mock_chat:
            mock_instance = MagicMock()
            mock_instance.ainvoke = AsyncMock(
                side_effect=openai.AuthenticationError(
                    message="Invalid API key",
                    response=MagicMock(),
                    body=None,
                )
            )
            mock_chat.return_value = mock_instance

            service = AIService(
                checkpointer=memory_checkpointer,
                prompt_service=prompt_service,
            )

            with pytest.raises(openai.AuthenticationError):
                await service.chat(user_id=1, message="Тест")

        # Только один вызов — без retry
        assert mock_instance.ainvoke.call_count == 1

