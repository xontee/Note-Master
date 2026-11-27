"""Категории и теги."""

from __future__ import annotations

from collections.abc import Sequence

from app.cli.menu import Menu, MenuItem
from app.cli.navigation import Nav
from app.cli.views.base import BaseView
from app.core.exceptions import NoteMasterError
from app.models.note import Note


class CategoriesView(BaseView):
    """Организация заметок: список категорий, тегов, поиск по ним."""

    title = "Категории и теги"

    # ------------------------------------------------------------------ вывод
    def render_body(self) -> None:
        try:
            notes = self.ctx.note_service.get_all_notes()
        except NoteMasterError as exc:
            self.ctx.console.warning(f"Не удалось загрузить заметки: {exc}")
            return

        categories, tags = self._aggregate(notes)
        self.ctx.console.muted(f"Всего заметок: {len(notes)}")

        if categories:
            self.ctx.console.blank()
            self.ctx.console.heading("КАТЕГОРИИ")
            for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
                self.ctx.console.line(f"  {cat}: {count}")

        if tags:
            self.ctx.console.blank()
            self.ctx.console.heading("ТЕГИ")
            for tag, count in sorted(tags.items(), key=lambda x: (-x[1], x[0])):
                self.ctx.console.line(f"  {tag}: {count}")

        if not categories and not tags:
            self.ctx.console.info("Заметок пока нет.")

    # ------------------------------------------------------------------ меню
    def build_menu(self) -> Menu:
        return Menu(
            "МЕНЮ",
            (
                MenuItem("1", "Заметки по категории"),
                MenuItem("2", "Заметки по тегу"),
                MenuItem("0", "Назад"),
            ),
        )

    def handle(self, key: str) -> Nav:
        if key == "1":
            self._filter_by_category()
        elif key == "2":
            self._filter_by_tag()
        return Nav.STAY

    # ----------------------------------------------------------- сценарии
    def _filter_by_category(self) -> None:
        category = self.ctx.prompter.required("Категория")
        notes = self.ctx.note_service.filter_notes(
            category=category, sort_by="updated_at", descending=True
        )
        self.ctx.console.muted(f"Категория «{category}» — {len(notes)} заметок")
        self.ctx.notes.render_table(notes)

    def _filter_by_tag(self) -> None:
        tag = self.ctx.prompter.required("Тег")
        notes = self.ctx.note_service.filter_notes(
            tag=tag, sort_by="updated_at", descending=True
        )
        self.ctx.console.muted(f"Тег «{tag}» — {len(notes)} заметок")
        self.ctx.notes.render_table(notes)

    # ----------------------------------------------------------- утилиты
    @staticmethod
    def _aggregate(notes: Sequence[Note]):
        categories: dict[str, int] = {}
        tags: dict[str, int] = {}
        for note in notes:
            if note.category:
                key = note.category
                categories[key] = categories.get(key, 0) + 1
            for tag in note.tags:
                tags[tag] = tags.get(tag, 0) + 1
        return categories, tags


__all__ = ["CategoriesView"]
