"""Просмотр и управление заметками."""

from __future__ import annotations

from app.cli.menu import Menu, MenuItem
from app.cli.navigation import Nav
from app.cli.views.base import BaseView
from app.cli.views.note_details import NoteDetailsView
from app.core.exceptions import NoteMasterError


class NotesView(BaseView):
    """Полное управление заметками: создание, просмотр, редактирование, удаление."""

    title = "Заметки"

    def render_body(self) -> None:
        try:
            notes = self.ctx.note_service.get_all_notes()
            self.ctx.console.muted(f"Всего заметок: {len(notes)}")
        except NoteMasterError as exc:
            self.ctx.console.muted(f"Статистика недоступна: {exc}")

    def build_menu(self) -> Menu:
        return Menu(
            "МЕНЮ ЗАМЕТОК",
            (
                MenuItem("1", "Создать заметку"),
                MenuItem("2", "Показать все заметки"),
                MenuItem("3", "Открыть заметку"),
                MenuItem("4", "Редактировать заметку"),
                MenuItem("5", "Удалить заметку"),
                MenuItem("6", "Закрепить / Открепить"),
                MenuItem("0", "Назад"),
            ),
        )

    def handle(self, key: str) -> Nav:
        if key == "1":
            self.ctx.notes.create_note()
        elif key == "2":
            notes = self.ctx.note_service.get_all_notes(
                sort_by="updated_at", descending=True
            )
            self.ctx.notes.render_table(notes)
        elif key == "3":
            note = self.ctx.notes.select_note()
            if note:
                self.ctx.navigator.push(NoteDetailsView(self.ctx, note.id))
        elif key == "4":
            note = self.ctx.notes.select_note()
            if note:
                self.ctx.notes.edit_note(note)
        elif key == "5":
            note = self.ctx.notes.select_note()
            if note:
                self.ctx.notes.delete_note(note)
        elif key == "6":
            note = self.ctx.notes.select_note()
            if note:
                self.ctx.notes.toggle_pin(note)
        return Nav.STAY


class PinnedNotesView(BaseView):
    """Просмотр закреплённых заметок."""

    title = "Закреплённые заметки"

    def render_body(self) -> None:
        try:
            notes = self.ctx.note_service.filter_notes(
                pinned=True, sort_by="updated_at", descending=True
            )
        except NoteMasterError:
            return

        if not notes:
            self.ctx.console.info("Закреплённых заметок нет.")
            return

        self.ctx.notes.render_table(notes)

    def build_menu(self) -> Menu:
        return Menu(
            "МЕНЮ",
            (
                MenuItem("1", "Открыть заметку"),
                MenuItem("2", "Снять закрепление"),
                MenuItem("0", "Назад"),
            ),
        )

    def handle(self, key: str) -> Nav:
        if key == "1":
            notes = self._get_pinned()
            note = self.ctx.notes.select_note(candidates=notes)
            if note:
                self.ctx.navigator.push(NoteDetailsView(self.ctx, note.id))
        elif key == "2":
            notes = self._get_pinned()
            note = self.ctx.notes.select_note(candidates=notes)
            if note:
                self.ctx.notes.toggle_pin(note)
        return Nav.STAY

    def _get_pinned(self):
        try:
            return self.ctx.note_service.filter_notes(
                pinned=True, sort_by="updated_at", descending=True
            )
        except NoteMasterError:
            return []


__all__ = ["NotesView", "PinnedNotesView"]
