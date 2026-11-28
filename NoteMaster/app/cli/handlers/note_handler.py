"""Пользовательские сценарии работы с заметками.

Handler — это «сценарий», а не слой бизнес-логики. Он собирает ввод,
вызывает методы :class:`NoteService` и показывает результат. Никаких
обращений к JSON или файловой системе здесь нет.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.cli.components.console import Console
from app.cli.components.formatting import (
    format_timestamp,
    parse_bool,
    tags_text,
    wrap_block,
)
from app.cli.components.prompts import Prompter
from app.core.config import Config
from app.core.exceptions import NoteNotFoundError, ValidationError
from app.models.note import Note
from app.services.note_service import NoteService
from app.utils.helpers import parse_tags, short_id

NOTE_HEADERS = (
    "№",
    "Заголовок",
    "Категория",
    "Теги",
    "Создана",
    "Изменена",
    "Закр.",
    "Влож.",
)
NOTE_ALIGNS = ("right", "left", "left", "left", "left", "left", "center", "right")
NOTE_MIN_WIDTHS = (2, 10, 6, 6, 10, 10, 4, 5)


class NoteHandler:
    """Сценарии CRUD, выбора и отображения заметок."""

    def __init__(
        self,
        note_service: NoteService,
        config: Config,
        console: Console,
        prompter: Prompter,
    ) -> None:
        self._notes = note_service
        self._config = config
        self._console = console
        self._prompter = prompter

    # ------------------------------------------------------------------ вывод
    def render_table(self, notes: Sequence[Note]) -> None:
        if not notes:
            self._console.warning("Заметок не найдено.")
            return

        rows = []
        for index, note in enumerate(notes, start=1):
            rows.append(
                (
                    str(index),
                    note.title,
                    note.category or "—",
                    tags_text(note.tags),
                    format_timestamp(note.created_at),
                    format_timestamp(note.updated_at),
                    "*" if note.is_pinned else "",
                    str(len(note.attachments)),
                )
            )

        self._console.table(
            NOTE_HEADERS,
            rows,
            aligns=NOTE_ALIGNS,
            min_widths=NOTE_MIN_WIDTHS,
        )
        self._console.muted(f"Всего: {len(notes)}")

    def render_details(self, note: Note) -> None:
        """Карточка заметки с переносом длинного содержимого."""

        date_format = self._config.date_format
        self._console.panel(
            "Заметка",
            [
                f"ID: {note.id}",
                f"Заголовок: {note.title}",
                f"Категория: {note.category or '—'}",
                f"Теги: {tags_text(note.tags)}",
                f"Создана: {format_timestamp(note.created_at, date_format)}",
                f"Изменена: {format_timestamp(note.updated_at, date_format)}",
                f"Закреплена: {'да' if note.is_pinned else 'нет'}",
                f"Вложений: {len(note.attachments)}",
            ],
        )
        self._console.blank()
        self._console.heading("СОДЕРЖИМОЕ")
        content = note.content.strip() if note.content.strip() else "—"
        for line in wrap_block(content, max(20, self._console.width - 6)):
            self._console.line(f"  {line}")

    # ---------------------------------------------------------------- создание
    def create_note(self) -> Note | None:
        title = self._prompter.required("Заголовок")
        content = self._prompter.multiline("Содержимое")
        tags_raw = self._prompter.ask("Теги через запятую (Enter — без тегов)")
        category_raw = self._prompter.ask("Категория (Enter — без категории)")
        is_pinned = self._prompter.confirm("Закрепить заметку?", default=False)

        note = self._notes.create_note(
            title=title,
            content=content,
            tags=parse_tags(tags_raw),
            category=category_raw or None,
            is_pinned=is_pinned,
        )
        self._console.success(f"Заметка создана: «{note.title}»")
        self._console.line(f"  ID: {note.id}")
        return note

    # ------------------------------------------------------------------ выбор
    def select_note(
        self,
        candidates: Sequence[Note] | None = None,
        *,
        label: str = "Номер или ID заметки",
    ) -> Note | None:
        """Выбирает заметку по номеру строки, полному ID или префиксу."""

        restricted = candidates is not None
        if candidates is None:
            candidates = self._notes.get_all_notes(
                sort_by="updated_at", descending=True
            )
        notes = list(candidates)

        if not notes:
            self._console.warning("Заметок нет.")
            return None

        self._console.muted(f"Доступно заметок: {len(notes)}")
        raw = self._prompter.ask(f"{label} (Enter — отмена)")
        if not raw or raw == "0":
            self._console.info("Отменено.")
            return None

        # Сначала пытаемся разрешить как UUID (полный ID или префикс).
        # Это позволяет UUID-префиксам, начинающимся с цифры (например
        # "56151154-..."), корректно обрабатываться — иначе они были бы
        # ошибочно восприняты как номер строки.
        try:
            note = self._notes.resolve_note_id(raw)
        except ValidationError:
            raise  # неоднозначный префикс — это реальная ошибка ввода
        except NoteNotFoundError:
            # UUID не найден — проверяем, не номер ли это строки.
            if raw.isdigit():
                index = int(raw)
                if not 1 <= index <= len(notes):
                    raise ValidationError(
                        f"Нет заметки с номером {index}. " f"Доступно: 1–{len(notes)}."
                    )
                return notes[index - 1]
            # Не число и не UUID — пробрасываем ошибку из resolve_note_id
            raise
        if restricted and all(candidate.id != note.id for candidate in notes):
            raise ValidationError("Заметка не входит в текущий список.")
        return note

    # -------------------------------------------------------------- изменение
    def edit_note(self, note: Note) -> Note | None:
        fresh = self._notes.get_note(note.id)
        self._console.muted(f"Текущий заголовок: {fresh.title}")

        changes: dict[str, object] = {}

        title_raw = self._prompter.ask("Новый заголовок (Enter — оставить)")
        if title_raw:
            changes["title"] = title_raw

        if self._prompter.confirm("Изменить содержимое?", default=False):
            changes["content"] = self._prompter.multiline("Новое содержимое")

        tags_raw = self._prompter.ask(
            f"Теги [{tags_text(fresh.tags)}] (Enter — оставить, '-' — очистить)"
        )
        if tags_raw == "-":
            changes["tags"] = []
        elif tags_raw:
            changes["tags"] = parse_tags(tags_raw)

        category_raw = self._prompter.ask(
            f"Категория [{fresh.category or '—'}] " "(Enter — оставить, '-' — очистить)"
        )
        if category_raw == "-":
            changes["category"] = None
        elif category_raw:
            changes["category"] = category_raw

        pinned_raw = self._prompter.ask(
            f"Закрепление [{'да' if fresh.is_pinned else 'нет'}] "
            "(Enter — оставить, y/n)"
        )
        if pinned_raw:
            changes["is_pinned"] = parse_bool(pinned_raw, default=fresh.is_pinned)

        if not changes:
            self._console.info("Изменений нет.")
            return fresh

        updated = self._notes.update_note(fresh.id, **changes)
        self._console.success("Заметка обновлена.")
        return updated

    def toggle_pin(self, note: Note) -> Note | None:
        fresh = self._notes.get_note(note.id)
        if fresh.is_pinned:
            updated = self._notes.unpin_note(fresh.id)
            self._console.success(f"Заметка «{updated.title}» откреплена.")
        else:
            updated = self._notes.pin_note(fresh.id)
            self._console.success(f"Заметка «{updated.title}» закреплена.")
        return updated

    # --------------------------------------------------------------- удаление
    def delete_note(self, note: Note) -> bool:
        fresh = self._notes.get_note(note.id)
        if fresh.attachments:
            self._console.warning(
                f"Заметка содержит вложений: {len(fresh.attachments)}. "
                "Файлы будут удалены вместе с заметкой."
            )

        if not self._prompter.confirm(
            f"Удалить заметку «{fresh.title}»?", default=False
        ):
            self._console.info("Удаление отменено.")
            return False

        result = self._notes.delete_note(fresh.id)
        self._console.success(f"Заметка удалена (ID: {short_id(result.note_id)}).")

        if result.failed_attachments:
            self._console.warning(
                "Не удалось удалить файлы вложений: "
                f"{len(result.failed_attachments)}."
            )
            for attachment, reason in result.failed_attachments:
                self._console.muted(f"  • {attachment.filename}: {reason}")
        return True


__all__ = ["NoteHandler", "NOTE_HEADERS"]
