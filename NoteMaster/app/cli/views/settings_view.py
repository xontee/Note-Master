"""Настройки приложения."""

from __future__ import annotations

import platform

from app import __version__
from app.cli.menu import Menu, MenuItem
from app.cli.navigation import Nav
from app.cli.views.base import BaseView
from app.core.exceptions import NoteMasterError
from app.utils.helpers import human_readable_size


class SettingsView(BaseView):
    """Просмотр настроек и проверка состояния хранилища."""

    title = "Настройки"

    # ------------------------------------------------------------------ вывод
    def render_body(self) -> None:
        cfg = self.ctx.config
        notes_count = 0
        attachments_count = 0

        try:
            notes = self.ctx.note_service.get_all_notes()
            notes_count = len(notes)
            attachments_count = sum(len(n.attachments) for n in notes)
        except NoteMasterError as exc:
            self.ctx.console.warning(f"Статистика недоступна: {exc}")

        lines = [
            f"NoteMaster: {__version__}",
            f"Python: {platform.python_version()}",
            f"Путь к хранилищу: {cfg.notes_file}",
            f"Путь к вложениям: {cfg.attachments_dir}",
            f"Макс. размер вложения: {human_readable_size(cfg.max_attachment_size)}",
            f"Макс. вложений на заметку: {cfg.max_attachments_per_note}",
            f"Пустые файлы: {'разрешены' if cfg.allow_empty_files else 'запрещены'}",
            f"Разрешённые расширения: "
            f"{'ограничены: ' + ', '.join(sorted(cfg.allowed_extensions or [])) if cfg.allowed_extensions else 'не ограничены (кроме запрещённых)'}",
            f"Запрещённые расширения: {len(cfg.forbidden_extensions)}",
            f"Режим отладки: {'вкл' if cfg.debug else 'выкл'}",
            f"Заметок: {notes_count}",
            f"Вложений: {attachments_count}",
        ]

        self.ctx.console.panel("Настройки", lines)

    # ------------------------------------------------------------------ меню
    def build_menu(self) -> Menu:
        return Menu(
            "МЕНЮ",
            (
                MenuItem("1", "Проверить хранилище"),
                MenuItem("0", "Назад"),
            ),
        )

    def handle(self, key: str) -> Nav:
        if key == "1":
            self.ctx.attachments.check_availability()
        return Nav.STAY


__all__ = ["SettingsView"]
