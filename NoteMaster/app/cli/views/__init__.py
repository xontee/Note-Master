"""Экраны пользовательского интерфейса CLI."""

from __future__ import annotations

from app.cli.views.attachments_view import AttachmentsView
from app.cli.views.base import BaseView
from app.cli.views.categories_view import CategoriesView
from app.cli.views.dashboard import DashboardView
from app.cli.views.note_details import NoteDetailsView
from app.cli.views.notes_view import NotesView, PinnedNotesView
from app.cli.views.search_view import SearchView
from app.cli.views.settings_view import SettingsView

__all__ = [
    "BaseView",
    "DashboardView",
    "NotesView",
    "PinnedNotesView",
    "NoteDetailsView",
    "SearchView",
    "CategoriesView",
    "AttachmentsView",
    "SettingsView",
]
