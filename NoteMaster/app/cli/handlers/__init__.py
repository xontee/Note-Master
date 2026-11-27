"""Сценарии CLI для заметок и вложений."""

from __future__ import annotations

from app.cli.handlers.attachment_handler import AttachmentHandler
from app.cli.handlers.note_handler import NOTE_HEADERS, NoteHandler

__all__ = ["NoteHandler", "AttachmentHandler", "NOTE_HEADERS"]
