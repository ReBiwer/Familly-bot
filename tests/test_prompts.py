"""
Тесты для PromptService.

Проверяют загрузку, валидацию и получение промптов.
"""

from pathlib import Path

import pytest
from src.services.prompts import (
    PromptModel,
    PromptNotFoundError,
    PromptService,
    PromptStatus,
)


class TestPromptModel:
    """Тесты для модели промпта."""

    def test_valid_prompt(self):
        """Создание валидного промпта."""
        prompt = PromptModel(
            name="test",
            version="1.0",
            status="prod",
            description="Test prompt",
            input_variables=[],
            template="Hello world",
        )

        assert prompt.name == "test"
        assert prompt.version == "1.0"
        assert prompt.status == PromptStatus.PROD

    def test_invalid_version_format(self):
        """Ошибка при неверном формате версии."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PromptModel(
                name="test",
                version="1",  # Должно быть "X.Y"
                status="prod",
                description="Test",
                input_variables=[],
                template="Hello",
            )

    def test_invalid_status(self):
        """Ошибка при неверном статусе."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PromptModel(
                name="test",
                version="1.0",
                status="invalid",  # Должно быть dev или prod
                description="Test",
                input_variables=[],
                template="Hello",
            )


class TestPromptService:
    """Тесты для сервиса промптов."""

    def test_load_prompts(self, temp_prompts_file: Path):
        """Успешная загрузка промптов из файла."""
        service = PromptService(prompts_file_path=temp_prompts_file)

        # Проверяем, что промпты загружены
        all_prompts = service.list_prompts()
        assert len(all_prompts) == 6  # 6 промптов в тестовом файле

    def test_get_prompt_by_name(self, temp_prompts_file: Path):
        """Получение промпта по имени."""
        service = PromptService(prompts_file_path=temp_prompts_file)

        prompt = service.get_prompt("test_prompt", version="1.0", status="prod")

        assert prompt.name == "test_prompt"
        assert prompt.template == "Это тестовый промпт"

    def test_get_prompt_not_found(self, temp_prompts_file: Path):
        """Ошибка при несуществующем промпте."""
        service = PromptService(prompts_file_path=temp_prompts_file)

        with pytest.raises(PromptNotFoundError) as exc_info:
            service.get_prompt("nonexistent", version="1.0", status="prod")

        assert "nonexistent" in str(exc_info.value)

    def test_get_prompt_wrong_version(self, temp_prompts_file: Path):
        """Ошибка при неверной версии."""
        service = PromptService(prompts_file_path=temp_prompts_file)

        with pytest.raises(PromptNotFoundError):
            service.get_prompt("test_prompt", version="9.9", status="prod")

    def test_get_prompt_wrong_status(self, temp_prompts_file: Path):
        """Ошибка при неверном статусе."""
        service = PromptService(prompts_file_path=temp_prompts_file)

        with pytest.raises(PromptNotFoundError):
            # test_prompt существует только в prod
            service.get_prompt("test_prompt", version="1.0", status="dev")

    def test_format_prompt_without_vars(self, temp_prompts_file: Path):
        """Форматирование промпта без переменных."""
        service = PromptService(prompts_file_path=temp_prompts_file)

        result = service.format_prompt("test_prompt", version="1.0", status="prod")

        assert result == "Это тестовый промпт"

    def test_format_prompt_with_vars(self, temp_prompts_file: Path):
        """Форматирование промпта с переменными."""
        service = PromptService(prompts_file_path=temp_prompts_file)

        result = service.format_prompt(
            "test_with_vars",
            version="1.0",
            status="prod",
            user_name="Владимир",
            topic="Python",
        )

        assert result == "Привет, Владимир! Тема: Python"

    def test_format_prompt_missing_vars(self, temp_prompts_file: Path):
        """Ошибка при недостающих переменных."""
        service = PromptService(prompts_file_path=temp_prompts_file)

        with pytest.raises(KeyError) as exc_info:
            service.format_prompt(
                "test_with_vars",
                version="1.0",
                status="prod",
                user_name="Владимир",
                # topic не передан!
            )

        assert "topic" in str(exc_info.value)

    def test_list_prompts_all(self, temp_prompts_file: Path):
        """Список всех промптов."""
        service = PromptService(prompts_file_path=temp_prompts_file)

        all_prompts = service.list_prompts()

        assert len(all_prompts) == 6

    def test_list_prompts_by_status(self, temp_prompts_file: Path):
        """Фильтрация промптов по статусу."""
        service = PromptService(prompts_file_path=temp_prompts_file)

        prod_prompts = service.list_prompts(status="prod")
        dev_prompts = service.list_prompts(status="dev")

        assert len(prod_prompts) == 4  # 4 prod промпта
        assert len(dev_prompts) == 2  # 2 dev промпта (system_default и dev_prompt)
        assert all(p.status == PromptStatus.PROD for p in prod_prompts)
        assert all(p.status == PromptStatus.DEV for p in dev_prompts)

    def test_versioned_prompts(self, temp_prompts_file: Path):
        """Получение разных версий одного промпта."""
        service = PromptService(prompts_file_path=temp_prompts_file)

        v1 = service.get_prompt("versioned_prompt", version="1.0", status="prod")
        v2 = service.get_prompt("versioned_prompt", version="2.0", status="prod")

        assert v1.template == "Версия 1.0"
        assert v2.template == "Версия 2.0"

    def test_file_not_found(self, tmp_path: Path):
        """Ошибка при несуществующем файле."""
        fake_path = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            PromptService(prompts_file_path=fake_path)

    def test_reload_prompts(self, temp_prompts_file: Path):
        """Перезагрузка промптов."""
        service = PromptService(prompts_file_path=temp_prompts_file)

        initial_count = len(service.list_prompts())

        # Добавляем новый промпт в файл
        content = temp_prompts_file.read_text()
        content += """
        - name: "new_prompt"
            version: "1.0"
            status: "prod"
            description: "New"
            input_variables: []
            template: "New prompt"
        """
        temp_prompts_file.write_text(content)

        # Перезагружаем
        service.reload()

        assert len(service.list_prompts()) == initial_count + 1
