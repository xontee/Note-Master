"""Тесты моделей Note и Attachment."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import ValidationError
from app.models.attachment import Attachment
from app.models.note import Note


def test_note_defaults() -> None:
    note = Note(title="  Заголовок  ")
    assert note.title == "Заголовок"
    assert note.content == ""
    assert note.tags == []
    assert note.category is None
    assert note.is_pinned is False
    assert note.attachments == []
    assert isinstance(note.id, UUID)
    assert note.created_at.tzinfo is not None
    assert note.updated_at >= note.created_at


def test_note_empty_title_rejected() -> None:
    with pytest.raises(ValidationError):
        Note(title="   ")


def test_note_non_string_title_rejected() -> None:
    with pytest.raises(ValidationError):
        Note(title=123)  # type: ignore[arg-type]


def test_note_too_long_title_rejected() -> None:
    with pytest.raises(ValidationError):
        Note(title="x" * 201)


def test_note_content_may_be_empty() -> None:
    note = Note(title="Заметка", content="")
    assert note.content == ""


def test_note_tags_normalized() -> None:
    note = Note(title="Заметка", tags=[" Python ", "python", "SQL", ""])
    assert note.tags == ["Python", "SQL"]


def test_note_category_normalized() -> None:
    note = Note(title="Заметка", category="  Работа ")
    assert note.category == "Работа"
    assert Note(title="Заметка", category="   ").category is None


def test_note_update_touches_timestamp() -> None:
    old = datetime(2020, 1, 1, tzinfo=timezone.utc)
    note = Note(title="Старое", created_at=old, updated_at=old)
    note.update(title="Новое")
    assert note.title == "Новое"
    assert note.updated_at > old


def test_note_update_can_clear_category() -> None:
    note = Note(title="Заметка", category="Работа")
    note.update(category=None)
    assert note.category is None


def test_note_serialization_roundtrip() -> None:
    attachment = Attachment(
        filename="file.txt",
        relative_path="2024/01/abc/file.txt",
        extension=".txt",
        size=10,
        mime_type="text/plain",
    )
    note = Note(
        title="Заголовок",
        content="Содержимое",
        tags=["a", "b"],
        category="Работа",
        is_pinned=True,
        attachments=[attachment],
    )

    restored = Note.from_dict(note.to_dict())
    assert restored.id == note.id
    assert restored.title == note.title
    assert restored.tags == note.tags
    assert restored.attachments[0].id == attachment.id
    assert restored.created_at == note.created_at


def test_note_from_dict_missing_field() -> None:
    with pytest.raises(ValidationError):
        Note.from_dict({"id": str(uuid4()), "title": "x"})


def test_note_from_dict_invalid_id() -> None:
    payload = Note(title="x").to_dict()
    payload["id"] = "not-a-uuid"
    with pytest.raises(ValidationError):
        Note.from_dict(payload)


def test_note_matches_case_insensitive() -> None:
    note = Note(
        title="Python Notes",
        content="Про SOLID и архитектуру",
        tags=["Backend"],
        category="Работа",
    )
    assert note.matches("python")
    assert note.matches("solid")
    assert note.matches("backend")
    assert note.matches("работа")
    assert not note.matches("javascript")
    assert note.matches("")


def test_note_has_tag_and_category_case_insensitive() -> None:
    note = Note(title="x", tags=["Python"], category="Работа")
    assert note.has_tag("python")
    assert note.in_category("работа")
    assert not note.has_tag("java")


def test_attachment_defaults_and_serialization() -> None:
    attachment = Attachment(
        filename="report.pdf",
        relative_path="2024/05/note/att.pdf",
        extension="PDF",
        size=123,
    )
    assert attachment.extension == ".pdf"
    assert attachment.stored_filename == "att.pdf"
    assert isinstance(attachment.id, UUID)

    restored = Attachment.from_dict(attachment.to_dict())
    assert restored.id == attachment.id
    assert restored.filename == "report.pdf"
    assert restored.size == 123


def test_attachment_rejects_unsafe_filename() -> None:
    with pytest.raises(ValidationError):
        Attachment(
            filename="../evil.txt",
            relative_path="x/y",
            extension=".txt",
            size=1,
        )


def test_attachment_rejects_negative_size() -> None:
    with pytest.raises(ValidationError):
        Attachment(
            filename="a.txt",
            relative_path="a.txt",
            extension=".txt",
            size=-1,
        )


def test_attachment_naive_datetime_becomes_aware() -> None:
    naive = datetime(2024, 1, 1, 12, 0, 0)
    attachment = Attachment(
        filename="a.txt",
        relative_path="a.txt",
        extension=".txt",
        size=1,
        created_at=naive,
    )
    assert attachment.created_at.tzinfo is not None


def test_note_updated_at_not_before_created_at() -> None:
    created = datetime(2024, 1, 2, tzinfo=timezone.utc)
    note = Note(
        title="x",
        created_at=created,
        updated_at=created - timedelta(days=1),
    )
    assert note.updated_at == created
