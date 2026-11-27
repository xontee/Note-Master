"""Вспомогательные функции, не зависящие от конкретных слоёв."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

_SIZE_UNITS = ("B", "KB", "MB", "GB", "TB", "PB")


def utc_now() -> datetime:
    """Возвращает текущий момент в UTC с информацией о часовом поясе."""

    return datetime.now(timezone.utc)


def configure_console_output() -> None:
    """Делает вывод в консоль устойчивым к её кодировке.

    Windows-консоли с кодовой страницей вроде ``cp866`` не умеют кодировать
    типографские символы, из-за чего ``print`` падает с ``UnicodeEncodeError``
    и команды «молчат». Включаем ``errors='replace'``, а если текущая
    кодировка не поддерживает даже кириллицу — переключаемся на UTF-8.
    """

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue

        encoding = getattr(stream, "encoding", None) or "utf-8"
        try:
            "тест".encode(encoding)
            target = encoding
        except (UnicodeEncodeError, LookupError):
            target = "utf-8"

        try:
            reconfigure(encoding=target, errors="replace")
        except (OSError, ValueError):
            pass


def ensure_aware(value: datetime) -> datetime:
    """Гарантирует, что ``datetime`` имеет часовой пояс (по умолчанию UTC)."""

    if not isinstance(value, datetime):
        raise TypeError(f"Expected datetime, got {type(value)!r}")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def to_iso(value: datetime) -> str:
    """Сериализует ``datetime`` в ISO-8601 (с часовым поясом)."""

    return ensure_aware(value).isoformat()


def from_iso(value: str) -> datetime:
    """Разбирает ISO-8601 строку и возвращает timezone-aware ``datetime``."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError("Datetime value must be a non-empty string")
    parsed = datetime.fromisoformat(value.strip())
    return ensure_aware(parsed)


def human_readable_size(size: int) -> str:
    """Форматирует размер в байтах в человекочитаемый вид."""

    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise ValueError("Size must be a non-negative integer")

    value = float(size)
    for unit in _SIZE_UNITS:
        if value < 1024 or unit == _SIZE_UNITS[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"  # pragma: no cover - недостижимо


def normalize_extension(name_or_path: str | Path) -> str:
    """Возвращает расширение в нижнем регистре с ведущей точкой (или "")."""

    suffix = Path(str(name_or_path)).suffix.lower()
    return suffix


def parse_tags(raw: str) -> list[str]:
    """Разбирает строку тегов, разделённых запятыми."""

    if not isinstance(raw, str):
        raise TypeError("Tags input must be a string")
    return [part.strip() for part in raw.split(",") if part.strip()]


def normalize_tags(tags: Iterable[str] | str | None) -> list[str]:
    """Нормализует список тегов: обрезает пробелы и убирает дубликаты.

    Дубликаты определяются без учёта регистра, но сохраняется исходное
    написание первого вхождения.
    """

    if tags is None:
        return []
    if isinstance(tags, str):
        tags = parse_tags(tags)

    result: list[str] = []
    seen: set[str] = set()
    for raw in tags:
        if not isinstance(raw, str):
            raise TypeError(f"Tag must be a string, got {type(raw)!r}")
        tag = raw.strip()
        if not tag:
            continue
        key = tag.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(tag)
    return result


def format_datetime(value: datetime, fmt: str) -> str:
    """Форматирует дату с учётом настроек приложения."""

    return ensure_aware(value).astimezone(timezone.utc).strftime(fmt)


def short_id(value: object, length: int = 8) -> str:
    """Возвращает короткое представление идентификатора для вывода."""

    text = str(value)
    return text[:length]


__all__ = [
    "utc_now",
    "configure_console_output",
    "ensure_aware",
    "to_iso",
    "from_iso",
    "human_readable_size",
    "normalize_extension",
    "parse_tags",
    "normalize_tags",
    "format_datetime",
    "short_id",
]
