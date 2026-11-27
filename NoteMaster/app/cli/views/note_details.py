"""Подробный просмотр одной заметки."""

from __future__ import annotations

from uuid import UUID

from app.cli.context import AppContext
from app.cli.menu import Menu, MenuItem
from app.cli.navigation import Nav
from app.cli.views.base import BaseView
from app.core.exceptions import NoteMasterError
from app.models.note import Note


class NoteDetailsView(BaseView):
    """Открытая заметка с возможностью редактирования, закрепления и удаления."""

    title = "Заметка"

    def __init__(self, context: AppContext, note_id: UUID) -> None:
        super().__init__(context)
        self._note_id = note_id

    # ------------------------------------------------------------------ вывод
    def render_body(self) -> None:
        note = self._load()
        if note is None:
            return

        self.ctx.notes.render_details(note)
        self.ctx.console.blank()
        self.ctx.attachments.render_table(note)

    # ------------------------------------------------------------------ меню
    def build_menu(self) -> Menu:
        return Menu(
            "Действия",
            (
                MenuItem("1", "Редактировать заметку"),
                MenuItem("2", "Закрепить / Открепить"),
                MenuItem("3", "Удалить заметку"),
                MenuItem("4", "Добавить вложение"),
                MenuItem("5", "Показать вложения"),
                MenuItem("0", "Назад"),
            ),
        )

    # ----------------------------------------------------------- обработка
    def handle(self, key: str) -> Nav:
        note = self._load()
        if note is None:
            return Nav.BACK

        if key == "1":
            self.ctx.notes.edit_note(note)
        elif key == "2":
            self.ctx.notes.toggle_pin(note)
        elif key == "3":
            if self.ctx.notes.delete_note(note):
                return Nav.BACK
        elif key == "4":
            self.ctx.attachments.add(note)
        elif key == "5":
            self.ctx.attachments.render_table(note)
        # "0" → BACK
        return Nav.STAY

    # ---------------------------------------------------------------- helpers
    def _load(self) -> Note | None:
        """Загружает заметку; возвращает ``None`` при ошибке."""

        try:
            return self.ctx.note_service.get_note(self._note_id)
        except NoteMasterError as exc:
            self.ctx.report_error(exc)
            return None


__all__ = ["NoteDetailsView"]
