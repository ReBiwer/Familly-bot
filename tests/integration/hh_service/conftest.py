import datetime
import json
import re
import socket
import time
from multiprocessing import Process
from pathlib import Path
from urllib.parse import urlparse

import pytest
import uvicorn
from hh_api.auth.keyed_stores import TokenPair
from hh_api.auth.token_manager import OAuthConfig
from playwright.async_api import Browser
from src.application.services.hh_service import AuthTokens
from src.domain.entities.user import UserEntity
from src.domain.entities.vacancy import VacancyEntity
from src.infrastructure.services.hh_service import HHService
from src.infrastructure.settings.test import TestAppSettings
from src.main import create_web_app


@pytest.fixture(scope="package")
def hh_service(test_settings: TestAppSettings) -> HHService:
    service = HHService()
    service._hh_tm.config = OAuthConfig(
        client_id=test_settings.HH_CLIENT_ID,
        client_secret=test_settings.HH_CLIENT_SECRET,
        redirect_uri=test_settings.HH_REDIRECT_URI,
    )
    return service


@pytest.fixture(scope="package")
def oauth_url(hh_service: HHService, test_settings: TestAppSettings) -> str:
    return hh_service.get_auth_url("test_tokens")


@pytest.fixture(scope="package")
def mock_hh_service(hh_service: HHService, session_mocker):
    session_mocker.patch("src.infrastructure.di.providers.HHService", return_value=hh_service)


@pytest.fixture(scope="package")
def run_test_server(test_settings: TestAppSettings, mock_hh_service):
    parsed = urlparse(test_settings.HH_REDIRECT_URI)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8000

    def _serve(h: str, p: int) -> None:
        # создаём приложение внутри процесса и запускаем uvicorn
        app = create_web_app()
        uvicorn.run(app, host=h, port=p, log_level="warning", lifespan="on")

    proc = Process(target=_serve, args=(host, port), daemon=True)
    proc.start()

    # ждём доступности порта
    deadline = time.time() + 15.0
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            try:
                if s.connect_ex((host, port)) == 0:
                    break
            except OSError:
                pass
        time.sleep(0.1)
    else:
        # если не поднялся — завершаем процесс и падаем
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=3.0)
        raise RuntimeError(f"Server did not start on {host}:{port} within 15s")

    try:
        yield
    finally:
        if proc.is_alive():
            proc.terminate()
        proc.join(timeout=5.0)


@pytest.fixture(scope="package")
def auth_storage_path(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("pw") / "auth.json"


@pytest.fixture(scope="package", autouse=True)
async def auth_tokens(
    browser: Browser,
    oauth_url: str,
    test_user_entity: UserEntity,
    test_settings: TestAppSettings,
    hh_service: HHService,
    run_test_server,
    auth_storage_path,
):
    """
    Фикстура для oauth авторизации на hh.ru и сохранения токенов
    :param browser: встроенная фикстура плагина playwright-pytest, представляет собой браузер
    :param oauth_url: url куда нужно зайти для oauth авторизации
    :param test_user_entity: тестовый пользователь к которому привязываем токены
    :param test_settings: фикстура, настройки тестов
    :param hh_service: инстанс HHService, который у нас замокан в запущенном приложении
    :param run_test_server: фикстура, запуск тестового сервиса для получения токенов
    :param auth_storage_path: путь для сохранения storage_state (состояния контекста playwright)
    :return:
    """
    # создаем контекст для хранения токенов в куках
    context = await browser.new_context()
    page = await context.new_page()

    # процесс oauth авторизации
    await page.goto(oauth_url, wait_until="domcontentloaded")
    await page.get_by_label("Электронная почта или телефон").fill(test_settings.HH_LOGIN)
    await page.get_by_role("button", name="Войти с паролем").click()
    await page.get_by_label("Пароль").fill(test_settings.HH_PASSWORD)
    await page.get_by_role("button", name="Войти").first.click()
    pattern = re.compile(
        r"^http://localhost:8000/auth/hh/tokens/test\?(?=.*\bcode=[^&]+)(?=.*\bstate=test_tokens).+"
    )
    await page.wait_for_url(pattern)
    text = await page.text_content("pre, body")
    data = json.loads(text)
    tokens = AuthTokens(access_token=data["access_token"], refresh_token=data["refresh_token"])

    # кладем полученные токены в куки браузера
    await context.add_cookies(
        [  # type: ignore
            {
                "name": "access_token",
                "value": tokens["access_token"],
                "url": "http://localhost:8000",
            },
            {
                "name": "refresh_token",
                "value": tokens["refresh_token"],
                "url": "http://localhost:8000",
            },
        ]
    )
    # сохраняем контекст в файле и закрываем контекст
    await context.storage_state(path=auth_storage_path)
    await context.close()

    # добавляем токены в инстанс HHService
    token_pair = TokenPair(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        expires_in=3600,
        expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=3600),
    )
    await hh_service.hh_client.tm.store.set_tokens(test_user_entity.hh_id, token_pair)

    return tokens


@pytest.fixture(scope="package")
def browser_context_args(auth_storage_path):
    return {"storage_state": auth_storage_path}


@pytest.fixture(scope="package")
async def test_vacancy(hh_service: HHService, test_settings: TestAppSettings) -> VacancyEntity:
    vacancy, *_ = await hh_service.get_vacancies(
        test_settings.HH_FAKE_SUBJECT, per_page=10, text="Python разработчик"
    )
    return vacancy
