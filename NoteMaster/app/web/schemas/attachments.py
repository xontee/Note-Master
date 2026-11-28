"""Pydantic-схемы для эндпоинтов вложений.

В ``AttachmentResponse`` намеренно отсутствуют ``relative_path`` и
``stored_filename`` — внутренние пути не покидают сервер. Скачивание
происходит через ссылку ``/api/v1/attachments/{id}/download``.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AttachmentResponse(BaseModel):
    """Метаданные вложения, безопасные для передачи клиенту."""

    id: UUID
    note_id: UUID = Field(..., description="ID заметки-владельца.")
    filename: str
    extension: str
    mime_type: str | None
    size: int
    created_at: datetime
    download_url: str = Field(
        ..., description="Относительный URL для скачивания файла."
    )


class AttachmentListResponse(BaseModel):
    """Список вложений заметки."""

    items: list[AttachmentResponse]
    total: int


__all__ = ["AttachmentResponse", "AttachmentListResponse"]
