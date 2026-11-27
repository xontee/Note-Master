"""Тесты проверки целостности хранилища."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from app.models.note import Note
from app.services.attachment_service import AttachmentService
from app.services.integrity_service import IntegrityService
from app.services.note_service import NoteService


def _create_note_with_attachment(
    note_svc: NoteService,
    att_svc: AttachmentService,
    make_file: callable,
) -> Note:
    note = note_svc.create_note("Заметка для целостности")
    att_svc.add_attachment(note.id, make_file("file.txt", b"content"))
    return note


def test_integrity_healthy(
    note_service: NoteService,
    attachment_service: AttachmentService,
    make_file: callable,
    integrity_service: IntegrityService,
) -> None:
    _create_note_with_attachment(note_service, attachment_service, make_file)

    report = integrity_service.check()
    assert report.is_healthy
    assert report.total_notes == 1
    assert report.total_attachments == 1


def test_integrity_missing_file(
    note_service: NoteService,
    attachment_service: AttachmentService,
    make_file: callable,
    integrity_service: IntegrityService,
) -> None:
    note = _create_note_with_attachment(note_service, attachment_service, make_file)
    attachment = note_service.get_note(note.id).attachments[0]

    # Удаляем физический файл напрямую
    attachment_service._storage.delete(attachment.relative_path)

    report = integrity_service.check()
    assert not report.is_healthy
    assert len(report.missing_files) == 1
    assert report.missing_files[0].id == attachment.id


def test_integrity_orphan_file(
    note_service: NoteService,
    integrity_service: IntegrityService,
    make_file: callable,
    tmp_path: Path,
) -> None:
    # Создаём "сироту" напрямую в хранилище
    storage = note_service._attachment_storage
    source = tmp_path / "orphan.txt"
    source.write_bytes(b"orphan data")
    note_id = note_service.create_note("Заметка").id
    storage.save(source, note_id, uuid4(), ".txt")

    report = integrity_service.check()
    assert not report.is_healthy
    assert len(report.orphan_files) >= 1


def test_integrity_summary(
    note_service: NoteService,
    attachment_service: AttachmentService,
    make_file: callable,
    integrity_service: IntegrityService,
) -> None:
    _create_note_with_attachment(note_service, attachment_service, make_file)
    report = integrity_service.check()
    summary = report.summary()
    assert "Заметок: 1" in summary
    assert "Вложений в метаданных: 1" in summary
    assert report.is_healthy
