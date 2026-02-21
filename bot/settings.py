from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendSettings(BaseModel):
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    @property
    def PATH(self) -> str:
        return f"http://{self.HOST}:{self.PORT}"


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
    DEBUG: bool = True

    REDIS: RedisSettings
    BACKEND: BackendSettings

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        extra="ignore",
        env_nested_delimiter="__",  # Ключевой параметр для вложенных моделей!
    )


bot_settings = BotSettings()
