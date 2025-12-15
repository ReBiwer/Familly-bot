"""
Сервис для управления промптами.

Этот модуль предоставляет функционал для загрузки, валидации и получения
промптов из YAML файла. Промпты фильтруются по статусу и версии,
указанным в настройках приложения.

Архитектура:
1. Промпты хранятся в YAML файле (src/prompts.yaml)
2. При инициализации сервис загружает и валидирует все промпты
3. Методы get_prompt() и format_prompt() используют настройки из app_settings

Почему YAML, а не база данных:
- Промпты — часть кода, должны версионироваться в Git
- Нет необходимости в динамическом изменении на продакшене
- Проще тестировать и делать code review изменений

Почему Pydantic для валидации:
- Автоматическая проверка структуры при загрузке
- Типизация для IDE и статических анализаторов
- Понятные сообщения об ошибках
"""

import logging
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from src.settings import app_settings

logger = logging.getLogger(__name__)


class PromptStatus(str, Enum):
    """
    Статус промпта.

    DEV — промпт в разработке, может быть нестабильным
    PROD — проверенный промпт для продакшена
    """

    DEV = "dev"
    PROD = "prod"


class PromptModel(BaseModel):
    """
    Модель одного промпта.

    Используется для валидации структуры промптов при загрузке из YAML.
    Pydantic автоматически проверит, что все обязательные поля присутствуют
    и имеют правильный тип.

    Attributes:
        name: Уникальный идентификатор промпта (например, "system_default")
        version: Версия промпта (например, "1.0", "2.1")
        status: Статус промпта (dev/prod)
        description: Описание назначения промпта
        input_variables: Список переменных для подстановки в шаблон
        template: Текст промпта с плейсхолдерами {variable}

    Example:
        ```python
        prompt = PromptModel(
            name="greeting",
            version="1.0",
            status="prod",
            description="Приветственное сообщение",
            input_variables=["user_name"],
            template="Привет, {user_name}!"
        )
        ```
    """

    name: str = Field(..., min_length=1, description="Уникальное имя промпта")
    version: str = Field(..., pattern=r"^\d+\.\d+$", description="Версия в формате X.Y")
    status: PromptStatus = Field(..., description="Статус: dev или prod")
    description: str = Field(..., description="Описание назначения промпта")
    input_variables: list[str] = Field(
        default_factory=list, description="Переменные для подстановки"
    )
    template: str = Field(..., min_length=1, description="Текст промпта")

    @field_validator("template")
    @classmethod
    def validate_template_variables(cls, template: str, info) -> str:
        """
        Проверяет, что все input_variables присутствуют в template.

        Это защита от опечаток: если указана переменная в input_variables,
        но её нет в template — скорее всего, это ошибка.
        """
        # info.data содержит уже провалидированные поля
        input_vars = info.data.get("input_variables", [])

        for var in input_vars:
            placeholder = f"{{{var}}}"
            if placeholder not in template:
                logger.warning(
                    "Переменная '%s' указана в input_variables, но не найдена в template промпта",
                    var,
                )

        return template


class PromptsFile(BaseModel):
    """
    Модель файла промптов.

    Корневая структура YAML файла с промптами.
    """

    prompts: list[PromptModel]


class PromptNotFoundError(Exception):
    """Промпт не найден по указанным критериям."""

    pass


