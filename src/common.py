import logging
import logging.config
from pathlib import Path

PATH_LOGS = f"{Path(__file__).resolve().parent}/logs"


def setup_logging(root_log_level: str | int = logging.INFO, log_dir: str = PATH_LOGS):
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
                "filename": f"{log_dir}/app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "formatter": "default",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": f"{log_dir}/errors.log",
                "maxBytes": 10485760,
                "backupCount": 5,
                "level": "ERROR",
                "formatter": "default",
            },
        },
        "loggers": {
            "urllib3": {"level": "WARNING"},
            "httpx": {"level": "WARNING"},
        },
        "root": {
            "level": root_log_level,
            "handlers": ["console_stdout", "general_file", "error_file"],
        },
    }

    logging.config.dictConfig(config)
    logging.info("Logging configured with dictConfig")
