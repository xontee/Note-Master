"""Точка сборки консольного интерфейса.

CLI не создаёт сервисы и не знает о JSON/файлах: он получает готовые
зависимости из композиционного корня (:mod:`app.main`) и только
переключает экраны.
"""

from __future__ import annotations

from app import __version__
from app.cli.components.console import Console, WriteFn
from app.cli.components.prompts import InputCancelled, InputFn, Prompter
from app.cli.context import AppContext
from app.cli.handlers.attachment_handler import AttachmentHandler
from app.cli.handlers.note_handler import NoteHandler
from app.cli.navigation import Nav, Navigator
from app.cli.views.dashboard import DashboardView
from app.core.config import Config
from app.services.attachment_service import AttachmentService
from app.services.integrity_service import IntegrityService
from app.services.note_service import NoteService


class NoteMasterCLI:
    """Интерактивное приложение NoteMaster CLI v1.0."""

    def __init__(
        self,
        note_service: NoteService,
        attachment_service: AttachmentService,
        config: Config,
        integrity_service: IntegrityService | None = None,
        *,
        input_fn: InputFn | None = None,
        output_fn: WriteFn | None = None,
        color: bool | None = None,
        width: int | None = None,
    ) -> None:
        self._config = config
        self._console = Console(output_fn, color=color, width=width)
        self._prompter = Prompter(self._console, input_fn)

        self._context = AppContext(
            config=config,
            console=self._console,
            prompter=self._prompter,
            note_service=note_service,
            attachment_service=attachment_service,
            integrity_service=integrity_service,
            notes=NoteHandler(note_service, config, self._console, self._prompter),
            attachments=AttachmentHandler(
                attachment_service, integrity_service, self._console, self._prompter
            ),
            navigator=Navigator(),
        )

    # ------------------------------------------------------------------ запуск
    def run(self) -> None:
        """Запускает цикл интерфейса до выхода или конца ввода."""

        console = self._console
        console.app_header("NOTE MASTER", "Personal Knowledge Management", __version__)

        navigator = self._context.navigator
        navigator.reset(DashboardView(self._context))

        while True:
            view = navigator.current
            try:
                nav = view.run_once()
            except InputCancelled:
                console.blank()
                console.info("Ввод завершён. До встречи!")
                return

            if nav is Nav.EXIT:
                if self._confirm_exit():
                    console.blank()
                    console.info("До встречи!")
                    return
                continue

            if nav is Nav.BACK:
                if navigator.can_go_back:
                    navigator.pop()
                else:
                    console.muted("Это главный экран. Для выхода выберите «0».")
                continue

            if nav is Nav.HOME:
                navigator.home()

    # --------------------------------------------------------------- helpers
    def _confirm_exit(self) -> bool:
        """Защита от случайного выхода."""

        try:
            return self._prompter.confirm("Выйти из NoteMaster?", default=False)
        except InputCancelled:
            return True


__all__ = ["NoteMasterCLI"]
