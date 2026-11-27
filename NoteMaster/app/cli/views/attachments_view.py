"""Управление вложениями."""

from __future__ import annotations

from app.cli.menu import Menu, MenuItem
from app.cli.navigation import Nav
from app.cli.views.base import BaseView
from app.core.exceptions import NoteMasterError


class AttachmentsView(BaseView):
    """Полное управление вложениями: добавление, просмотр, удаление, экспорт."""

    title = "Вложения"

    def render_body(self) -> None:
        if self.ctx.integrity_service is not None:
            try:
                report = self.ctx.integrity_service.check()
                self.ctx.console.muted(
                    f"Всего вложений: {report.total_attachments} · "
                    f"Файлов без метаданных: {len(report.orphan_files)}"
                )
            except NoteMasterError as exc:
                self.ctx.console.muted(f"Статус: {exc}")

    def build_menu(self) -> Menu:
        return Menu(
            "МЕНЮ ВЛОЖЕНИЙ",
            (
                MenuItem("1", "Добавить вложение"),
                MenuItem("2", "Показать вложения заметки"),
                MenuItem("3", "Информация о вложении"),
                MenuItem("4", "Удалить вложение"),
                MenuItem("5", "Экспортировать вложение"),
                MenuItem("6", "Проверить доступность вложений"),
                MenuItem("0", "Назад"),
            ),
        )

    def handle(self, key: str) -> Nav:
        if key == "1":
            self._add()
        elif key == "2":
            self._list()
        elif key == "3":
            self._info()
        elif key == "4":
            self._remove()
        elif key == "5":
            self._export()
        elif key == "6":
            self.ctx.attachments.check_availability()
        return Nav.STAY

    # ----------------------------------------------------------- сценарии
    def _select_note(self):
        return self.ctx.notes.select_note()

    def _add(self) -> None:
        note = self._select_note()
        if note:
            self.ctx.attachments.add(note)

    def _list(self) -> None:
        note = self._select_note()
        if note:
            self.ctx.attachments.render_table(note)

    def _info(self) -> None:
        note = self._select_note()
        if note:
            self.ctx.attachments.info(note)

    def _remove(self) -> None:
        note = self._select_note()
        if note:
            self.ctx.attachments.remove(note)

    def _export(self) -> None:
        note = self._select_note()
        if note:
            self.ctx.attachments.export(note)


__all__ = ["AttachmentsView"]