class PromptService:
    """
    Сервис для работы с промптами.

    Загружает промпты из YAML файла и предоставляет методы для их получения
    с учётом настроек статуса и версии из app_settings.

    Attributes:
        _prompts: Список загруженных промптов
        _prompts_by_key: Словарь для быстрого поиска по (name, version, status)

    Example:
        ```python
        service = PromptService()

        # Получить промпт по имени (версия и статус из настроек)
        prompt = service.get_prompt("system_default")

        # Получить отформатированный промпт с переменными
        text = service.format_prompt("greeting", user_name="Владимир")
        ```
    """

    def __init__(self, prompts_file_path: Path | None = None):
        """
        Инициализация сервиса.

        Args:
            prompts_file_path: Путь к файлу промптов.
                              Если None, используется путь из настроек.

        Raises:
            FileNotFoundError: Файл промптов не найден
            yaml.YAMLError: Ошибка парсинга YAML
            ValidationError: Структура промптов не соответствует схеме
        """
        self._file_path = prompts_file_path or app_settings.PROMPT.file_path
        self._prompts: list[PromptModel] = []
        self._prompts_by_key: dict[tuple[str, str, PromptStatus], PromptModel] = {}

        self._load_prompts()
        logger.info(
            "PromptService инициализирован. Загружено %d промптов из %s",
            len(self._prompts),
            self._file_path,
        )

    def _load_prompts(self) -> None:
        """
        Загружает и валидирует промпты из YAML файла.

        Почему safe_load, а не load:
        - safe_load не выполняет произвольный Python код из YAML
        - Безопаснее для любых входных данных
        - Достаточен для базовых типов (dict, list, str, int, bool)

        Raises:
            FileNotFoundError: Файл не найден
            yaml.YAMLError: Ошибка парсинга YAML
            ValidationError: Ошибка валидации структуры
        """
        logger.debug("Загрузка промптов из файла: %s", self._file_path)

        if not self._file_path.exists():
            raise FileNotFoundError(f"Файл промптов не найден: {self._file_path}")

        with open(self._file_path, encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)

        # Валидация через Pydantic
        prompts_file = PromptsFile(**raw_data)
        self._prompts = prompts_file.prompts

        # Создаём индекс для быстрого поиска
        for prompt in self._prompts:
            key = (prompt.name, prompt.version, prompt.status)
            self._prompts_by_key[key] = prompt

        logger.debug("Загружено промптов: %d", len(self._prompts))

    def get_prompt(
        self,
        name: str,
        version: str | None = None,
        status: PromptStatus | str | None = None,
    ) -> PromptModel:
        """
        Получает промпт по имени.

        Args:
            name: Имя промпта (обязательно)
            version: Версия промпта. Если None — берётся из app_settings.PROMPT.VERSION
            status: Статус промпта. Если None — берётся из app_settings.PROMPT.STATUS

        Returns:
            PromptModel: Найденный промпт

        Raises:
            PromptNotFoundError: Промпт с указанными параметрами не найден

        Example:
            ```python
            # Использует версию и статус из настроек
            prompt = service.get_prompt("system_default")

            # Явно указанные версия и статус
            prompt = service.get_prompt("system_default", version="1.0", status="prod")
            ```
        """
        # Берём значения по умолчанию из настроек
        version = version or app_settings.PROMPT.VERSION
        status_value = status or app_settings.PROMPT.STATUS

        # Преобразуем строку в enum если нужно
        if isinstance(status_value, str):
            status_value = PromptStatus(status_value)

        key = (name, version, status_value)

        if key not in self._prompts_by_key:
            available = self._get_available_versions(name)
            raise PromptNotFoundError(
                f"Промпт '{name}' с version='{version}' и status='{status_value.value}' не найден. "
                f"Доступные варианты для '{name}': {available}"
            )

        return self._prompts_by_key[key]

    def _get_available_versions(self, name: str) -> list[str]:
        """
        Возвращает список доступных версий и статусов для промпта.

        Используется для информативного сообщения об ошибке.
        """
        available = []
        for prompt in self._prompts:
            if prompt.name == name:
                available.append(f"v{prompt.version} ({prompt.status.value})")
        return available if available else ["промпт не существует"]

    def format_prompt(
        self,
        name: str,
        version: str | None = None,
        status: PromptStatus | str | None = None,
        **variables: Any,
    ) -> str:
        """
        Получает промпт и подставляет переменные.

        Args:
            name: Имя промпта
            version: Версия (опционально, по умолчанию из настроек)
            status: Статус (опционально, по умолчанию из настроек)
            **variables: Переменные для подстановки в шаблон

        Returns:
            str: Отформатированный текст промпта

        Raises:
            PromptNotFoundError: Промпт не найден
            KeyError: Не переданы все необходимые переменные

        Example:
            ```python
            text = service.format_prompt(
                "cover_letter",
                vacancy="Python Developer",
                resume="5 лет опыта..."
            )
            ```
        """
        prompt = self.get_prompt(name, version, status)

        # Проверяем, что переданы все необходимые переменные
        missing_vars = set(prompt.input_variables) - set(variables.keys())
        if missing_vars:
            raise KeyError(
                f"Не переданы обязательные переменные для промпта '{name}': {missing_vars}"
            )

        # Форматируем шаблон
        try:
            return prompt.template.format(**variables)
        except KeyError as e:
            raise KeyError(f"Ошибка подстановки переменной в промпт '{name}': {e}") from e

    def list_prompts(
        self,
        status: PromptStatus | str | None = None,
    ) -> list[PromptModel]:
        """
        Возвращает список всех промптов, опционально фильтруя по статусу.

        Args:
            status: Фильтр по статусу. Если None — возвращает все промпты.

        Returns:
            list[PromptModel]: Список промптов

        Example:
            ```python
            # Все промпты
            all_prompts = service.list_prompts()

            # Только продакшен промпты
            prod_prompts = service.list_prompts(status="prod")
            ```
        """
        if status is None:
            return self._prompts.copy()

        if isinstance(status, str):
            status = PromptStatus(status)

        return [p for p in self._prompts if p.status == status]

    def reload(self) -> None:
        """
        Перезагружает промпты из файла.

        Полезно для hot-reload в development режиме.
        В продакшене лучше перезапустить сервис.
        """
        logger.info("Перезагрузка промптов из %s", self._file_path)
        self._prompts.clear()
        self._prompts_by_key.clear()
        self._load_prompts()
