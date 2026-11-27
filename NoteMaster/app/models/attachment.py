"""Модель файлового вложения."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from uuid import UUID, uuid4

from app.core.exceptions import ValidationError
from app.utils.helpers import ensure_aware, from_iso, to_iso, utc_now


@dataclass(slots=True, kw_only=True)
class Attachment:
    """Метаданные файла, прикреплённого к заметке.

    Оригинальное имя (``filename``) хранится отдельно от физического
    (``stored_filename``), поэтому коллизии имён и небезопасные символы не
    влияют на путь хранения.
    """

    filename: str
    relative_path: str
    extension: str
    size: int
    id: UUID = field(default_factory=uuid4)
    stored_filename: str = ""
    mime_type: str | None = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            try:
                self.id = UUID(str(self.id))
            except (ValueError, AttributeError, TypeError) as exc:
                raise ValidationError(f"Invalid attachment id: {self.id!r}") from exc

        self.filename = self._validate_filename(self.filename)

        if not isinstance(self.relative_path, str) or not self.relative_path.strip():
            raise ValidationError("Attachment relative_path must be a non-empty string")
        self.relative_path = self.relative_path.strip().replace("\\", "/")

        if not isinstance(self.stored_filename, str):
            raise ValidationError("Attachment stored_filename must be a string")
        stored = self.stored_filename.strip()
        self.stored_filename = stored or Path(self.relative_path).name

        if not isinstance(self.extension, str):
            raise ValidationError("Attachment extension must be a string")
        extension = self.extension.strip().lower()
        if extension and not extension.startswith("."):
            extension = "." + extension
        self.extension = extension

        if isinstance(self.size, bool) or not isinstance(self.size, int) or self.size < 0:
            raise ValidationError("Attachment size must be a non-negative integer")

        if self.mime_type is not None and not isinstance(self.mime_type, str):
            raise ValidationError("Attachment mime_type must be a string or None")

        if not isinstance(self.created_at, datetime):
            raise ValidationError("Attachment created_at must be a datetime")
        self.created_at = ensure_aware(self.created_at)

    # ------------------------------------------------------------ валидация
    @staticmethod
    def _validate_filename(value: str) -> str:
        if not isinstance(value, str):
            raise ValidationError("Attachment filename must be a string")
        filename = value.strip()
        if not filename:
            raise ValidationError("Attachment filename must not be empty")
        if filename in {".", ".."} or "/" in filename or "\\" in filename:
            raise ValidationError(
                f"Attachment filename must be a plain file name: {value!r}"
            )
        return filename

    # -------------------------------------------------------- сериализация
    def to_dict(self) -> dict[str, Any]:
        """Преобразует модель в JSON-совместимый словарь."""

        return {
            "id": str(self.id),
            "filename": self.filename,
            "stored_filename": self.stored_filename,
            "relative_path": self.relative_path,
            "mime_type": self.mime_type,
            "extension": self.extension,
            "size": self.size,
            "created_at": to_iso(self.created_at),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Attachment":
        """Восстанавливает модель из словаря, проверяя обязательные поля."""

        if not isinstance(data, Mapping):
            raise ValidationError("Attachment data must be a mapping")

        required = ("id", "filename", "relative_path", "extension", "size", "created_at")
        missing = [key for key in required if key not in data]
        if missing:
            raise ValidationError(
                "Attachment is missing required fields: " + ", ".join(missing)
            )

        try:
            attachment_id = UUID(str(data["id"]))
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValidationError(f"Invalid attachment id: {data['id']!r}") from exc

        try:
            created_at = from_iso(data["created_at"])
        except ValueError as exc:
            raise ValidationError(f"Invalid attachment created_at: {exc}") from exc

        try:
            return cls(
                id=attachment_id,
                filename=data["filename"],
                stored_filename=data.get("stored_filename", ""),
                relative_path=data["relative_path"],
                mime_type=data.get("mime_type"),
                extension=data["extension"],
                size=data["size"],
                created_at=created_at,
            )
        except ValidationError:
            raise
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"Invalid attachment data: {exc}") from exc


__all__ = ["Attachment"]
