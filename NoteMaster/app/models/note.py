"""Модель заметки."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping
from uuid import UUID, uuid4

from app.core.exceptions import ValidationError
from app.models.attachment import Attachment
from app.utils.helpers import ensure_aware, from_iso, normalize_tags, to_iso, utc_now

MAX_TITLE_LENGTH = 200

# Сентинел «значение не передано» для частичного обновления.
UNSET: Any = object()


@dataclass(slots=True, kw_only=True)
class Note:
    """Заметка с метаданными, тегами, категорией и вложениями."""

    title: str
    content: str = ""
    tags: list[str] = field(default_factory=list)
    category: str | None = None
    is_pinned: bool = False
    attachments: list[Attachment] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.title = self._validate_title(self.title)
        self.content = self._validate_content(self.content)

        try:
            self.tags = normalize_tags(self.tags)
        except TypeError as exc:
            raise ValidationError(str(exc)) from exc

        self.category = self._validate_category(self.category)
        self.is_pinned = bool(self.is_pinned)

        if not isinstance(self.id, UUID):
            try:
                self.id = UUID(str(self.id))
            except (ValueError, AttributeError, TypeError) as exc:
                raise ValidationError(f"Invalid note id: {self.id!r}") from exc

        if not isinstance(self.created_at, datetime):
            raise ValidationError("Note created_at must be a datetime")
        if not isinstance(self.updated_at, datetime):
            raise ValidationError("Note updated_at must be a datetime")
        self.created_at = ensure_aware(self.created_at)
        self.updated_at = ensure_aware(self.updated_at)
        if self.updated_at < self.created_at:
            self.updated_at = self.created_at

        if not isinstance(self.attachments, list):
            raise ValidationError("Note attachments must be a list")
        for attachment in self.attachments:
            if not isinstance(attachment, Attachment):
                raise ValidationError(
                    "Note attachments must contain Attachment instances"
                )

    # ------------------------------------------------------------ валидация
    @staticmethod
    def _validate_title(value: str) -> str:
        if not isinstance(value, str):
            raise ValidationError("Note title must be a string")
        title = value.strip()
        if not title:
            raise ValidationError("Note title must not be empty")
        if len(title) > MAX_TITLE_LENGTH:
            raise ValidationError(
                f"Note title must not exceed {MAX_TITLE_LENGTH} characters"
            )
        return title

    @staticmethod
    def _validate_content(value: str) -> str:
        if not isinstance(value, str):
            raise ValidationError("Note content must be a string")
        return value

    @staticmethod
    def _validate_category(value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValidationError("Note category must be a string or None")
        category = value.strip()
        return category or None

    # --------------------------------------------------------------- домен
    def touch(self) -> None:
        """Обновляет метку изменения."""

        self.updated_at = utc_now()

    def update(
        self,
        *,
        title: Any = UNSET,
        content: Any = UNSET,
        tags: Any = UNSET,
        category: Any = UNSET,
        is_pinned: Any = UNSET,
    ) -> "Note":
        """Частично обновляет заметку и обновляет ``updated_at``.

        Параметр ``category`` можно явно установить в ``None`` для очистки.
        """

        if title is not UNSET:
            self.title = self._validate_title(title)
        if content is not UNSET:
            self.content = self._validate_content(content)
        if tags is not UNSET:
            try:
                self.tags = normalize_tags(tags)
            except TypeError as exc:
                raise ValidationError(str(exc)) from exc
        if category is not UNSET:
            self.category = self._validate_category(category)
        if is_pinned is not UNSET:
            self.is_pinned = bool(is_pinned)

        self.touch()
        return self

    def has_tag(self, tag: str) -> bool:
        """Проверяет наличие тега без учёта регистра."""

        if not isinstance(tag, str):
            raise ValidationError("Tag must be a string")
        target = tag.strip().casefold()
        return any(existing.casefold() == target for existing in self.tags)

    def in_category(self, category: str) -> bool:
        """Проверяет принадлежность категории без учёта регистра."""

        if not isinstance(category, str):
            raise ValidationError("Category must be a string")
        if self.category is None:
            return False
        return self.category.casefold() == category.strip().casefold()

    def matches(self, query: str) -> bool:
        """Полнотекстовый поиск по заголовку, содержимому, тегам и категории.

        Поиск нечувствителен к регистру. Метод намеренно оставлен в модели,
        чтобы будущие репозитории (SQLite/PostgreSQL) могли переиспользовать
        или заменить его реализацию.
        """

        if not isinstance(query, str):
            raise ValidationError("Search query must be a string")
        normalized = query.strip().casefold()
        if not normalized:
            return True

        if normalized in self.title.casefold():
            return True
        if normalized in self.content.casefold():
            return True
        if any(normalized in tag.casefold() for tag in self.tags):
            return True
        if self.category is not None and normalized in self.category.casefold():
            return True
        return False

    # -------------------------------------------------------- сериализация
    def to_dict(self) -> dict[str, Any]:
        """Преобразует модель в JSON-совместимый словарь."""

        return {
            "id": str(self.id),
            "title": self.title,
            "content": self.content,
            "tags": list(self.tags),
            "category": self.category,
            "is_pinned": self.is_pinned,
            "created_at": to_iso(self.created_at),
            "updated_at": to_iso(self.updated_at),
            "attachments": [attachment.to_dict() for attachment in self.attachments],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Note":
        """Восстанавливает заметку из словаря."""

        if not isinstance(data, Mapping):
            raise ValidationError("Note data must be a mapping")

        required = ("id", "title", "created_at", "updated_at")
        missing = [key for key in required if key not in data]
        if missing:
            raise ValidationError("Note is missing required fields: " + ", ".join(missing))

        attachments_raw = data.get("attachments") or []
        if not isinstance(attachments_raw, list):
            raise ValidationError("Note attachments must be a list")

        attachments: list[Attachment] = []
        for index, item in enumerate(attachments_raw):
            if not isinstance(item, Mapping):
                raise ValidationError(f"Attachment at index {index} must be a mapping")
            attachments.append(Attachment.from_dict(item))

        try:
            note_id = UUID(str(data["id"]))
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValidationError(f"Invalid note id: {data['id']!r}") from exc

        try:
            created_at = from_iso(data["created_at"])
            updated_at = from_iso(data["updated_at"])
        except ValueError as exc:
            raise ValidationError(f"Invalid note timestamps: {exc}") from exc

        try:
            return cls(
                id=note_id,
                title=data["title"],
                content=data.get("content", ""),
                tags=data.get("tags") or [],
                category=data.get("category"),
                is_pinned=bool(data.get("is_pinned", False)),
                attachments=attachments,
                created_at=created_at,
                updated_at=updated_at,
            )
        except ValidationError:
            raise
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"Invalid note data: {exc}") from exc


__all__ = ["Note", "MAX_TITLE_LENGTH", "UNSET"]
