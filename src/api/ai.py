"""
Роутер для работы с AI.

Предоставляет эндпоинты для общения с AI-ассистентом.
"""

import logging

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, HTTPException, status

from src.schemas import ChatRequest, ChatResponse
from src.services.ai import AIService

router = APIRouter(
    prefix="/ai",
    tags=["ai"],
    route_class=DishkaRoute,
)

logger = logging.getLogger(__name__)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    ai_service: FromDishka[AIService],
) -> ChatResponse:
    """
    Отправка сообщения AI-ассистенту.

    Args:
        request: Запрос с user_id и message
        ai_service: Сервис для работы с AI (инжектится через Dishka)

    Returns:
        ChatResponse с ответом от AI

    Raises:
        HTTPException 400 если сообщение пустое
        HTTPException 500 если произошла ошибка при обращении к LLM
    """
    logger.info("Chat request from user_id=%s", request.user_id)

    try:
        response = await ai_service.chat(
            user_id=request.user_id,
            message=request.message,
        )

        logger.info("Chat response generated for user_id=%s", request.user_id)

        return ChatResponse(
            user_id=request.user_id,
            message=request.message,
            response=response,
        )

    except ValueError as e:
        logger.warning("Invalid chat request: %s", e)
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except RuntimeError as e:
        logger.error("AI service error: %s", e)
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service temporarily unavailable",
        )

    except Exception as e:
        logger.exception("Unexpected error in chat endpoint: %s", e)
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
