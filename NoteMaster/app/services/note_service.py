"""Бизнес-логика работы с заметками."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.exceptions import (
    NoteNotFoundError,
    ValidationError,
)
from app.models.note import UNSET, Note
from app.repositories.base import NoteRepository
from app.storage.file_storage import AttachmentStorage

_SORT_FIELDS = frozenset({"created_at", "updated_at", "title"})


@dataclass(frozen=True, slots=True)
class DeleteNoteResult:
    """Результат удаления заметки.

    ``failed_attachments`` содержит пары «вложение — причина», если файл не
    удалось удалить после удаления записи. Заметка при этом уже удалена, а
    оставшиеся файлы являются «сиротами» и могут быть найдены проверкой
    целостности.
    """

    note_id: UUID
    deleted: bool
    failed_attachments: tuple[tuple[Any, str], ...] = ()


class NoteService:
    """Сервис CRUD, поиска и фильтрации заметок.

    Зависит только от абстракций :class:`NoteRepository` и
    :class:`AttachmentStorage`, поэтому JSON можно заменить на SQLite без
    изменения этого класса.
    """

    def __init__(
        self,
        repository: NoteRepository,
        attachment_storage: AttachmentStorage | None = None,
    ) -> None:
        self._repository = repository
        self._attachment_storage = attachment_storage

    # ------------------------------------------------------------------ CRUD
    def create_note(
        self,
        title: str,
        content: str = "",
        tags: list[str] | str | None = None,
        category: str | None = None,
        is_pinned: bool = False,
    ) -> Note:
        note = Note(
            title=title,
            content=content,
            tags=tags or [],
            category=category,
            is_pinned=is_pinned,
        )
        return self._repository.create(note)

    def get_note(self, note_id: UUID | str) -> Note:
        return self._repository.get_by_id(self._coerce_uuid(note_id))

    def get_all_notes(
        self,
        sort_by: str | None = None,
        descending: bool = False,
    ) -> list[Note]:
        return self._sort(self._repository.get_all(), sort_by, descending)

    def update_note(
        self,
        note_id: UUID | str,
        *,
        title: Any = UNSET,
        content: Any = UNSET,
        tags: Any = UNSET,
        category: Any = UNSET,
        is_pinned: Any = UNSET,
    ) -> Note:
        note = self.get_note(note_id)
        note.update(
            title=title,
            content=content,
            tags=tags,
            category=category,
            is_pinned=is_pinned,
        )
        return self._repository.update(note)

    def delete_note(
        self,
        note_id: UUID | str,
        *,
        remove_attachments: bool = True,
    ) -> DeleteNoteResult:
        """Удаляет заметку и (по умолчанию) её физические вложения.

        Сначала атомарно удаляется запись из репозитория, затем выполняется
        best-effort очистка файлов. Сбои очистки не скрываются: они
        возвращаются в :class:`DeleteNoteResult`.
        """

        note = self.get_note(note_id)
        attachments = list(note.attachments)
        self._repository.delete(note.id)

        failures: list[tuple[Any, str]] = []
        if remove_attachments and self._attachment_storage is not None:
            for attachment in attachments:
                try:
                    self._attachment_storage.delete(attachment.relative_path)
                except (
                    Exception
                ) as exc:  # noqa: BLE001 - причина возвращается вызывающему
                    failures.append((attachment, str(exc)))

        return DeleteNoteResult(
            note_id=note.id,
            deleted=True,
            failed_attachments=tuple(failures),
        )

    # ------------------------------------------------------- поиск/фильтры
    def search_notes(
        self,
        query: str,
        sort_by: str | None = None,
        descending: bool = False,
    ) -> list[Note]:
        return self._sort(self._repository.search(query), sort_by, descending)

    def filter_notes(
        self,
        *,
        query: str | None = None,
        tag: str | None = None,
        category: str | None = None,
        pinned: bool | None = None,
        sort_by: str | None = None,
        descending: bool = False,
    ) -> list[Note]:
        notes = self._repository.get_all()

        if query:
            notes = [note for note in notes if note.matches(query)]
        if tag:
            notes = [note for note in notes if note.has_tag(tag)]
        if category:
            notes = [note for note in notes if note.in_category(category)]
        if pinned is not None:
            notes = [note for note in notes if note.is_pinned == pinned]

        return self._sort(notes, sort_by, descending)

    def pin_note(self, note_id: UUID | str) -> Note:
        return self.update_note(note_id, is_pinned=True)

    def unpin_note(self, note_id: UUID | str) -> Note:
        return self.update_note(note_id, is_pinned=False)

    # ------------------------------------------------------------ утилиты
    def resolve_note_id(self, prefix: str) -> Note:
        """Находит заметку по полному ID или однозначному префиксу."""

        if not isinstance(prefix, str) or not prefix.strip():
            raise ValidationError("Идентификатор заметки не может быть пустым")

        raw = prefix.strip().lower()
        compact = raw.replace("-", "")

        matches: list[Note] = []
        for note in self._repository.get_all():
            note_id = str(note.id).lower()
            if note_id.startswith(raw) or note_id.replace("-", "").startswith(compact):
                matches.append(note)

        if not matches:
            raise NoteNotFoundError(f"Заметка не найдена: {prefix}")
        if len(matches) > 1:
            raise ValidationError(
                f"Неоднозначный префикс ID '{prefix}': найдено {len(matches)} заметок. "
                "Введите больше символов ID."
            )
        return matches[0]

    def _sort(
        self,
        notes: list[Note],
        sort_by: str | None,
        descending: bool,
    ) -> list[Note]:
        if sort_by is None:
            return notes
        if sort_by not in _SORT_FIELDS:
            raise ValidationError(
                f"Unsupported sort field '{sort_by}'. "
                f"Allowed: {', '.join(sorted(_SORT_FIELDS))}"
            )

        if sort_by == "title":
            key = lambda note: note.title.casefold()  # noqa: E731
        else:
            key = lambda note: getattr(note, sort_by)  # noqa: E731

        return sorted(notes, key=key, reverse=descending)

    @staticmethod
    def _coerce_uuid(value: object) -> UUID:
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValidationError(f"Invalid note id: {value!r}") from exc


__all__ = ["NoteService", "DeleteNoteResult"]
