"""Экран поиска и фильтрации заметок."""

from __future__ import annotations

from app.cli.menu import Menu, MenuItem
from app.cli.navigation import Nav
from app.cli.views.base import BaseView
from app.models.note import Note


class SearchView(BaseView):
    """Поиск по тексту, тегу и категории через NoteService."""

    title = "Поиск"

    def __init__(self, context) -> None:  # noqa: ANN001
        super().__init__(context)
        self._results: list[Note] = []
        self._last_query: str = ""

    # ------------------------------------------------------------------ вывод
    def render_body(self) -> None:
        if not self._last_query:
            self.ctx.console.muted(
                "Поиск идёт по заголовку, содержимому, тегам и категории."
            )
            return

        self.ctx.console.muted(f"Запрос: {self._last_query}")
        if not self._results:
            self.ctx.console.warning("Ничего не найдено.")
            return
        self.ctx.notes.render_table(self._results)

    # ------------------------------------------------------------------ меню
    def build_menu(self) -> Menu:
        return Menu(
            "МЕНЮ ПОИСКА",
            (
                MenuItem("1", "Поиск по тексту"),
                MenuItem("2", "Поиск по тегу"),
                MenuItem("3", "Поиск по категории"),
                MenuItem("4", "Открыть найденную заметку"),
                MenuItem("5", "Повторить поиск"),
                MenuItem("0", "Назад"),
            ),
        )

    # ------------------------------------------------------------ обработка
    def handle(self, key: str) -> Nav:
        if key == "1":
            self._search_text()
        elif key == "2":
            self._search_tag()
        elif key == "3":
            self._search_category()
        elif key == "4":
            self._open_result()
        elif key == "5":
            self._repeat()
        return Nav.STAY

    # ------------------------------------------------------------- сценарии
    def _search_text(self) -> None:
        query = self.ctx.prompter.required("Поисковый запрос")
        self._results = self.ctx.note_service.search_notes(
            query, sort_by="updated_at", descending=True
        )
        self._last_query = f"текст «{query}»"

    def _search_tag(self) -> None:
        tag = self.ctx.prompter.required("Тег")
        self._results = self.ctx.note_service.filter_notes(
            tag=tag, sort_by="updated_at", descending=True
        )
        self._last_query = f"тег «{tag}»"

    def _search_category(self) -> None:
        category = self.ctx.prompter.required("Категория")
        self._results = self.ctx.note_service.filter_notes(
            category=category, sort_by="updated_at", descending=True
        )
        self._last_query = f"категория «{category}»"

    def _open_result(self) -> None:
        if not self._results:
            self.ctx.console.warning("Сначала выполните поиск.")
            return

        from app.cli.views.note_details import NoteDetailsView

        note = self.ctx.notes.select_note(candidates=self._results)
        if note:
            self.ctx.navigator.push(NoteDetailsView(self.ctx, note.id))

    def _repeat(self) -> None:
        if not self._last_query:
            self.ctx.console.warning("Нет предыдущего запроса.")
            return
        if self._last_query.startswith("текст"):
            raw = self.ctx.prompter.required("Поисковый запрос")
            self._results = self.ctx.note_service.search_notes(
                raw, sort_by="updated_at", descending=True
            )
            self._last_query = f"текст «{raw}»"
        elif self._last_query.startswith("тег"):
            raw = self.ctx.prompter.required("Тег")
            self._results = self.ctx.note_service.filter_notes(
                tag=raw, sort_by="updated_at", descending=True
            )
            self._last_query = f"тег «{raw}»"
        else:
            raw = self.ctx.prompter.required("Категория")
            self._results = self.ctx.note_service.filter_notes(
                category=raw, sort_by="updated_at", descending=True
            )
            self._last_query = f"категория «{raw}»"


__all__ = ["SearchView"]
