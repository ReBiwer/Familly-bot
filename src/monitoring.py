from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator


def setup_monitoring(app: FastAPI) -> None:
    """
    Настройка Prometheus метрик для FastAPI приложения.

    Используем библиотеку prometheus-fastapi-instrumentator для сбора метрик.
    Она автоматически собирает метрики о длительности запросов, статусах ответов и размере данных.
    """
    instrumentator = Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,  # Игнорируем запросы, которые не попали в роутинг (404 и т.д. если не настроено)
        should_instrument_requests_inprogress=True,
        excluded_handlers=[".*admin.*", "/metrics"],  # Исключаем админку и сам эндпоинт метрик
        inprogress_name="inprogress",
        inprogress_labels=True,
    )

    # Инструментируем приложение (добавляем middleware)
    instrumentator.instrument(app)

    # Экспортируем эндпоинт /metrics
    instrumentator.expose(app)
