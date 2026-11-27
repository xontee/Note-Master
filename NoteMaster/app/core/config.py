"""Централизованная конфигурация NoteMaster.

Единственный источник настроек приложения. Все остальные модули получают
:class:`Config` через внедрение зависимостей и не читают переменные окружения
или файлы конфигурации самостоятельно.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_ENCODING = "utf-8"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_MAX_ATTACHMENT_SIZE = 25 * 1024 * 1024  # 25 MiB
DEFAULT_MAX_ATTACHMENTS_PER_NOTE = 20

# Данные привязаны к расположению проекта, а не к текущему каталогу запуска.
# Это исключает ситуацию, когда `python NoteMaster/run.py` из другого каталога
# создаёт второе пустое хранилище и «не видит» существующие заметки.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"

# Потенциально опасные форматы, запрещённые по умолчанию.
DEFAULT_FORBIDDEN_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".exe",
        ".bat",
        ".cmd",
        ".com",
        ".scr",
        ".pif",
        ".msi",
        ".msp",
        ".dll",
        ".sys",
        ".drv",
        ".cpl",
        ".hta",
        ".reg",
        ".lnk",
        ".inf",
        ".ps1",
        ".psm1",
        ".psd1",
        ".vbs",
        ".vbe",
        ".js",
        ".jse",
        ".wsf",
        ".wsh",
        ".jar",
        ".apk",
        ".app",
        ".sh",
        ".bash",
        ".zsh",
        ".command",
        ".iso",
        ".img",
        ".vhd",
        ".vhdx",
    }
)


def normalize_extensions(values: Iterable[str]) -> frozenset[str]:
    """Приводит расширения к нижнему регистру и формату с ведущей точкой."""

    normalized: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            raise TypeError(f"Extension must be a string, got {type(value)!r}")
        extension = value.strip().lower()
        if not extension:
            continue
        if not extension.startswith("."):
            extension = "." + extension
        normalized.add(extension)
    return frozenset(normalized)


@dataclass(frozen=True, slots=True)
class Config:
    """Неизменяемая конфигурация приложения."""

    data_dir: Path = DEFAULT_DATA_DIR
    encoding: str = DEFAULT_ENCODING
    date_format: str = DEFAULT_DATE_FORMAT
    max_attachment_size: int = DEFAULT_MAX_ATTACHMENT_SIZE
    max_attachments_per_note: int = DEFAULT_MAX_ATTACHMENTS_PER_NOTE
    allowed_extensions: frozenset[str] | None = None
    forbidden_extensions: frozenset[str] = DEFAULT_FORBIDDEN_EXTENSIONS
    allow_empty_files: bool = False
    debug: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "data_dir", Path(self.data_dir))

        if self.allowed_extensions is not None:
            object.__setattr__(
                self,
                "allowed_extensions",
                normalize_extensions(self.allowed_extensions),
            )
        object.__setattr__(
            self,
            "forbidden_extensions",
            normalize_extensions(self.forbidden_extensions),
        )

        if self.max_attachment_size <= 0:
            raise ValueError("max_attachment_size must be a positive integer")
        if self.max_attachments_per_note <= 0:
            raise ValueError("max_attachments_per_note must be a positive integer")
        if not self.encoding:
            raise ValueError("encoding must not be empty")
        if not self.date_format:
            raise ValueError("date_format must not be empty")

    @classmethod
    def default(cls) -> "Config":
        """Конфигурация по умолчанию (каталог ``data/``)."""

        return cls()

    # ------------------------------------------------------------------ пути
    @property
    def notes_file(self) -> Path:
        """Путь к JSON-файлу с заметками."""

        return self.data_dir / "notes.json"

    @property
    def attachments_dir(self) -> Path:
        """Корневой каталог файлового хранилища вложений."""

        return self.data_dir / "attachments"

    @property
    def backups_dir(self) -> Path:
        """Каталог для резервных копий."""

        return self.data_dir / "backups"

    # -------------------------------------------------------------- политика
    def is_extension_allowed(self, extension: str) -> bool:
        """Проверяет расширение с учётом белого и чёрного списков."""

        normalized = (extension or "").strip().lower()
        if normalized and not normalized.startswith("."):
            normalized = "." + normalized

        if normalized in self.forbidden_extensions:
            return False
        if (
            self.allowed_extensions is not None
            and normalized not in self.allowed_extensions
        ):
            return False
        return True


__all__ = [
    "Config",
    "DEFAULT_DATA_DIR",
    "PROJECT_ROOT",
    "DEFAULT_ENCODING",
    "DEFAULT_DATE_FORMAT",
    "DEFAULT_FORBIDDEN_EXTENSIONS",
    "DEFAULT_MAX_ATTACHMENT_SIZE",
    "DEFAULT_MAX_ATTACHMENTS_PER_NOTE",
    "normalize_extensions",
]
