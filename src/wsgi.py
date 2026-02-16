"""
WSGI-обёртка для запуска FastAPI через Gunicorn (Linux) или Uvicorn (Windows).

Почему два режима:
- Gunicorn использует модуль fcntl и системный вызов fork(),
  которые существуют ТОЛЬКО в Unix (Linux/macOS).
  На Windows он физически не может работать.
- Uvicorn — кроссплатформенный ASGI-сервер, работает везде,
  но не умеет управлять пулом воркеров как Gunicorn.

Поэтому:
- Продакшен (Docker/Linux) → Gunicorn + Uvicorn-воркеры (многопроцессность)
- Разработка (Windows)      → Uvicorn напрямую (один процесс, hot-reload)
"""

import sys

from fastapi import FastAPI


def get_app_options(
    host: str,
    port: int,
    workers: int,
    timeout: int,
    worker_class: str = "uvicorn.workers.UvicornWorker",
) -> dict:
    """Формирует словарь опций для Gunicorn."""
    return {
        "accesslog": "-",
        "errorlog": "-",
        "loglevel": "info",
        "bind": f"{host}:{port}",
        "workers": workers,
        "timeout": timeout,
        "worker_class": worker_class,
    }


def create_gunicorn_app(app: FastAPI, options: dict | None = None):
    """
    Фабрика для создания Gunicorn Application.

    Импорт gunicorn выполняется ЛЕНИВО (внутри функции), а не на уровне модуля.
    Это позволяет безопасно импортировать wsgi.py на Windows —
    ошибка возникнет только при попытке реально создать Gunicorn-приложение.

    Почему класс определён внутри функции:
    BaseApplication из gunicorn нельзя наследовать без импорта gunicorn.
    Если вынести класс на уровень модуля — получим ту же ошибку fcntl на Windows.
    """
    from gunicorn.app.base import BaseApplication

    class _GunicornApp(BaseApplication):
        """
        Обёртка FastAPI приложения для запуска через Gunicorn.

        Gunicorn ожидает WSGI-интерфейс, но благодаря UvicornWorker
        мы получаем полноценный ASGI-сервер с многопроцессностью.
        """

        def __init__(self, app: FastAPI, options: dict | None = None):
            self.options = options or {}
            self.application = app
            super().__init__()

        def load(self):
            return self.application

        @property
        def config_options(self) -> dict:
            return {
                k: v
                for k, v in self.options.items()
                if k in self.cfg.settings and v is not None
            }

        def load_config(self):
            for key, value in self.config_options.items():
                self.cfg.set(key.lower(), value)

    return _GunicornApp(app=app, options=options)


def run_server(
    app: FastAPI,
    host: str,
    port: int,
    workers: int = 4,
    timeout: int = 900,
    log_level: str = "info",
) -> None:
    """
    Универсальный запуск сервера — автоматически выбирает движок по платформе.

    Windows (sys.platform == 'win32'):
        → Uvicorn напрямую. Один процесс, подходит для отладки.

    Linux/macOS:
        → Gunicorn с Uvicorn-воркерами. Многопроцессный продакшен-режим.

    Args:
        app: FastAPI-приложение
        host: Адрес привязки (например '0.0.0.0')
        port: Порт (например 8000)
        workers: Количество Gunicorn-воркеров (игнорируется на Windows)
        timeout: Таймаут воркера в секундах (игнорируется на Windows)
        log_level: Уровень логирования ('debug', 'info', 'warning', 'error')
    """
    if sys.platform == "win32":
        # Windows: Gunicorn недоступен, запускаем uvicorn напрямую.
        # Это однопроцессный режим — идеально для локальной разработки и отладки.
        import uvicorn

        uvicorn.run(app, host=host, port=port, log_level=log_level)
    else:
        # Linux/macOS: Gunicorn с пулом Uvicorn-воркеров.
        # Каждый воркер — отдельный процесс, что даёт настоящую параллельность.
        options = get_app_options(
            host=host, port=port, workers=workers, timeout=timeout
        )
        gunicorn_app = create_gunicorn_app(app=app, options=options)
        gunicorn_app.run()
