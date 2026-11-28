"""Pydantic-схемы для эндпоинтов заметок.

Схемы — это HTTP-контракт. Они не наследуют Core-модели и не знают о JSON.
Маппинг Core Note → NoteResponse выполняется в роутах через чистую функцию,
чтобы API-контракт оставался стабильным при изменении внутренней модели.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ─────────────────────────────────────────────────────────────── Запросы ─────


class NoteCreateRequest(BaseModel):
    """Тело POST /notes — создание новой заметки."""

    title: str = Field(..., min_length=1, max_length=200, description="Заголовок заметки.")
    content: str = Field("", description="Текст заметки.")
    tags: list[str] = Field(default_factory=list, description="Список тегов.")
    category: str | None = Field(None, description="Категория.")
    is_pinned: bool = Field(False, description="Закреплена ли заметка.")


class NoteUpdateRequest(BaseModel):
    """Тело PUT /notes/{id} — частичное обновление.

    Поля, не присутствующие в запросе (``exclude_unset``), не передаются в
    сервис — это сохраняет семантику сентинела ``UNSET`` из Core.
    Явный ``null`` для ``category`` очищает категорию.
    """

    title: str | None = Field(None, min_length=1, max_length=200)
    content: str | None = None
    tags: list[str] | None = None
    category: str | None = None
    is_pinned: bool | None = None

    model_config = ConfigDict(json_schema_extra={"example": {"title": "Обновлённый заголовок"}})


class PinRequest(BaseModel):
    """Тело PATCH /notes/{id}/pin."""

    is_pinned: bool


# ─────────────────────────────────────────────────────────────── Ответы ──────


class AttachmentSummary(BaseModel):
    """Краткая сводка вложения внутри ответа заметки (без тела)."""

    id: UUID
    filename: str
    extension: str
    mime_type: str | None
    size: int
    created_at: datetime


class NoteResponse(BaseModel):
    """Полный ответ заметки в HTTP API.

    Не содержит внутренних полей (relative_path, stored_filename).
    UUID и datetime сериализуются Pydantic стандартно: str / ISO-8601.
    """

    id: UUID
    title: str
    content: str
    tags: list[str]
    category: str | None
    is_pinned: bool
    created_at: datetime
    updated_at: datetime
    attachments: list[AttachmentSummary] = Field(default_factory=list)


class NoteListResponse(BaseModel):
    """Коллекционный ответ с пагинацией."""

    items: list[NoteResponse]
    total: int
    limit: int | None
    offset: int


__all__ = [
    "NoteCreateRequest",
    "NoteUpdateRequest",
    "PinRequest",
    "AttachmentSummary",
    "NoteResponse",
    "NoteListResponse",
]
