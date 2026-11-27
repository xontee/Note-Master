"""Слой хранения: JSON-документ и файловое хранилище вложений."""

from __future__ import annotations

from app.storage.file_storage import AttachmentStorage, LocalAttachmentStorage
from app.storage.json_storage import JSON_SCHEMA_VERSION, JsonStorage

__all__ = [
    "JsonStorage",
    "JSON_SCHEMA_VERSION",
    "AttachmentStorage",
    "LocalAttachmentStorage",
]
