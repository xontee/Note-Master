"""Форматирование значений для терминального интерфейса.

Модуль не знает о сервисах и не содержит бизнес-логики: он только приводит
данные Core к виду, удобному для вывода. Ширина строк считается в
терминальных колонках, а не в символах, поэтому кириллица и широкие символы
не ломают таблицы.
"""

from __future__ import annotations

import textwrap
import unicodedata
from datetime import datetime

from app.core.exceptions import (
    AttachmentLimitExceededError,
    AttachmentNotFoundError,
    AttachmentSizeLimitError,
    AttachmentStorageError,
    AttachmentValidationError,
    DuplicateNoteError,
    NoteMasterError,
    NoteNotFoundError,
    SerializationError,
    StorageError,
    ValidationError,
)
from app.utils.helpers import format_datetime

_TABLE_DATE_FORMAT = "%Y-%m-%d %H:%M"

_TRUE_VALUES = frozenset({"y", "yes", "д", "да", "1", "true"})
_FALSE_VALUES = frozenset({"n", "no", "н", "нет", "0", "false"})


def char_width(char: str) -> int:
    """Возвращает ширину символа в терминальных колонках."""

    if unicodedata.combining(char):
        return 0
    if unicodedata.east_asian_width(char) in {"W", "F"}:
        return 2
    return 1


def display_width(text: str) -> int:
    """Ширина строки без учёта ANSI-последовательностей.

    ANSI-коды в ячейки таблиц не попадают, поэтому отдельная очистка не
    требуется: цвета применяются к уже готовым строкам.
    """

    return sum(char_width(char) for char in text)


def truncate(text: str, width: int, ellipsis: str = "…") -> str:
    """Обрезает строку до ``width`` терминальных колонок."""

    if width <= 0:
        return ""
    if display_width(text) <= width:
        return text
    if width <= display_width(ellipsis):
        return ellipsis[:width]

    target = width - display_width(ellipsis)
    result: list[str] = []
    used = 0
    for char in text:
        char_size = char_width(char)
        if used + char_size > target:
            break
        result.append(char)
        used += char_size
    return "".join(result) + ellipsis


def pad(text: str, width: int, align: str = "left") -> str:
    """Дополняет строку пробелами до нужной ширины."""

    gap = width - display_width(text)
    if gap <= 0:
        return text
    if align == "right":
        return " " * gap + text
    if align == "center":
        left = gap // 2
        return " " * left + text + " " * (gap - left)
    return text + " " * gap


def wrap_block(text: str, width: int) -> list[str]:
    """Переносит многострочный текст по словам, сохраняя пустые строки."""

    if width <= 0:
        return [text]
    lines: list[str] = []
    for raw_line in (text or "").splitlines() or [""]:
        if not raw_line.strip():
            lines.append("")
            continue
        wrapped = textwrap.wrap(
            raw_line,
            width=width,
            break_long_words=True,
            break_on_hyphens=False,
            replace_whitespace=False,
        )
        lines.extend(wrapped or [""])
    return lines


def format_timestamp(value: datetime, fmt: str = _TABLE_DATE_FORMAT) -> str:
    """Форматирует дату для таблиц и карточек."""

    return format_datetime(value, fmt)


def tags_text(tags: list[str]) -> str:
    """Представляет теги одной строкой."""

    return ", ".join(tags) if tags else "—"


def parse_bool(raw: str, *, default: bool) -> bool:
    """Разбирает ответ пользователя; при неоднозначности возвращает default."""

    value = (raw or "").strip().lower()
    if not value:
        return default
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    return default


def describe_error(error: BaseException) -> tuple[str, str]:
    """Превращает исключение Core в понятное пользователю сообщение.

    Возвращает пару «заголовок — подробность». Подробность сохраняет исходный
    текст Core-исключения, поэтому причина не теряется.
    """

    if isinstance(error, AttachmentSizeLimitError):
        return (
            "Файл превышает допустимый размер.",
            "Уменьшите файл или измените лимит в Config.",
        )
    if isinstance(error, AttachmentLimitExceededError):
        return (
            "Достигнут лимит вложений у заметки.",
            "Удалите лишние вложения или измените лимит в Config.",
        )
    if isinstance(error, AttachmentValidationError):
        return ("Вложение не прошло проверку.", str(error))
    if isinstance(error, AttachmentStorageError):
        return ("Ошибка файлового хранилища вложений.", str(error))
    if isinstance(error, AttachmentNotFoundError):
        return ("Вложение не найдено.", str(error))
    if isinstance(error, NoteNotFoundError):
        return ("Заметка не найдена.", str(error))
    if isinstance(error, DuplicateNoteError):
        return ("Заметка с таким ID уже существует.", str(error))
    if isinstance(error, SerializationError):
        return ("Данные хранилища повреждены.", str(error))
    if isinstance(error, StorageError):
        return ("Ошибка хранилища.", str(error))
    if isinstance(error, ValidationError):
        return ("Некорректные данные.", str(error))
    if isinstance(error, NoteMasterError):
        return ("Ошибка NoteMaster.", str(error))
    return ("Непредвиденная ошибка.", str(error))


__all__ = [
    "char_width",
    "display_width",
    "truncate",
    "pad",
    "wrap_block",
    "format_timestamp",
    "tags_text",
    "parse_bool",
    "describe_error",
]
