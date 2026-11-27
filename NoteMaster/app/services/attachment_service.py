"""Бизнес-логика управления файловыми вложениями."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from app.attachments.validators import ValidatedAttachment, validate_attachment_file
from app.core.config import Config
from app.core.exceptions import (
    AttachmentLimitExceededError,
    AttachmentNotFoundError,
    AttachmentStorageError,
    NoteNotFoundError,
    ValidationError,
)
from app.models.attachment import Attachment
from app.models.note import Note
from app.repositories.base import NoteRepository
from app.storage.file_storage import AttachmentStorage


class AttachmentService:
    """Сервис добавления, чтения, удаления и экспорта вложений."""

    def __init__(
        self,
        repository: NoteRepository,
        storage: AttachmentStorage,
        config: Config,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._config = config

    # -------------------------------------------------------------- добавление
    def add_attachment(self, note_id: UUID | str, file_path: str | Path) -> Attachment:
        """Добавляет файл к заметке.

        Порядок операций защищает от «сирот»: сначала валидируется файл,
        затем он копируется в хранилище, затем сохраняются метаданные. Если
        сохранение метаданных не удалось, скопированный файл удаляется.
        """

        note = self._repository.get_by_id(self._coerce_uuid(note_id))

        if len(note.attachments) >= self._config.max_attachments_per_note:
            raise AttachmentLimitExceededError(
                "Attachment limit exceeded: "
                f"{len(note.attachments)}/{self._config.max_attachments_per_note}"
            )

        validated = validate_attachment_file(file_path, self._config)

        attachment_id = uuid4()
        relative_path = self._storage.save(
            validated.path,
            note.id,
            attachment_id,
            validated.extension,
        )

        attachment = Attachment(
            id=attachment_id,
            filename=validated.filename,
            stored_filename=Path(relative_path).name,
            relative_path=relative_path,
            mime_type=validated.mime_type,
            extension=validated.extension,
            size=validated.size,
        )

        note.attachments.append(attachment)
        note.touch()

        try:
            self._repository.update(note)
        except Exception:
            # Компенсация: не оставляем незарегистрированный файл в хранилище.
            try:
                self._storage.delete(relative_path)
            except AttachmentStorageError:
                pass
            raise

        return attachment

    # ------------------------------------------------------------------ чтение
    def get_attachment(
        self,
        note_id: UUID | str,
        attachment_id: UUID | str,
    ) -> Attachment:
        note = self._repository.get_by_id(self._coerce_uuid(note_id))
        return self._find_attachment(note, attachment_id)

    def list_attachments(self, note_id: UUID | str) -> list[Attachment]:
        note = self._repository.get_by_id(self._coerce_uuid(note_id))
        return list(note.attachments)

    def attachment_exists(
        self,
        note_id: UUID | str,
        attachment_id: UUID | str,
    ) -> bool:
        try:
            self.get_attachment(note_id, attachment_id)
        except (NoteNotFoundError, AttachmentNotFoundError, ValidationError):
            return False
        return True

    def validate_attachment(self, file_path: str | Path) -> ValidatedAttachment:
        return validate_attachment_file(file_path, self._config)

    # --------------------------------------------------------------- удаление
    def remove_attachment(
        self,
        note_id: UUID | str,
        attachment_id: UUID | str,
    ) -> Attachment:
        """Удаляет вложение: сначала файл, затем метаданные.

        Если физический файл уже отсутствует, удаление метаданных всё равно
        выполняется — это позволяет восстановить консистентность.
        """

        note = self._repository.get_by_id(self._coerce_uuid(note_id))
        attachment = self._find_attachment(note, attachment_id)

        if self._storage.exists(attachment.relative_path):
            self._storage.delete(attachment.relative_path)

        note.attachments = [
            item for item in note.attachments if item.id != attachment.id
        ]
        note.touch()
        self._repository.update(note)
        return attachment

    # ---------------------------------------------------------------- экспорт
    def export_attachment(
        self,
        note_id: UUID | str,
        attachment_id: UUID | str,
        destination: str | Path,
        *,
        overwrite: bool = False,
    ) -> Path:
        note = self._repository.get_by_id(self._coerce_uuid(note_id))
        attachment = self._find_attachment(note, attachment_id)

        destination_path = Path(destination).expanduser()
        if destination_path.is_dir():
            destination_path = destination_path / attachment.filename

        return self._storage.export(
            attachment.relative_path,
            destination_path,
            overwrite=overwrite,
        )

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _find_attachment(note: Note, attachment_id: UUID | str) -> Attachment:
        try:
            identifier = (
                attachment_id
                if isinstance(attachment_id, UUID)
                else UUID(str(attachment_id))
            )
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValidationError(
                f"Invalid attachment id: {attachment_id!r}"
            ) from exc

        for attachment in note.attachments:
            if attachment.id == identifier:
                return attachment
        raise AttachmentNotFoundError(
            f"Attachment {identifier} not found in note {note.id}"
        )

    @staticmethod
    def _coerce_uuid(value: object) -> UUID:
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValidationError(f"Invalid note id: {value!r}") from exc


__all__ = ["AttachmentService"]
