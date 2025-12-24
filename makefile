.PHONY: tests makemigrations migrate run-bot run-web run-all lint lint-check lint-fix format

tests:
	uv run pytest

makemigrations:
	uv run alembic -c src/alembic.ini revision --autogenerate -m "$(comment)"

migrate:
	uv run alembic -c src/alembic.ini upgrade head

run-all:
	docker compose up -d

run-bot:
	docker compose up -d bot

run-web:
	docker compose up -d web

# === Ruff Linting & Formatting ===
# Полная проверка и форматирование (старая команда для совместимости)
run-linter: lint

# Проверить код без изменений
lint-check:
	@echo "🔍 Проверка кода..."
	uv run ruff check .
	@echo "✅ Проверка завершена!"

# Проверить и автоматически исправить
lint-fix:
	@echo "🔧 Исправление ошибок линтера..."
	uv run ruff check --fix .
	@echo "✅ Исправления применены!"

# Форматирование кода
format:
	@echo "🎨 Форматирование кода..."
	uv run ruff format .
	@echo "✅ Форматирование завершено!"

# Полный линтинг: исправить + отформатировать
lint: lint-fix format
	@echo "✨ Код готов к коммиту!"
