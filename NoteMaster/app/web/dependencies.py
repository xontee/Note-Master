"""Провайдеры зависимостей FastAPI.

Сервисы не создаются в каждом эндпоинте: они берутся из единого
:class:`~app.web.container.Container`, который кладётся в ``app.state`` на
старте приложения (lifespan). Эндпоинт получает нужный сервис через ``Depends``.

Такая прослойка даёт два преимущества:

* эндпоинты не знают, откуда берутся сервисы (контейнер, кэш, пул);
* в тестах достаточно переопределить провайдер через
  ``app.dependency_overrides[get_note_service] = ...`` — и реальный Container
  не понадобится вовсе.
"""

from __future__ import annotations

from fastapi import Request

from app.services.attachment_service import AttachmentService
from app.services.integrity_service import IntegrityService
from app.services.note_service import NoteService
from app.web.config import WebConfig
from app.web.container import Container


def get_container(request: Request) -> Container:
    """Возвращает контейнер, созданный на старте приложения."""

    container = getattr(request.app.state, "container", None)
    if container is None:  # pragma: no cover - защита от запуска без lifespan
        raise RuntimeError("Application container is not initialized")
    return container


def get_note_service(request: Request) -> NoteService:
    return get_container(request).note_service


def get_attachment_service(request: Request) -> AttachmentService:
    return get_container(request).attachment_service


def get_integrity_service(request: Request) -> IntegrityService:
    return get_container(request).integrity_service


def get_web_config(request: Request) -> WebConfig:
    return get_container(request).web_config


__all__ = [
    "get_container",
    "get_note_service",
    "get_attachment_service",
    "get_integrity_service",
    "get_web_config",
]
