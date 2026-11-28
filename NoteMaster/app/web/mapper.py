"""Чистые функции маппинга Core-моделей в DTO-ответы.

Не используются Pydantic-модели напрямую — это гарантирует, что
внутренняя структура Core (например, ``relative_path``) не протекает
в HTTP-ответ.
"""

from __future__ import annotations

from app.models.note import Note
from app.web.schemas.notes import AttachmentSummary, NoteResponse


def note_to_response(note: Note) -> NoteResponse:
    """Преобразует Core-модель Note в HTTP-ответ."""

    return NoteResponse(
        id=note.id,
        title=note.title,
        content=note.content,
        tags=list(note.tags),
        category=note.category,
        is_pinned=note.is_pinned,
        created_at=note.created_at,
        updated_at=note.updated_at,
        attachments=[
            AttachmentSummary(
                id=a.id,
                filename=a.filename,
                extension=a.extension,
                mime_type=a.mime_type,
                size=a.size,
                created_at=a.created_at,
            )
            for a in note.attachments
        ],
    )


__all__ = ["note_to_response"]
