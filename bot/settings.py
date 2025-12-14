from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisSettings(BaseModel):
    """
    Настройки подключения к Redis.

    Переменные загружаются через AppSettings с префиксом REDIS__
    """

    HOST: str
    PORT: str
    NUM_DB: int

    @property
    def redis_url(self) -> str:
        return f"redis://{self.HOST}:{self.PORT}/{self.NUM_DB}"


class BotSettings(BaseSettings):
    BASE_DIR: Path = Path(__file__).resolve().parent
    BOT_TOKEN: str
    BACKEND_BASE_URL: str

    REDIS: RedisSettings

    model_config = SettingsConfigDict(
        env_file=f"/{BASE_DIR}/.env",
        extra="ignore",
        env_nested_delimiter="__",  # Ключевой параметр для вложенных моделей!
    )


bot_settings = BotSettings()
