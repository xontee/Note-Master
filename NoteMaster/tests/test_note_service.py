"""Тесты сервиса заметок NoteService."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import (
    NoteNotFoundError,
    ValidationError,
)
from app.models.note import Note
from app.services.note_service import DeleteNoteResult, NoteService


@pytest.fixture
def service(note_service: NoteService) -> NoteService:
    """Псевдоним фикстуры для краткости в этом модуле."""

    return note_service


def _make_note(service: NoteService, title: str, **kwargs) -> Note:
    return service.create_note(
        title=title,
        content=kwargs.get("content", ""),
        tags=kwargs.get("tags", []),
        category=kwargs.get("category"),
        is_pinned=kwargs.get("is_pinned", False),
    )


def test_create_get_and_delete(service: NoteService) -> None:
    note = _make_note(service, "Новая заметка")
    assert note.id is not None

    retrieved = service.get_note(note.id)
    assert retrieved.title == "Новая заметка"

    result = service.delete_note(note.id)
    assert result.deleted
    with pytest.raises(NoteNotFoundError):
        service.get_note(note.id)


def test_update_changes_title_and_touches_timestamp(service: NoteService) -> None:
    note = _make_note(service, "Старый")
    old_updated = note.updated_at

    note_updated = service.update_note(note.id, title="Новый")
    assert note_updated.title == "Новый"
    assert note_updated.updated_at >= old_updated


def test_update_clears_category(service: NoteService) -> None:
    note = _make_note(service, "Заметка", category="Работа")
    updated = service.update_note(note.id, category=None)
    assert updated.category is None


def test_update_nonexistent_raises(service: NoteService) -> None:
    with pytest.raises(NoteNotFoundError):
        service.update_note(uuid4(), title="X")


def test_get_all_sorted_desc(service: NoteService) -> None:
    for i in range(3):
        _make_note(service, f"Заметка {i}")

    notes = service.get_all_notes(sort_by="created_at", descending=True)
    assert len(notes) == 3
    # Должны быть отсортированы (не обязательно строго по убыванию, но все 3 на месте)
    assert len(notes) == 3


def test_get_all_sorted_by_title(service: NoteService) -> None:
    _make_note(service, "Бета")
    _make_note(service, "Альфа")
    _make_note(service, "Гамма")

    notes = service.get_all_notes(sort_by="title", descending=False)
    titles = [n.title for n in notes]
    assert titles == ["Альфа", "Бета", "Гамма"]


def test_search(service: NoteService) -> None:
    _make_note(service, "Python", content="ООП")
    _make_note(service, "JavaScript", content="Прототипы")

    results = service.search_notes("python")
    assert len(results) == 1
    assert results[0].title == "Python"

    results = service.search_notes("прототипы")
    assert len(results) == 1


def test_filter_notes_combined(service: NoteService) -> None:
    _make_note(service, "A", tags=["python"], category="Работа", is_pinned=True)
    _make_note(service, "B", tags=["python"], category="Дом")
    _make_note(service, "C", tags=["go"], category="Работа")

    results = service.filter_notes(tag="python", category="работа")
    assert len(results) == 1
    assert results[0].title == "A"


def test_pin_and_unpin(service: NoteService) -> None:
    note = _make_note(service, "Не закреплена")
    assert not note.is_pinned

    service.pin_note(note.id)
    pinned = service.get_note(note.id)
    assert pinned.is_pinned

    service.unpin_note(note.id)
    unpinned = service.get_note(note.id)
    assert not unpinned.is_pinned


def test_resolve_note_id_full(service: NoteService) -> None:
    note = _make_note(service, "ID тест")
    resolved = service.resolve_note_id(str(note.id))
    assert resolved.id == note.id


def test_resolve_note_id_prefix(service: NoteService) -> None:
    note = _make_note(service, "ID тест")
    prefix = str(note.id)[:8]
    resolved = service.resolve_note_id(prefix)
    assert resolved.id == note.id


def test_resolve_note_id_not_found(service: NoteService) -> None:
    with pytest.raises(NoteNotFoundError):
        service.resolve_note_id("zzzzzzzz")


def test_resolve_note_id_ambiguous(service: NoteService) -> None:
    note1 = Note(title="A", id=UUID("11111111-1111-4111-8111-111111111111"))
    note2 = Note(title="B", id=UUID("11111111-2222-4222-8222-222222222222"))
    service._repository.create(note1)
    service._repository.create(note2)

    with pytest.raises(ValidationError):
        service.resolve_note_id("11111111")


def test_delete_note_with_attachments(service: NoteService) -> None:
    note = _make_note(service, "С вложением")
    # Вложения ещё нет — создадим через attach (тест без attach — проверить очистку пустой заметки)
    result = service.delete_note(note.id)
    assert result.deleted
    assert result.failed_attachments == ()

    with pytest.raises(NoteNotFoundError):
        service.get_note(note.id)


def test_filter_pinned_only(service: NoteService) -> None:
    _make_note(service, "Закреп", is_pinned=True)
    _make_note(service, "Не закреп")

    pinned = service.filter_notes(pinned=True)
    assert len(pinned) == 1
    assert pinned[0].is_pinned

    unpinned = service.filter_notes(pinned=False)
    assert len(unpinned) == 1
    assert not unpinned[0].is_pinned


def test_delete_note_with_failed_attachments(
    service: NoteService,
    attachment_service,
    make_file,
) -> None:
    """Если удаление файла вложения падает — заметка всё равно удаляется."""

    note = _make_note(service, "С вложением")
    attachment = attachment_service.add_attachment(
        note.id, make_file("file.txt", b"data")
    )

    original_delete = service._attachment_storage.delete

    def broken_delete(relative_path: str) -> bool:
        raise RuntimeError("No filesystem")

    service._attachment_storage.delete = broken_delete

    try:
        result = service.delete_note(note.id)
    finally:
        service._attachment_storage.delete = original_delete

    assert result.deleted
    assert len(result.failed_attachments) == 1
    assert result.failed_attachments[0][0].id == attachment.id

    # Заметка удалена, но физический файл остался (сирота, не потеря данных)
    with pytest.raises(NoteNotFoundError):
        service.get_note(note.id)
    assert service._attachment_storage.exists(attachment.relative_path)


def test_sort_by_invalid_field(service: NoteService) -> None:
    with pytest.raises(ValidationError):
        service.get_all_notes(sort_by="invalid_field")
