"""Пользовательские сценарии работы с вложениями.

CLI не копирует файлы и не вычисляет пути хранения: этим занимается
:class:`AttachmentService` и абстракция ``AttachmentStorage``. Handler лишь
проверяет формат пользовательского ввода (например, что путь указывает на
файл) и отображает результат.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from uuid import UUID

from app.cli.components.console import Console
from app.cli.components.formatting import format_timestamp
from app.cli.components.prompts import Prompter
from app.core.exceptions import AttachmentStorageError, NoteMasterError
from app.models.attachment import Attachment
from app.models.note import Note
from app.services.attachment_service import AttachmentService
from app.services.integrity_service import IntegrityService
from app.utils.helpers import human_readable_size, short_id

ATTACHMENT_HEADERS = (
    "№",
    "Файл",
    "Расш.",
    "MIME",
    "Размер",
    "Добавлено",
    "Статус",
)
ATTACHMENT_ALIGNS = ("right", "left", "left", "left", "right", "left", "center")
ATTACHMENT_MIN_WIDTHS = (2, 10, 5, 8, 7, 10, 6)


class AttachmentHandler:
    """Сценарии добавления, просмотра, удаления и экспорта вложений."""

    def __init__(
        self,
        attachment_service: AttachmentService,
        integrity_service: IntegrityService | None,
        console: Console,
        prompter: Prompter,
    ) -> None:
        self._attachments = attachment_service
        self._integrity = integrity_service
        self._console = console
        self._prompter = prompter

    # ------------------------------------------------------------------ вывод
    def render_table(self, note: Note) -> None:
        attachments = self._attachments.list_attachments(note.id)
        self._console.heading("ВЛОЖЕНИЯ")
        if not attachments:
            self._console.muted("У заметки нет вложений.")
            return

        missing_ids = self._missing_ids()
        rows = [
            (
                str(index),
                attachment.filename,
                attachment.extension or "—",
                attachment.mime_type or "—",
                human_readable_size(attachment.size),
                format_timestamp(attachment.created_at),
                self._status(attachment, missing_ids),
            )
            for index, attachment in enumerate(attachments, start=1)
        ]
        self._console.table(
            ATTACHMENT_HEADERS,
            rows,
            aligns=ATTACHMENT_ALIGNS,
            min_widths=ATTACHMENT_MIN_WIDTHS,
        )
        self._console.muted(f"Всего вложений: {len(attachments)}")

    def info(self, note: Note) -> None:
        attachment = self.select_attachment(note)
        if attachment is None:
            return

        missing_ids = self._missing_ids()
        if missing_ids is None:
            status = "неизвестно (проверка недоступна)"
        elif attachment.id in missing_ids:
            status = "файл отсутствует в хранилище"
        else:
            status = "файл доступен"

        self._console.panel(
            "Вложение",
            [
                f"ID: {attachment.id}",
                f"Имя файла: {attachment.filename}",
                f"Расширение: {attachment.extension or '—'}",
                f"MIME-тип: {attachment.mime_type or '—'}",
                f"Размер: {human_readable_size(attachment.size)}",
                f"Добавлено: {format_timestamp(attachment.created_at, '%Y-%m-%d %H:%M:%S')}",
                f"Путь в хранилище: {attachment.relative_path}",
                f"Статус: {status}",
            ],
        )

    # -------------------------------------------------------------- добавление
    def add(self, note: Note) -> Attachment | None:
        path_raw = self._prompter.required("Путь к исходному файлу")
        path = Path(path_raw).expanduser()

        # Проверка формата ввода: путь должен указывать на существующий файл.
        # Все остальные проверки (размер, расширение, сигнатура) — в Core.
        if not path.is_file():
            self._console.error(f"Файл не найден: {path}")
            self._console.muted("Проверьте путь. Вложение не добавлено.")
            return None

        attachment = self._attachments.add_attachment(note.id, path)
        self._console.success(f"Вложение добавлено: {attachment.filename}")
        self._console.line(f"  ID: {attachment.id}")
        self._console.muted(
            f"  Размер: {human_readable_size(attachment.size)} · "
            f"MIME: {attachment.mime_type or '—'}"
        )
        return attachment

    # ---------------------------------------------------------------- удаление
    def remove(self, note: Note) -> Attachment | None:
        attachment = self.select_attachment(note)
        if attachment is None:
            return None

        if not self._prompter.confirm(
            f"Удалить вложение «{attachment.filename}»?", default=False
        ):
            self._console.info("Удаление отменено.")
            return None

        removed = self._attachments.remove_attachment(note.id, attachment.id)
        self._console.success(f"Вложение «{removed.filename}» удалено.")
        return removed

    # ------------------------------------------------------------------ экспорт
    def export(self, note: Note) -> Path | None:
        attachment = self.select_attachment(note)
        if attachment is None:
            return None

        destination = self._prompter.required(
            "Путь назначения (файл или каталог)"
        )

        try:
            exported = self._attachments.export_attachment(
                note.id, attachment.id, destination
            )
        except AttachmentStorageError as exc:
            if "already exists" not in str(exc).lower():
                raise
            if not self._prompter.confirm(
                "Файл уже существует. Перезаписать?", default=False
            ):
                self._console.info("Экспорт отменён.")
                return None
            exported = self._attachments.export_attachment(
                note.id, attachment.id, destination, overwrite=True
            )

        self._console.success(f"Вложение экспортировано: {exported}")
        return exported

    # -------------------------------------------------------------- доступность
    def check_availability(self) -> None:
        if self._integrity is None:
            self._console.warning("Проверка доступности недоступна.")
            return

        report = self._integrity.check()
        self._console.panel(
            "Доступность вложений",
            [
                f"Вложений в метаданных: {report.total_attachments}",
                f"Отсутствующих файлов: {len(report.missing_files)}",
                f"Файлов без метаданных: {len(report.orphan_files)}",
            ],
        )

        if report.missing_files:
            self._console.table(
                ("Файл", "Путь в хранилище"),
                [
                    (attachment.filename, attachment.relative_path)
                    for attachment in report.missing_files
                ],
                aligns=("left", "left"),
                min_widths=(10, 10),
            )
        elif report.total_attachments == 0:
            self._console.info("Вложений нет.")
        else:
            self._console.success("Все файлы вложений доступны.")

        if report.orphan_files:
            self._console.warning(
                f"Файлов без метаданных: {len(report.orphan_files)}."
            )
            for relative_path in report.orphan_files:
                self._console.muted(f"  • {relative_path}")

    # ------------------------------------------------------------------ выбор
    def select_attachment(self, note: Note) -> Attachment | None:
        attachments = self._attachments.list_attachments(note.id)
        if not attachments:
            self._console.warning("У заметки нет вложений.")
            return None

        self.render_table(note)
        raw = self._prompter.ask("Номер или ID вложения (Enter — отмена)")
        if not raw or raw == "0":
            self._console.info("Отменено.")
            return None

        if raw.isdigit():
            index = int(raw)
            if not 1 <= index <= len(attachments):
                self._console.error(
                    f"Нет вложения с номером {index}. "
                    f"Доступно: 1–{len(attachments)}."
                )
                return None
            return attachments[index - 1]

        return self._attachments.get_attachment(note.id, raw)

    # ---------------------------------------------------------------- helpers
    def _missing_ids(self) -> set[UUID] | None:
        """ID вложений, физические файлы которых отсутствуют.

        ``None`` означает, что проверить не удалось (нет IntegrityService или
        хранилище вернуло ошибку). Это не скрывает проблему: в таблице статус
        будет «?».
        """

        if self._integrity is None:
            return None
        try:
            report = self._integrity.check()
        except NoteMasterError:
            return None
        return {attachment.id for attachment in report.missing_files}

    @staticmethod
    def _status(attachment: Attachment, missing_ids: set[UUID] | None) -> str:
        if missing_ids is None:
            return "?"
        return "НЕТ" if attachment.id in missing_ids else "OK"


__all__ = ["AttachmentHandler", "ATTACHMENT_HEADERS"]
