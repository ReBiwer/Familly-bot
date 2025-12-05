from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class DBSettings(BaseModel):
    """
    Настройки подключения к базе данных PostgreSQL.

    Использует BaseModel (не BaseSettings), чтобы переменные загружались
    через родительский AppSettings с правильным префиксом DB__
    """

    USER: str
    PASS: str
    HOST: str
    NAME: str

    @property
    def db_url(self) -> str:
        return f"postgresql+asyncpg://{self.USER}:{self.PASS}@{self.HOST}:5432/{self.NAME}"


class RedisSettings(BaseModel):
    """
    Настройки подключения к Redis.

    Переменные загружаются через AppSettings с префиксом REDIS__
    """

    HOST: str
    PORT: str
    CHECKPOINT_NUM_DB: int
    CHECKPOINT_TTL: int = 60  # Время жизни сейфпоинтов по умолчанию (1 час)

    @property
    def redis_url(self) -> str:
        return f"redis://{self.HOST}:{self.PORT}/{self.CHECKPOINT_NUM_DB}"


class HHAPISettings(BaseModel):
    """
    Настройки для работы с API HeadHunter.

    Переменные загружаются через AppSettings с префиксом HH__
    """

    CLIENT_ID: str
    CLIENT_SECRET: str
    REDIRECT_URI: str
    TOKEN_URL: str = "https://api.hh.ru/token"


class LLMSettings(BaseModel):
    """
    Настройки для работы с Language Model (LLM).

    Переменные загружаются через AppSettings с префиксом LLM__
    """

    MODEL: str
    BASE_URL: str = "https://openrouter.ai/api/v1"
    API_KEY: str


class AuthSettings(BaseModel):
    """
    Настройки аутентификации и авторизации.

    Переменные загружаются через AppSettings с префиксом AUTH__
    """

    JWT_TOKEN: str
    JWT_ALG: str = "HS256"


class Frontsettings(BaseModel):
    """
    Настройки для взаимодействия с фронтом (телеграм бот, фронт, мобильное приложение)

    Переменные закрюжаются через AppSettings с префиксом FRONT__
    """

    BOT_USERNAME: str


class AppSettings(BaseSettings):
    """
    Главные настройки приложения.

    Загружает все переменные из .env файла.
    Вложенные модели используют двойное подчеркивание (__) как разделитель.

    Пример переменных окружения:
    - HOST=localhost
    - PORT=8000
    - DB__USER=postgres
    - DB__PASS=secret
    - REDIS__HOST=localhost
    - LLM__API_KEY=sk-xxx
    """

    # Базовые настройки приложения
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    LOG_LEVEl: str = "INFO"
    HOST: str
    PORT: int

    # Вложенные настройки - теперь будут корректно загружены
    AUTH: AuthSettings
    DB: DBSettings
    REDIS: RedisSettings
    HH: HHAPISettings
    LLM: LLMSettings
    FRONT: Frontsettings

    model_config = SettingsConfigDict(
        env_file=f"/{BASE_DIR}/.env",
        extra="ignore",
        env_nested_delimiter="__",  # Ключевой параметр для вложенных моделей!
    )


app_settings = AppSettings()
