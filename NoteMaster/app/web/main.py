"""Фабрика FastAPI-приложения NoteMaster Web.

Здесь собираются HTTP-слой и Core:

* :func:`create_app` строит ``FastAPI`` c метаданными OpenAPI;
* lifespan создаёт :class:`~app.web.container.Container` один раз за запуск и
  кладёт его в ``app.state`` (жизненный цикл сервиса = жизненный цикл сервера);
* подключаются ограниченный CORS и централизованные обработчики ошибок;
* монтируется версионированный роутер ``/api/v1``.

Функция принимает готовый ``container`` — это точка подмены для тестов:
API-тесты строят контейнер на временном каталоге и не трогают данные
пользователя.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.web.api.router import api_router
from app.web.config import WebConfig
from app.web.container import Container, build_container
from app.web.exceptions.handlers import register_exception_handlers


def create_app(
    web_config: WebConfig | None = None,
    container: Container | None = None,
) -> FastAPI:
    """Создаёт настроенное приложение FastAPI.

    :param web_config: HTTP-настройки; по умолчанию читаются из окружения.
    :param container: готовый контейнер зависимостей; если не передан —
        собирается в lifespan из ``web_config``.
    """

    config = web_config or WebConfig.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = container or build_container(config)
        yield

    app = FastAPI(
        title="NoteMaster Web API",
        version=__version__,
        description=(
            "REST API персональной системы знаний NoteMaster. "
            "Локальный однопользовательский интерфейс над единым Core."
        ),
        lifespan=lifespan,
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
    )

    # CORS ограничен адресами фронтенда: локальный single-user интерфейс не
    # должен принимать произвольные кросс-доменные запросы.
    if config.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(config.cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=config.api_prefix)

    # Экспортируем конфигурацию на app.state для диагностических целей.
    app.state.web_config = config
    return app


def app_factory() -> FastAPI:
    """Zero-arg фабрика для ``uvicorn(factory=True)``.

    Читает конфигурацию из окружения в момент запуска воркера, а не импорта,
    поэтому настройки не «замораживаются» при сборке пакета.
    """

    return create_app()


__all__ = ["create_app", "app_factory"]
