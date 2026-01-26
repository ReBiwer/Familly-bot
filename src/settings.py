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


class LLMSettings(BaseModel):
    """
    Настройки для работы с Language Model (LLM).

    Переменные загружаются через AppSettings с префиксом LLM__
    """

    OPENAI_MODEL: str
    BASE_URL: str = "https://openrouter.ai/api/v1"
    API_KEY: str
    OLLAMA_MODEL: str
    TEMPERATURE: float = 0.7


class AuthSettings(BaseModel):
    """
    Настройки аутентификации и авторизации.

    Переменные загружаются через AppSettings с префиксом AUTH__
    """

    JWT_TOKEN: str
    JWT_ALG: str = "HS256"


class FrontSettings(BaseModel):
    """
    Настройки для взаимодействия с фронтом (телеграм бот, фронт, мобильное приложение)

    Переменные закрюжаются через AppSettings с префиксом FRONT__
    """

    BOT_USERNAME: str
    BOT_TOKEN: str


class PromptSettings(BaseModel):
    """
    Настройки для системы управления промптами.

    Переменные загружаются через AppSettings с префиксом PROMPT__

    Attributes:
        STATUS: Статус промптов для использования ('dev' или 'prod').
                - 'dev' — промпты в разработке, могут быть нестабильны
                - 'prod' — проверенные промпты для продакшена
        VERSION: Версия промпта (например, '1.0', '2.1').
                 Позволяет использовать разные версии одного промпта.
        FILE_NAME: Имя YAML файла с промптами.
                   По умолчанию 'prompts.yaml'.

    Пример переменных окружения:
        PROMPT__STATUS=prod
        PROMPT__VERSION=1.0
    """

    STATUS: str = "dev"  # dev | prod
    VERSION: str = "1.0"
    FILE_NAME: str = "prompts.yaml"

    @property
    def file_path(self) -> Path:
        """
        Возвращает абсолютный путь к файлу с промптами.

        Путь вычисляется относительно директории src/, где лежит settings.py.
        Это гарантирует корректную работу независимо от того,
        откуда запущено приложение.

        Returns:
            Path: Абсолютный путь к файлу промптов (например, /home/user/project/src/prompts.yaml)
        """
        # __file__ — путь к settings.py, parent — директория src/
        src_dir = Path(__file__).resolve().parent
        return src_dir / self.FILE_NAME


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
    - PROMPT__STATUS=prod
    - PROMPT__VERSION=1.0
    """

    # Базовые настройки приложения
    BASE_DIR: Path = Path(__file__).resolve().parent
    LOG_LEVEl: str = "INFO"
    HOST: str
    PORT: int
    DEBUG: bool = False

    # Вложенные настройки - теперь будут корректно загружены
    AUTH: AuthSettings
    DB: DBSettings
    REDIS: RedisSettings
    LLM: LLMSettings
    FRONT: FrontSettings
    # PROMPT имеет значения по умолчанию — необязателен в .env
    PROMPT: PromptSettings = PromptSettings()

    model_config = SettingsConfigDict(
        env_file=f"/{BASE_DIR}/.env",
        extra="ignore",
        env_nested_delimiter="__",  # Ключевой параметр для вложенных моделей!
    )


app_settings = AppSettings()
