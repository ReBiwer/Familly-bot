import logging

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter
from src.application.dtos.query import QueryCreateDTO, QueryRecreateDTO
from src.application.services.hh_service import IHHService
from src.application.use_cases.generate_response import GenerateResponseUseCase
from src.application.use_cases.regenerate_response import RegenerateResponseUseCase
from src.domain.entities.response import ResponseToVacancyEntity

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/ai",
    tags=["ai"],
    route_class=DishkaRoute,
)


@router.post("/responses/generate")
async def generate_response(
    query: QueryCreateDTO,
    use_case: FromDishka[GenerateResponseUseCase],
) -> ResponseToVacancyEntity:
    logger.info("Получен запрос на генерацию отклика. Входные данные: %s", query)
    result = await use_case(query)
    logger.info("Сгенерированный отклик: %s", result.message)
    return result


@router.post("/responses/regenerate")
async def regenerate_response(
    query: QueryRecreateDTO,
    use_case: FromDishka[RegenerateResponseUseCase],
) -> ResponseToVacancyEntity:
    logger.info("Получен запрос на исправление отклика на вакансию. Входные данные: %s", query)
    result = await use_case(query)
    logger.info("Новый отклик: %s", result.message)
    return result


@router.post("/responses/send")
async def send_response(
    response: ResponseToVacancyEntity, hh_service: FromDishka[IHHService]
) -> None:
    logger.info("Отправка отклика - '%s' на вакансию %s", response.message, response.url_vacancy)
    await hh_service.send_response_to_vacancy(response)
