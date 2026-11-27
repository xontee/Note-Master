"""Композиционный корень NoteMaster.

Здесь создаются все зависимости и связываются в единое приложение.
Все модули получают объекты через внедрение — нигде нет глобального состояния.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.cli.components.console import enable_windows_ansi
from app.cli.interface import NoteMasterCLI
from app.core.config import Config
from app.repositories.json_repository import JsonNoteRepository
from app.services.attachment_service import AttachmentService
from app.services.integrity_service import IntegrityService
from app.services.note_service import NoteService
from app.storage.file_storage import LocalAttachmentStorage
from app.storage.json_storage import JsonStorage
from app.utils.helpers import configure_console_output


def build_application(config: Config | None = None) -> "Application":
    """Собирает приложение из отдельных компонентов.

    Используется для запуска CLI и для тестов.
    """

    cfg = config or Config.default()
    storage = JsonStorage(cfg.notes_file, encoding=cfg.encoding)
    storage.ensure_initialized()
    repository = JsonNoteRepository(storage)
    attachment_storage = LocalAttachmentStorage(cfg.attachments_dir)
    note_service = NoteService(repository, attachment_storage)
    attachment_service = AttachmentService(repository, attachment_storage, cfg)
    integrity_service = IntegrityService(repository, attachment_storage)
    cli = NoteMasterCLI(
        note_service,
        attachment_service,
        cfg,
        integrity_service=integrity_service,
    )
    return Application(
        cfg,
        storage,
        repository,
        attachment_storage,
        note_service,
        attachment_service,
        integrity_service,
        cli,
    )


class Application:
    """Объект приложения с доступом ко всем компонентам."""

    def __init__(
        self,
        config: Config,
        storage: JsonStorage,
        repository: JsonNoteRepository,
        attachment_storage: LocalAttachmentStorage,
        note_service: NoteService,
        attachment_service: AttachmentService,
        integrity_service: IntegrityService,
        cli: NoteMasterCLI,
    ) -> None:
        self.config = config
        self.storage = storage
        self.repository = repository
        self.attachment_storage = attachment_storage
        self.note_service = note_service
        self.attachment_service = attachment_service
        self.integrity_service = integrity_service
        self.cli = cli


def main(argv: list[str] | None = None) -> int:
    """Точка входа приложения.

    Поддерживает аргументы командной строки для сценариев вне интерактивного
    режима.
    """

    parser = argparse.ArgumentParser(
        prog="notemaster",
        description="NoteMaster - система управления заметками с вложениями",
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Каталог данных (по умолчанию <проект>/data, не зависит от текущего каталога)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Включить режим отладки",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Проверить целостность хранилища и выйти",
    )

    args = parser.parse_args(argv)
    configure_console_output()
    enable_windows_ansi()
    config = (
        Config(data_dir=Path(args.data_dir), debug=args.debug)
        if args.data_dir
        else Config(debug=args.debug)
    )
    app = build_application(config)

    if args.check:
        report = app.integrity_service.check()
        print(report.summary())
        if not report.is_healthy:
            return 1
        return 0

    try:
        app.cli.run()
    except KeyboardInterrupt:
        print("\nВыход.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
