"""Валидация файлов перед добавлением во вложения.

Проверки не ограничиваются расширением: для известных форматов сверяется
сигнатура (magic bytes), а исполняемые сигнатуры блокируются независимо от
расширения.
"""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Config
from app.core.exceptions import (
    AttachmentSizeLimitError,
    AttachmentValidationError,
)
from app.utils.helpers import human_readable_size, normalize_extension

_HEAD_SIZE = 16

# Сигнатуры исполняемых/потенциально опасных файлов.
_DANGEROUS_SIGNATURES: tuple[bytes, ...] = (
    b"MZ",  # Windows PE
    b"\x7fELF",  # Linux ELF
    b"\xfe\xed\xfa\xce",  # Mach-O 32-bit
    b"\xfe\xed\xfa\xcf",  # Mach-O 64-bit
    b"\xca\xfe\xba\xbe",  # Java class / Mach-O fat
)

# Ожидаемые сигнатуры для распространённых форматов.
_EXPECTED_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".bmp": (b"BM",),
    ".zip": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    ".docx": (b"PK\x03\x04",),
    ".xlsx": (b"PK\x03\x04",),
    ".pptx": (b"PK\x03\x04",),
    ".odt": (b"PK\x03\x04",),
    ".ods": (b"PK\x03\x04",),
    ".odp": (b"PK\x03\x04",),
    ".7z": (b"7z\xbc\xaf\x27\x1c",),
    ".rar": (b"Rar!\x1a\x07",),
    ".gz": (b"\x1f\x8b",),
}


@dataclass(frozen=True, slots=True)
class ValidatedAttachment:
    """Результат успешной валидации файла."""

    path: Path
    filename: str
    extension: str
    size: int
    mime_type: str | None


def validate_attachment_file(file_path: str | Path, config: Config) -> ValidatedAttachment:
    """Проверяет файл и возвращает нормализованные метаданные.

    :raises AttachmentValidationError: файл отсутствует, не читается или
        нарушает политику расширений/содержимого.
    :raises AttachmentSizeLimitError: размер превышает лимит конфигурации.
    """

    path = Path(file_path).expanduser()

    try:
        if not path.exists():
            raise AttachmentValidationError(f"File does not exist: {path}")
        if not path.is_file():
            raise AttachmentValidationError(f"Path is not a regular file: {path}")
    except OSError as exc:
        raise AttachmentValidationError(f"Cannot access file {path}: {exc}") from exc

    filename = path.name
    if not filename:
        raise AttachmentValidationError("File name must not be empty")

    extension = normalize_extension(filename)
    if not config.is_extension_allowed(extension):
        display = extension or "<none>"
        raise AttachmentValidationError(
            f"File extension '{display}' is not allowed"
        )

    try:
        size = path.stat().st_size
    except OSError as exc:
        raise AttachmentValidationError(f"Cannot read file size: {exc}") from exc

    if size == 0 and not config.allow_empty_files:
        raise AttachmentValidationError("Empty files are not allowed")

    if size > config.max_attachment_size:
        raise AttachmentSizeLimitError(
            "Attachment size "
            f"{human_readable_size(size)} exceeds the limit "
            f"{human_readable_size(config.max_attachment_size)}"
        )

    head = _read_head(path)
    _verify_content(path, extension, head)

    mime_type, _encoding = mimetypes.guess_type(filename)
    return ValidatedAttachment(
        path=path,
        filename=filename,
        extension=extension,
        size=size,
        mime_type=mime_type,
    )


def _read_head(path: Path) -> bytes:
    try:
        with path.open("rb") as handle:
            return handle.read(_HEAD_SIZE)
    except OSError as exc:
        raise AttachmentValidationError(f"File is not readable: {exc}") from exc


def _verify_content(path: Path, extension: str, head: bytes) -> None:
    if any(head.startswith(signature) for signature in _DANGEROUS_SIGNATURES):
        raise AttachmentValidationError(
            f"Executable content is not allowed: {path.name}"
        )

    if extension == ".webp":
        if not (len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP"):
            raise AttachmentValidationError(
                f"File content does not match extension '{extension}': {path.name}"
            )
        return

    expected = _EXPECTED_SIGNATURES.get(extension)
    if expected is None:
        return
    if not any(head.startswith(signature) for signature in expected):
        raise AttachmentValidationError(
            f"File content does not match extension '{extension}': {path.name}"
        )


__all__ = ["ValidatedAttachment", "validate_attachment_file"]
