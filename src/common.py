"""
Модуль с обшими настройками проекта. Пока тут только настройка логирования
"""

import logging
import logging.config
from pathlib import Path

PATH_LOGS = Path(__file__).resolve().parent / "logs"


def setup_logging(root_log_level: str | int = logging.INFO, log_dir: Path = PATH_LOGS):
    """
    Инициализация настроек логгеров и форматирования
    """
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(levelname)-8s] %(name)40s:%(lineno)-3d - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": root_log_level,
                "formatter": "default",
            },
            "console_stdout": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",  # Вывод не в stderr, а в stdout
                "level": root_log_level,
                "formatter": "default",
            },
            "general_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": log_dir / "app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "formatter": "default",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": log_dir / "errors.log",
                "maxBytes": 10485760,
                "backupCount": 5,
                "level": "ERROR",
                "formatter": "default",
            },
        },
        "loggers": {
            "root": {
                "level": root_log_level,
                "handlers": ["console_stdout", "general_file", "error_file"],
            },
            "asyncio": {"level": "WARNING"},
            "urllib3": {"level": "WARNING"},
            "httpx": {"level": "WARNING"},
            "httpcore": {"level": "WARNING"},
            "langgraph": {"level": "WARNING"},
            
            # Перехватываем логи Uvicorn (сервера FastAPI)
            "uvicorn": {
                "handlers": ["console_stdout", "general_file", "error_file"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": [],
                "level": "INFO",
                "propagate": True,
            },
            "uvicorn.access": {
                "handlers": [],
                "level": "INFO",
                "propagate": True,
            },
        },
    }

    logging.config.dictConfig(config)
    logging.info("Logging configured with dictConfig")
