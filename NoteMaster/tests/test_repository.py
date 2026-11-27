"""Тесты репозитория JsonNoteRepository."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.exceptions import DuplicateNoteError, NoteNotFoundError, SerializationError
from app.models.note import Note
from app.repositories.json_repository import JsonNoteRepository
from app.storage.json_storage import JsonStorage


def test_create_and_get(repository: JsonNoteRepository) -> None:
    note = Note(title="Создан")
    created = repository.create(note)
    assert created.id == note.id
    retrieved = repository.get_by_id(created.id)
    assert retrieved.title == "Создан"


def test_create_duplicate_raises(repository: JsonNoteRepository) -> None:
    note = Note(title="Дубль")
    repository.create(note)
    note2 = Note(title="Дубль", id=note.id)
    with pytest.raises(DuplicateNoteError):
        repository.create(note2)


def test_get_by_id_not_found(repository: JsonNoteRepository) -> None:
    with pytest.raises(NoteNotFoundError):
        repository.get_by_id(uuid4())


def test_get_all_empty(repository: JsonNoteRepository) -> None:
    assert repository.get_all() == []


def test_update_and_persist(repository: JsonNoteRepository) -> None:
    note = Note(title="Оригинал")
    repository.create(note)

    note.update(title="Обновлён")
    repository.update(note)

    updated = repository.get_by_id(note.id)
    assert updated.title == "Обновлён"


def test_update_nonexistent_raises(repository: JsonNoteRepository) -> None:
    note = Note(title="Не существует")
    with pytest.raises(NoteNotFoundError):
        repository.update(note)


def test_delete_and_persist(repository: JsonNoteRepository) -> None:
    note = Note(title="Удалить")
    repository.create(note)
    repository.delete(note.id)

    with pytest.raises(NoteNotFoundError):
        repository.get_by_id(note.id)
    assert repository.get_all() == []


def test_delete_nonexistent_raises(repository: JsonNoteRepository) -> None:
    with pytest.raises(NoteNotFoundError):
        repository.delete(uuid4())


def test_search_title(repository: JsonNoteRepository) -> None:
    repository.create(Note(title="Python"))
    repository.create(Note(title="JavaScript"))
    repository.create(Note(title="SQL"))

    results = repository.search("python")
    assert len(results) == 1
    assert results[0].title == "Python"

    results = repository.search("sql")
    assert len(results) == 1

    results = repository.search("javascript")
    assert len(results) == 1


def test_search_content(repository: JsonNoteRepository) -> None:
    repository.create(Note(title="A", content="SOLID принципы"))
    repository.create(Note(title="B", content="HTML разметка"))

    results = repository.search("solid")
    assert len(results) == 1
    assert results[0].title == "A"


def test_search_tags(repository: JsonNoteRepository) -> None:
    repository.create(Note(title="A", tags=["backend", "api"]))
    repository.create(Note(title="B", tags=["frontend", "css"]))

    results = repository.search("api")
    assert len(results) == 1
    assert results[0].title == "A"


def test_filter_by_tag(repository: JsonNoteRepository) -> None:
    repository.create(Note(title="A", tags=["python"]))
    repository.create(Note(title="B", tags=["python", "java"]))
    repository.create(Note(title="C", tags=["go"]))

    results = repository.filter_by_tag("python")
    assert len(results) == 2


def test_filter_by_category(repository: JsonNoteRepository) -> None:
    repository.create(Note(title="A", category="Работа"))
    repository.create(Note(title="B", category="Работа"))
    repository.create(Note(title="C", category="Дом"))

    results = repository.filter_by_category("работа")
    assert len(results) == 2


def test_get_pinned(repository: JsonNoteRepository) -> None:
    repository.create(Note(title="Закреп", is_pinned=True))
    repository.create(Note(title="Обык"))
    repository.create(Note(title="Закр2", is_pinned=True))

    assert len(repository.get_pinned()) == 2


def test_persistence_across_instances(storage: JsonStorage) -> None:
    Note(title="Первый").id
    note = Note(title="Первый")
    r1 = JsonNoteRepository(storage)
    r1.create(note)

    # Новый репозиторий на том же хранилище
    r2 = JsonNoteRepository(storage)
    results = r2.get_all()
    assert len(results) == 1
    assert results[0].title == "Первый"


def test_corrupted_json_raises_serialization_error(storage: JsonStorage) -> None:
    storage.path.write_text("{{broken", encoding="utf-8")
    repo = JsonNoteRepository(storage)
    with pytest.raises(SerializationError):
        repo.get_all()
