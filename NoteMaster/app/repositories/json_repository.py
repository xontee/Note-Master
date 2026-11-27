"""JSON-реализация репозитория заметок."""

from __future__ import annotations

import threading
from typing import Any
from uuid import UUID

from app.core.exceptions import (
    DuplicateNoteError,
    NoteNotFoundError,
    SerializationError,
    StorageError,
    ValidationError,
)
from app.models.note import Note
from app.repositories.base import NoteRepository
from app.storage.json_storage import JSON_SCHEMA_VERSION, JsonStorage


class JsonNoteRepository(NoteRepository):
    """Репозиторий, хранящий заметки в JSON-документе.

    Управляет структурой данных (список заметок + метаданные вложений) и
    делегирует физическое чтение/запись :class:`JsonStorage`.
    """

    def __init__(self, storage: JsonStorage) -> None:
        self._storage = storage
        self._lock = threading.RLock()

    @property
    def storage(self) -> JsonStorage:
        return self._storage

    # ---------------------------------------------------------------- CRUD
    def create(self, note: Note) -> Note:
        if not isinstance(note, Note):
            raise ValidationError("create() expects a Note instance")

        with self._lock:
            notes = self._load()
            if any(existing.id == note.id for existing in notes):
                raise DuplicateNoteError(f"Note with id {note.id} already exists")
            notes.append(note)
            self._save(notes)
            return note

    def get_by_id(self, note_id: UUID) -> Note:
        identifier = self._coerce_uuid(note_id)
        with self._lock:
            for note in self._load():
                if note.id == identifier:
                    return note
        raise NoteNotFoundError(f"Note not found: {identifier}")

    def get_all(self) -> list[Note]:
        with self._lock:
            return self._load()

    def update(self, note: Note) -> Note:
        if not isinstance(note, Note):
            raise ValidationError("update() expects a Note instance")

        with self._lock:
            notes = self._load()
            for index, existing in enumerate(notes):
                if existing.id == note.id:
                    notes[index] = note
                    self._save(notes)
                    return note
        raise NoteNotFoundError(f"Note not found: {note.id}")

    def delete(self, note_id: UUID) -> None:
        identifier = self._coerce_uuid(note_id)
        with self._lock:
            notes = self._load()
            remaining = [note for note in notes if note.id != identifier]
            if len(remaining) == len(notes):
                raise NoteNotFoundError(f"Note not found: {identifier}")
            self._save(remaining)

    # ------------------------------------------------------- поиск/фильтры
    def search(self, query: str) -> list[Note]:
        with self._lock:
            return [note for note in self._load() if note.matches(query)]

    def filter_by_tag(self, tag: str) -> list[Note]:
        with self._lock:
            return [note for note in self._load() if note.has_tag(tag)]

    def filter_by_category(self, category: str) -> list[Note]:
        with self._lock:
            return [note for note in self._load() if note.in_category(category)]

    def get_pinned(self) -> list[Note]:
        with self._lock:
            return [note for note in self._load() if note.is_pinned]

    # -------------------------------------------------------------- helpers
    def _load(self) -> list[Note]:
        payload = self._storage.read()
        raw_notes = payload.get("notes", [])
        if not isinstance(raw_notes, list):
            raise SerializationError("Storage payload 'notes' must be a list")

        notes: list[Note] = []
        for index, raw in enumerate(raw_notes):
            try:
                notes.append(Note.from_dict(raw))
            except ValidationError as exc:
                raise SerializationError(
                    f"Invalid note at index {index}: {exc}"
                ) from exc
        return notes

    def _save(self, notes: list[Note]) -> None:
        payload: dict[str, Any] = {
            "version": JSON_SCHEMA_VERSION,
            "notes": [note.to_dict() for note in notes],
        }
        self._storage.write(payload)

    @staticmethod
    def _coerce_uuid(value: object) -> UUID:
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValidationError(f"Invalid note id: {value!r}") from exc


__all__ = ["JsonNoteRepository"]
