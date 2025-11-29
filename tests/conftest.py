import pytest
from playwright.sync_api import Page
from src.infrastructure.settings.test import TestAppSettings


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 1440, "height": 900},
        "locale": "ru-RU",
        "timezone_id": "Europe/Moscow",
        "ignore_https_errors": True,
        # Примеры дополнительных опций при необходимости:
        # "color_scheme": "dark",
        # "geolocation": {"latitude": 55.751244, "longitude": 37.618423},
        # "permissions": ["geolocation"],
        # "storage_state": "state.json",
    }


@pytest.fixture(autouse=True)
def _tune_playwright_timeouts(request) -> None:
    """Применяет таймауты только для тестов, использующих фикстуру `page`."""
    if "page" in getattr(request, "fixturenames", ()):  # не трогаем тесты без Playwright
        page: Page = request.getfixturevalue("page")
        page.set_default_timeout(5000)
        page.set_default_navigation_timeout(15000)


@pytest.fixture(scope="session")
def test_settings() -> TestAppSettings:
    return TestAppSettings()


def pytest_addoption(parser):
    parser.addoption(
        "--run-migrations",
        action="store_true",
        help="Запустить alembic upgrade в автозапускаемой фикстуре",
    )
