"""Контейнер зависимостей Web-слоя.

Аналог композиционного корня CLI (:func:`app.main.build_application`), но без
сборки CLI-объекта: Web собирает только Core-сервисы. Это сохраняет правило
«интерфейсы не тянут друг друга» и позволяет FastAPI получать готовые сервисы
через :mod:`app.web.dependencies`.

Порядок сборки повторяет доменный граф зависимостей::

    WebConfig
       ├── JsonStorage -> JsonNoteRepository
       ├── LocalAttachmentStorage
       ├── NoteService(repository, attachment_storage)
       ├── AttachmentService(repository, attachment_storage, config)
       └── IntegrityService(repository, attachment_storage)
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Config
from app.repositories.json_repository import JsonNoteRepository
from app.services.attachment_service import AttachmentService
from app.services.integrity_service import IntegrityService
from app.services.note_service import NoteService
from app.storage.file_storage import LocalAttachmentStorage
from app.storage.json_storage import JsonStorage
from app.web.config import WebConfig


@dataclass(slots=True)
class Container:
    """Готовые зависимости для HTTP-обработчиков.

    Хранит и доменный :class:`Config`, и :class:`WebConfig`, и все сервисы.
    Экземпляр создаётся один раз за жизненный цикл приложения и живёт в
    ``app.state``.
    """

    web_config: WebConfig
    config: Config
    storage: JsonStorage
    repository: JsonNoteRepository
    attachment_storage: LocalAttachmentStorage
    note_service: NoteService
    attachment_service: AttachmentService
    integrity_service: IntegrityService


def build_container(web_config: WebConfig) -> Container:
    """Создаёт и инициализирует все зависимости для одного запуска сервера."""

    config = web_config.core

    storage = JsonStorage(config.notes_file, encoding=config.encoding)
    storage.ensure_initialized()
    repository = JsonNoteRepository(storage)
    attachment_storage = LocalAttachmentStorage(config.attachments_dir)

    note_service = NoteService(repository, attachment_storage)
    attachment_service = AttachmentService(repository, attachment_storage, config)
    integrity_service = IntegrityService(repository, attachment_storage)

    return Container(
        web_config=web_config,
        config=config,
        storage=storage,
        repository=repository,
        attachment_storage=attachment_storage,
        note_service=note_service,
        attachment_service=attachment_service,
        integrity_service=integrity_service,
    )


__all__ = ["Container", "build_container"]
