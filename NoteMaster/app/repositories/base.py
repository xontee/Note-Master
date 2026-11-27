"""Абстрактный интерфейс репозитория заметок."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.core.exceptions import NoteNotFoundError
from app.models.note import Note


class NoteRepository(ABC):
    """Контракт хранилища заметок.

    Реализации (JSON, SQLite, PostgreSQL) обязаны следовать этому интерфейсу,
    чтобы :class:`NoteService` не зависел от конкретной технологии хранения.
    """

    @abstractmethod
    def create(self, note: Note) -> Note:
        """Сохраняет новую заметку."""

    @abstractmethod
    def get_by_id(self, note_id: UUID) -> Note:
        """Возвращает заметку по идентификатору."""

    @abstractmethod
    def get_all(self) -> list[Note]:
        """Возвращает все заметки."""

    @abstractmethod
    def update(self, note: Note) -> Note:
        """Сохраняет изменения существующей заметки."""

    @abstractmethod
    def delete(self, note_id: UUID) -> None:
        """Удаляет заметку по идентификатору."""

    @abstractmethod
    def search(self, query: str) -> list[Note]:
        """Ищет заметки по подстроке (без учёта регистра)."""

    @abstractmethod
    def filter_by_tag(self, tag: str) -> list[Note]:
        """Возвращает заметки с указанным тегом."""

    @abstractmethod
    def filter_by_category(self, category: str) -> list[Note]:
        """Возвращает заметки указанной категории."""

    @abstractmethod
    def get_pinned(self) -> list[Note]:
        """Возвращает закреплённые заметки."""

    def exists(self, note_id: UUID) -> bool:
        """Проверяет наличие заметки (реализация по умолчанию)."""

        try:
            self.get_by_id(note_id)
        except NoteNotFoundError:
            return False
        return True


__all__ = ["NoteRepository"]
