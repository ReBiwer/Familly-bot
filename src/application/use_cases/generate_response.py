import logging

from src.application.dtos.query import QueryCreateDTO
from src.application.services.ai_service import IAIService
from src.application.services.hh_service import IHHService
from src.domain.entities.response import ResponseToVacancyEntity

logger = logging.getLogger(__name__)


class GenerateResponseUseCase:
    def __init__(self, hh_service: IHHService, ai_service: IAIService):
        self.hh_service = hh_service
        self.ai_service = ai_service

    async def __call__(self, query: QueryCreateDTO) -> ResponseToVacancyEntity:
        logger.debug("Input vacancy url: %s", query.url_vacancy)
        vacancy_id = self.hh_service.extract_vacancy_id_from_url(query.url_vacancy)
        logger.debug("Extracted vacancy id: %s", vacancy_id)
        data = await self.hh_service.data_collect_for_llm(
            query.subject, query.user_id, vacancy_id, query.resume_hh_id
        )
        response = await self.ai_service.generate_response(data)
        logger.debug("Generated ai response: %s", response.message)
        return response
