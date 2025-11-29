from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class TestAppSettings(BaseSettings):
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    # Настройки тестовой базы данных
    DB_USER: str
    DB_PASS: str
    DB_HOST: str
    DB_NAME: str
    # Настройки для работы с API hh.ru
    HH_CLIENT_ID: str
    HH_CLIENT_SECRET: str
    HH_REDIRECT_URI: str
    HH_FAKE_SUBJECT: int = 1
    HH_LOGIN: str
    HH_PASSWORD: str

    # Настройки подключения к Redis
    REDIS_HOST: str
    REDIS_PORT: str
    REDIS_DB_NUM: int

    OPENAI_MODEL: str
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_API_KEY: str

    model_config = SettingsConfigDict(env_file=f"/{BASE_DIR}/.env.test", extra="ignore")

    @property
    def db_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:5432/{self.DB_NAME}"
        )

    #
    # @property
    # def redis_url(self) -> str:
    #     return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


test_app_settings = TestAppSettings()
