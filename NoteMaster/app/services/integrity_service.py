"""Проверка целостности связей «заметка — метаданные — файл»."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.attachment import Attachment
from app.repositories.base import NoteRepository
from app.storage.file_storage import AttachmentStorage


@dataclass(frozen=True, slots=True)
class IntegrityReport:
    """Отчёт о состоянии хранилища."""

    total_notes: int
    total_attachments: int
    missing_files: tuple[Attachment, ...]
    orphan_files: tuple[str, ...]
    size_mismatches: tuple[tuple[Attachment, int], ...]
    duplicate_note_ids: tuple[str, ...]

    @property
    def is_healthy(self) -> bool:
        return not (
            self.missing_files
            or self.orphan_files
            or self.size_mismatches
            or self.duplicate_note_ids
        )

    def summary(self) -> str:
        lines = [
            f"Заметок: {self.total_notes}",
            f"Вложений в метаданных: {self.total_attachments}",
            f"Отсутствующих файлов: {len(self.missing_files)}",
            f"Файлов без метаданных: {len(self.orphan_files)}",
            f"Несовпадений размера: {len(self.size_mismatches)}",
            f"Дубликатов ID заметок: {len(self.duplicate_note_ids)}",
        ]
        return "\n".join(lines)


class IntegrityService:
    """Проверяет согласованность JSON-метаданных и физических файлов."""

    def __init__(
        self,
        repository: NoteRepository,
        storage: AttachmentStorage,
    ) -> None:
        self._repository = repository
        self._storage = storage

    def check(self) -> IntegrityReport:
        notes = self._repository.get_all()

        duplicate_note_ids: list[str] = []
        seen_note_ids: set[str] = set()
        known_paths: set[str] = set()
        missing_files: list[Attachment] = []
        size_mismatches: list[tuple[Attachment, int]] = []
        total_attachments = 0

        for note in notes:
            note_key = str(note.id)
            if note_key in seen_note_ids:
                duplicate_note_ids.append(note_key)
            seen_note_ids.add(note_key)

            for attachment in note.attachments:
                total_attachments += 1
                known_paths.add(attachment.relative_path)

                if not self._storage.exists(attachment.relative_path):
                    missing_files.append(attachment)
                    continue

                try:
                    actual_size = self._storage.get_size(attachment.relative_path)
                except Exception:  # noqa: BLE001 - файл мог исчезнуть между вызовами
                    missing_files.append(attachment)
                    continue
                if actual_size != attachment.size:
                    size_mismatches.append((attachment, actual_size))

        actual_paths = set(self._storage.list_relative_paths())
        orphan_files = tuple(sorted(actual_paths - known_paths))

        return IntegrityReport(
            total_notes=len(notes),
            total_attachments=total_attachments,
            missing_files=tuple(missing_files),
            orphan_files=orphan_files,
            size_mismatches=tuple(size_mismatches),
            duplicate_note_ids=tuple(duplicate_note_ids),
        )


__all__ = ["IntegrityReport", "IntegrityService"]
