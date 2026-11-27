"""Доменные модели NoteMaster."""

from __future__ import annotations

from app.models.attachment import Attachment
from app.models.note import MAX_TITLE_LENGTH, UNSET, Note

__all__ = ["Attachment", "Note", "MAX_TITLE_LENGTH", "UNSET"]
