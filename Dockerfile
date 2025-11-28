# syntax=docker/dockerfile:1

###############################################################################
# Базовый stage с установкой uv и зависимостей проекта
###############################################################################
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Системные зависимости, необходимые для сборки колеса asyncpg и других пакетов
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем uv из официального образа
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Копируем файлы зависимостей отдельно для улучшения кеширования
COPY pyproject.toml uv.lock ./

# Синхронизируем зависимости без установки самого проекта (репозитория ещё нет)
RUN uv sync --frozen --no-dev --no-install-project --compile-bytecode

# Копируем исходный код и связанные артефакты
COPY source ./source
COPY alembic.ini ./alembic.ini
COPY README.md ./README.md

# Устанавливаем проект (появится исполняемый модуль source.* в .venv)
RUN uv sync --frozen --no-dev --compile-bytecode

###############################################################################
# Общая рантайм-база: только необходимые системные библиотеки и готовое venv
###############################################################################
FROM python:3.12-slim AS runtime-base

ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Минимальный набор системных библиотек, необходимых во время исполнения
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Переносим установленное приложение и виртуальное окружение из builder stage
COPY --from=builder /app /app

# Копируем скрипт entrypoint
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

###############################################################################
# Финальный образ для развёртывания веб-приложения (FastAPI + Gunicorn)
###############################################################################
FROM runtime-base AS web

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "-m", "source.main", "--type-app", "web"]

###############################################################################
# Финальный образ для Telegram-бота (aiogram)
###############################################################################
FROM runtime-base AS bot

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "-m", "source.main", "--type-app", "telegram"]
