import logging
from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse
from src.application.services.hh_service import AuthTokens, IHHService
from src.application.use_cases.auth_hh import OAuthHHUseCase
from src.settings import app_settings
from starlette.routing import NoMatchFound

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    route_class=DishkaRoute,
)


logger = logging.getLogger(__name__)


@router.get("/hh/oauth/url", name="get_oauth_url")
async def get_oauth_url(
    hh_service: FromDishka[IHHService],
    state: Annotated[
        str,
        Query(
            description="Текущее состояние, для возврата после авторизации",
        ),
    ] = "test_tokens",
) -> str:
    """
    Эндпоинт для получения ссылки для авторизации

    :param state: Текущее состояние куда нужно будет выполнить редирект после получения токенов
    :param hh_service: Сервис для работы с hh.ru
    :return:
    """
    return hh_service.get_auth_url(state)


@router.get("/hh/tokens", name="get_hh_token")
async def get_tokens(
    request: Request,
    use_case: FromDishka[OAuthHHUseCase],
    code: Annotated[str, Query(description="Код авторизации от HeadHunter")],
    state: Annotated[str, Query(description="Состояние переданное для возврата после авторизации")],
) -> RedirectResponse:
    """
    Эндпоинт для получения токенов после OAuth редиректа от HeadHunter.

    :param request: Объект запроса для получения redirect_url по имени (state)
    :param use_case: Use case, где описан процесс авторизации (получения токенов и url для редиректа)
    :param code: Обязательный код авторизации, который HeadHunter передает в query параметрах
    :param state: Обязательное состояние для редиректа после получения токенов
    :return:
    """
    try:
        logger.info("Обмен exchange token'а на access и refresh токены")
        redirect_url, tokens = await use_case(code, state, request, app_settings.HH_FAKE_SUBJECT)
        response = RedirectResponse(redirect_url)
        response.set_cookie("access_token", value=tokens["access_token"])
        response.set_cookie("refresh_token", value=tokens["refresh_token"])
        logger.info("Токены получены")
        return response
    except ConnectionError:
        logger.error("Ошибка соединения с API hh.ru")
        raise
    except NoMatchFound as e:
        logger.critical("Не корректно передан state=%s. Детали ошибки: %s", state, exc_info=e)
        raise


@router.get("/hh/tokens/test", name="test_tokens")
async def get_tokens_for_test(
    hh_service: FromDishka[IHHService],
    request: Request,
    code: Annotated[str, Query(description="Код авторизации от HeadHunter")] = None,
    state: Annotated[
        str, Query(description="Состояние переданное для возврата после авторизации")
    ] = None,
) -> AuthTokens:
    """
    Тестовая ручка для получения токенов авторизации
    :param code: код авторизации
    :param request: объект Request
    :param state: переданное состояние для редиректа
    :param hh_service: сервис для работы с API hh.ru
    :return:
    """
    logger.warning("Используется тестовая ручка для получения access токена")
    if code:
        return (await hh_service.auth(code))[1]

    return AuthTokens(
        access_token=request.cookies.get("access_token"),
        refresh_token=request.cookies.get("refresh_token"),
    )
