"""Общие компоненты ядра: конфигурация и исключения."""

from __future__ import annotations

from app.core.config import Config
from app.core.exceptions import (
    AttachmentError,
    AttachmentLimitExceededError,
    AttachmentNotFoundError,
    AttachmentSizeLimitError,
    AttachmentStorageError,
    AttachmentValidationError,
    DuplicateNoteError,
    NoteMasterError,
    NoteNotFoundError,
    SerializationError,
    StorageError,
    ValidationError,
)

__all__ = [
    "Config",
    "NoteMasterError",
    "ValidationError",
    "NoteNotFoundError",
    "DuplicateNoteError",
    "StorageError",
    "SerializationError",
    "AttachmentError",
    "AttachmentNotFoundError",
    "AttachmentStorageError",
    "AttachmentValidationError",
    "AttachmentSizeLimitError",
    "AttachmentLimitExceededError",
]
