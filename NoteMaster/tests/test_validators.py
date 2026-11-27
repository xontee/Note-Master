"""Тесты валидации файлов вложений."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import Config
from app.core.exceptions import (
    AttachmentSizeLimitError,
    AttachmentValidationError,
)
from app.attachments.validators import validate_attachment_file


def test_valid_txt_file(make_file: callable) -> None:
    f = make_file("readme.txt", b"Hello, world!")
    result = validate_attachment_file(f, Config.default())
    assert result.filename == "readme.txt"
    assert result.extension == ".txt"
    assert result.size == len(b"Hello, world!")
    assert result.mime_type == "text/plain"


def test_empty_file_rejected(make_file: callable) -> None:
    f = make_file("empty.txt", b"")
    config = Config.default()
    with pytest.raises(AttachmentValidationError):
        validate_attachment_file(f, config)


def test_empty_file_allowed_when_configured(make_file: callable) -> None:
    f = make_file("empty.txt", b"")
    config = Config(data_dir=Config.default().data_dir, allow_empty_files=True)
    result = validate_attachment_file(f, config)
    assert result.size == 0


def test_disallowed_extension(make_file: callable) -> None:
    f = make_file("script.exe", b"MZ fake")
    config = Config.default()
    with pytest.raises(AttachmentValidationError):
        validate_attachment_file(f, config)


def test_whitelist_rejects_unknown(make_file: callable) -> None:
    f = make_file("doc.md", b"markdown content")
    config = Config(
        data_dir=Config.default().data_dir,
        allowed_extensions=frozenset({".txt", ".pdf"}),
    )
    with pytest.raises(AttachmentValidationError):
        validate_attachment_file(f, config)


def test_pdf_signature_mismatch(make_file: callable) -> None:
    f = make_file("fake.pdf", b"not a pdf at all")
    config = Config(
        data_dir=Config.default().data_dir, allowed_extensions=frozenset({".pdf"})
    )
    with pytest.raises(AttachmentValidationError):
        validate_attachment_file(f, config)


def test_dangerous_executable_in_text_extension(make_file: callable) -> None:
    f = make_file("looks_safe.txt", b"MZ fake executable")
    with pytest.raises(AttachmentValidationError):
        validate_attachment_file(f, Config.default())


def test_size_limit_exceeded(make_file: callable) -> None:
    f = make_file("big.txt", b"x" * 1000)
    config = Config(data_dir=Config.default().data_dir, max_attachment_size=500)
    with pytest.raises(AttachmentSizeLimitError):
        validate_attachment_file(f, config)


def test_directory_rejected(tmp_path: Path) -> None:
    with pytest.raises(AttachmentValidationError):
        validate_attachment_file(tmp_path, Config.default())


def test_nonexistent_file() -> None:
    with pytest.raises(AttachmentValidationError):
        validate_attachment_file("/nonexistent/file.txt", Config.default())
