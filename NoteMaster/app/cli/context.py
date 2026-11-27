"""Общий контекст приложения для экранов CLI.

Context — это «набор зависимостей», который создаётся один раз в точке
входа и передаётся экранам. Благодаря этому экраны не создают сервисы
самостоятельно и не читают настройки из окружения.
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field

from app.cli.components.console import Console
from app.cli.components.formatting import describe_error
from app.cli.components.prompts import Prompter
from app.cli.handlers.attachment_handler import AttachmentHandler
from app.cli.handlers.note_handler import NoteHandler
from app.cli.navigation import Navigator
from app.core.config import Config
from app.core.exceptions import NoteMasterError
from app.services.attachment_service import AttachmentService
from app.services.integrity_service import IntegrityService
from app.services.note_service import NoteService


@dataclass(slots=True)
class AppContext:
    """Все зависимости, необходимые экранам."""

    config: Config
    console: Console
    prompter: Prompter
    note_service: NoteService
    attachment_service: AttachmentService
    integrity_service: IntegrityService | None
    notes: NoteHandler
    attachments: AttachmentHandler
    navigator: Navigator = field(default_factory=Navigator)

    def report_error(self, error: NoteMasterError) -> None:
        """Показывает понятное сообщение об ошибке Core."""

        message, detail = describe_error(error)
        self.console.error(message)
        if detail and detail != message:
            self.console.muted(f"  {detail}")
        if self.config.debug:
            self.console.muted(traceback.format_exc())


__all__ = ["AppContext"]
