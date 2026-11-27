"""Репозитории NoteMaster."""

from __future__ import annotations

from app.repositories.base import NoteRepository
from app.repositories.json_repository import JsonNoteRepository

__all__ = ["NoteRepository", "JsonNoteRepository"]
