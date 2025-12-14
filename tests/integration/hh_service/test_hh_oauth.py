import pytest
from playwright.async_api import Page
from src.application.services.hh_service import AuthTokens
from src.infrastructure.settings.test import TestAppSettings


@pytest.mark.skip
@pytest.mark.usefixtures("run_test_server")
async def test_oauth(page: Page, oauth_url: str, test_settings: TestAppSettings):
    await page.goto(oauth_url)
    await page.get_by_label("Электронная почта или телефон").fill(test_settings.HH_LOGIN)
    await page.get_by_role("button", name="Войти с паролем").click()
    await page.get_by_label("Пароль").fill(test_settings.HH_PASSWORD)
    await page.get_by_role("button", name="Войти").first.click()
    await page.wait_for_timeout(1000)


async def test_tokens(auth_tokens: AuthTokens):
    assert auth_tokens
    assert auth_tokens["access_token"] and auth_tokens["refresh_token"]
