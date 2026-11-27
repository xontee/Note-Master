"""Главный экран приложения — Dashboard."""

from __future__ import annotations

from app import __version__
from app.cli.menu import Menu, MenuItem
from app.cli.navigation import Nav
from app.cli.views.base import BaseView
from app.core.exceptions import NoteMasterError


class DashboardView(BaseView):
    """Стартовый экран: сводка по данным и главное меню."""

    title = "NoteMaster — Personal Knowledge Management"
    is_root = True
    zero_nav = Nav.EXIT

    # ------------------------------------------------------------------ вывод
    def render_body(self) -> None:
        self.ctx.console.muted("Добро пожаловать! Управляйте заметками и вложениями.")
        self.ctx.console.blank()

        notes = self._load_notes()
        total = len(notes)
        pinned = sum(1 for note in notes if note.is_pinned)
        attachments = sum(len(note.attachments) for note in notes)

        self.ctx.console.panel(
            "Сводка",
            [
                f"Заметок: {total}",
                f"Закреплённых: {pinned}",
                f"Вложений: {attachments}",
                f"Хранилище: {self._storage_status()}",
                f"Версия: {__version__}",
            ],
        )

        if total == 0:
            self.ctx.console.blank()
            self.ctx.console.info(
                "Заметок пока нет. Выберите «1 — Notes» и создайте первую заметку."
            )

    # ------------------------------------------------------------------ меню
    def build_menu(self) -> Menu:
        return Menu(
            "ГЛАВНОЕ МЕНЮ",
            (
                MenuItem("1", "Notes — заметки"),
                MenuItem("2", "Search — поиск"),
                MenuItem("3", "Pinned notes — закреплённые"),
                MenuItem("4", "Categories & Tags — категории и теги"),
                MenuItem("5", "Attachments — вложения"),
                MenuItem("6", "Settings — настройки"),
                MenuItem("0", "Exit — выход"),
            ),
            hint="Введите номер команды · Q — выход",
        )

    # ------------------------------------------------------------ обработка
    def handle(self, key: str) -> Nav:
        # Импорты внутри метода: Dashboard — корень, а экраны ссылаются друг
        # на друга. Ленивый импорт исключает циклы модулей.
        if key == "1":
            from app.cli.views.notes_view import NotesView

            self.ctx.navigator.push(NotesView(self.ctx))
        elif key == "2":
            from app.cli.views.search_view import SearchView

            self.ctx.navigator.push(SearchView(self.ctx))
        elif key == "3":
            from app.cli.views.notes_view import PinnedNotesView

            self.ctx.navigator.push(PinnedNotesView(self.ctx))
        elif key == "4":
            from app.cli.views.categories_view import CategoriesView

            self.ctx.navigator.push(CategoriesView(self.ctx))
        elif key == "5":
            from app.cli.views.attachments_view import AttachmentsView

            self.ctx.navigator.push(AttachmentsView(self.ctx))
        elif key == "6":
            from app.cli.views.settings_view import SettingsView

            self.ctx.navigator.push(SettingsView(self.ctx))
        return Nav.STAY

    # --------------------------------------------------------------- helpers
    def _load_notes(self):
        try:
            return self.ctx.note_service.get_all_notes()
        except NoteMasterError as exc:
            self.ctx.console.warning(f"Не удалось прочитать заметки: {exc}")
            return []

    def _storage_status(self) -> str:
        if self.ctx.integrity_service is None:
            return "неизвестно"
        try:
            report = self.ctx.integrity_service.check()
        except NoteMasterError as exc:
            return f"ошибка ({exc})"
        return "Operational" if report.is_healthy else "требует внимания"


__all__ = ["DashboardView"]
