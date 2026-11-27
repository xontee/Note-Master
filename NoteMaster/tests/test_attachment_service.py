"""Тесты сервиса вложений AttachmentService."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import (
    AttachmentLimitExceededError,
    AttachmentNotFoundError,
    AttachmentSizeLimitError,
    AttachmentStorageError,
    AttachmentValidationError,
    NoteNotFoundError,
    ValidationError,
)
from app.services.attachment_service import AttachmentService


@pytest.fixture
def service(attachment_service: AttachmentService) -> AttachmentService:
    """Псевдоним фикстуры для краткости в этом модуле."""

    return attachment_service


def test_add_attachment(
    service: AttachmentService,
    make_file: callable,
    note_service,
) -> None:
    note = note_service.create_note("Заметка с вложением")

    file_path = make_file("report.txt", b"some content here")
    attachment = service.add_attachment(note.id, file_path)

    assert attachment.filename == "report.txt"
    assert attachment.extension == ".txt"
    assert attachment.size == len(b"some content here")
    assert attachment.mime_type == "text/plain"
    assert service._storage.exists(attachment.relative_path)

    # Проверить, что заметка обновлена в репозитории
    refreshed = note_service.get_note(note.id)
    assert len(refreshed.attachments) == 1
    assert refreshed.attachments[0].id == attachment.id


def test_add_multiple_attachments(
    service: AttachmentService,
    make_file: callable,
    note_service,
) -> None:
    note = note_service.create_note("Два файла")
    f1 = make_file("a.txt", b"content A")
    f2 = make_file("b.txt", b"content B")

    att1 = service.add_attachment(note.id, f1)
    att2 = service.add_attachment(note.id, f2)

    assert len(note_service.get_note(note.id).attachments) == 2
    assert att1.filename != att2.filename


def test_add_same_original_names(
    service: AttachmentService,
    make_file: callable,
    note_service,
) -> None:
    """Два файла с одинаковым именем сохраняются отдельно."""

    note = note_service.create_note("Дубликат имени")
    f1 = make_file("report.txt", b"first", directory=service._config.data_dir / "d1")
    f2 = make_file("report.txt", b"second", directory=service._config.data_dir / "d2")

    att1 = service.add_attachment(note.id, f1)
    att2 = service.add_attachment(note.id, f2)

    assert att1.relative_path != att2.relative_path
    assert len(note_service.get_note(note.id).attachments) == 2


def test_get_attachment(
    service: AttachmentService,
    make_file: callable,
    note_service,
) -> None:
    note = note_service.create_note("Заметка")
    f = make_file("file.txt", b"data")
    attachment = service.add_attachment(note.id, f)

    found = service.get_attachment(note.id, attachment.id)
    assert found.id == attachment.id
    assert found.filename == "file.txt"


def test_list_attachments(
    service: AttachmentService,
    make_file: callable,
    note_service,
) -> None:
    note = note_service.create_note("Заметка")
    f1 = make_file("a.txt", b"a")
    f2 = make_file("b.txt", b"b")

    service.add_attachment(note.id, f1)
    service.add_attachment(note.id, f2)

    attachments = service.list_attachments(note.id)
    assert len(attachments) == 2


def test_remove_attachment(
    service: AttachmentService,
    make_file: callable,
    note_service,
) -> None:
    note = note_service.create_note("Заметка")
    f = make_file("file.txt", b"data")
    attachment = service.add_attachment(note.id, f)

    service.remove_attachment(note.id, attachment.id)

    with pytest.raises(AttachmentNotFoundError):
        service.get_attachment(note.id, attachment.id)
    assert not service._storage.exists(attachment.relative_path)


def test_export_to_file(
    service: AttachmentService,
    make_file: callable,
    note_service,
    tmp_path,
) -> None:
    note = note_service.create_note("Заметка")
    f = make_file("file.txt", b"export me")
    attachment = service.add_attachment(note.id, f)

    dest = tmp_path / "exported.txt"
    exported = service.export_attachment(note.id, attachment.id, dest)

    assert exported.exists()
    assert exported.read_bytes() == b"export me"


def test_export_to_directory(
    service: AttachmentService,
    make_file: callable,
    note_service,
    tmp_path,
) -> None:
    note = note_service.create_note("Заметка")
    f = make_file("file.txt", b"data")
    attachment = service.add_attachment(note.id, f)

    dest_dir = tmp_path / "exports"
    dest_dir.mkdir()
    exported = service.export_attachment(note.id, attachment.id, dest_dir)

    assert exported.exists()
    assert exported.name == "file.txt"


def test_export_overwrite_allowed(
    service: AttachmentService,
    make_file: callable,
    note_service,
    tmp_path,
) -> None:
    note = note_service.create_note("Заметка")
    f = make_file("file.txt", b"data")
    attachment = service.add_attachment(note.id, f)

    dest = tmp_path / "file.txt"
    dest.write_bytes(b"old")

    exported = service.export_attachment(note.id, attachment.id, dest, overwrite=True)
    assert exported.exists()


def test_export_overwrite_denied_by_default(
    service: AttachmentService,
    make_file: callable,
    note_service,
    tmp_path,
) -> None:
    note = note_service.create_note("Заметка")
    f = make_file("file.txt", b"data")
    attachment = service.add_attachment(note.id, f)

    dest = tmp_path / "file.txt"
    dest.write_bytes(b"old")

    with pytest.raises(AttachmentStorageError):
        service.export_attachment(note.id, attachment.id, dest)


def test_missing_source_file(
    service: AttachmentService,
    note_service,
) -> None:
    note = note_service.create_note("Заметка")
    with pytest.raises(AttachmentValidationError):
        service.add_attachment(note.id, "/nonexistent/file.txt")


def test_remove_missing_physical_file(
    service: AttachmentService,
    make_file: callable,
    note_service,
) -> None:
    """Если физический файл отсутствует — метаданные всё равно удаляются."""

    note = note_service.create_note("Заметка")
    f = make_file("file.txt", b"data")
    attachment = service.add_attachment(note.id, f)

    # Удалить физический файл напрямую
    service._storage.delete(attachment.relative_path)
    assert not service._storage.exists(attachment.relative_path)

    # Удалить метаданные — не должно вызвать ошибку
    service.remove_attachment(note.id, attachment.id)

    with pytest.raises(AttachmentNotFoundError):
        service.get_attachment(note.id, attachment.id)


def test_size_limit_exceeded(
    service: AttachmentService,
    make_file: callable,
    note_service,
) -> None:
    limited_config = service._config.__class__(
        data_dir=service._config.data_dir,
        max_attachment_size=10,
        max_attachments_per_note=service._config.max_attachments_per_note,
        allowed_extensions=service._config.allowed_extensions,
        forbidden_extensions=service._config.forbidden_extensions,
    )
    limited_service = AttachmentService(
        service._repository, service._storage, limited_config
    )
    note = note_service.create_note("Заметка")
    f = make_file("file.txt", b"12345678901234567890")  # 20 байт

    with pytest.raises(AttachmentSizeLimitError):
        limited_service.add_attachment(note.id, f)


def test_attachment_count_limit_exceeded(
    service: AttachmentService,
    make_file: callable,
    note_service,
) -> None:
    limited_config = service._config.__class__(
        data_dir=service._config.data_dir,
        max_attachment_size=service._config.max_attachment_size,
        max_attachments_per_note=1,
        allowed_extensions=service._config.allowed_extensions,
        forbidden_extensions=service._config.forbidden_extensions,
    )
    limited_service = AttachmentService(
        service._repository, service._storage, limited_config
    )
    note = note_service.create_note("Заметка")
    f1 = make_file("a.txt", b"a")
    f2 = make_file("b.txt", b"b")

    limited_service.add_attachment(note.id, f1)
    with pytest.raises(AttachmentLimitExceededError):
        limited_service.add_attachment(note.id, f2)


def test_disallowed_extension(
    service: AttachmentService,
    make_file: callable,
    note_service,
) -> None:
    limited_config = service._config.__class__(
        data_dir=service._config.data_dir,
        allowed_extensions=frozenset({".txt"}),
    )
    limited_service = AttachmentService(
        service._repository, service._storage, limited_config
    )
    note = note_service.create_note("Заметка")
    # Создадим файл с сигнатурой .pdf
    f = make_file("document.pdf", b"%PDF-1.4 fake pdf")

    with pytest.raises(AttachmentValidationError):
        limited_service.add_attachment(note.id, f)


def test_attachment_exists_true(
    service: AttachmentService,
    make_file: callable,
    note_service,
) -> None:
    note = note_service.create_note("Заметка")
    f = make_file("file.txt", b"data")
    attachment = service.add_attachment(note.id, f)
    assert service.attachment_exists(note.id, attachment.id)


def test_attachment_exists_false(
    service: AttachmentService,
    note_service,
) -> None:
    note = note_service.create_note("Заметка")
    assert not service.attachment_exists(note.id, uuid4())


def test_copy_error_leaves_no_metadata(
    service: AttachmentService,
    make_file: callable,
    note_service,
    monkeypatch,
) -> None:
    """Если shutil.copy2 падает — в хранилище и в JSON ничего не добавляется."""

    import shutil as _shutil

    note = note_service.create_note("Заметка")
    f = make_file("file.txt", b"data")

    original_copy2 = _shutil.copy2

    def boom(*args, **kwargs):
        raise OSError("simulated copy failure")

    monkeypatch.setattr(_shutil, "copy2", boom)

    with pytest.raises(AttachmentStorageError):
        service.add_attachment(note.id, f)

    note = note_service.get_note(note.id)
    assert note.attachments == []
    assert service._storage.list_relative_paths() == []

    monkeypatch.setattr(_shutil, "copy2", original_copy2)


def test_json_save_error_after_copy(
    service: AttachmentService,
    make_file: callable,
    note_service,
    monkeypatch,
) -> None:
    """Если JSON save упал после копирования — файл очищается."""

    note = note_service.create_note("Заметка")
    f = make_file("file.txt", b"data")

    original_update = service._repository.update

    def raise_error(note):
        raise RuntimeError("simulated write failure")

    monkeypatch.setattr(service._repository, "update", raise_error)

    with pytest.raises(RuntimeError):
        service.add_attachment(note.id, f)

    # Файл должен быть очищен
    note = note_service.get_note(note.id)
    assert note.attachments == []
    assert service._storage.list_relative_paths() == []

    monkeypatch.setattr(service._repository, "update", original_update)


def test_delete_note_cleans_attachments(
    note_service,
    make_file: callable,
    attachment_service,
) -> None:
    """Удаление заметки физически удаляет все вложения."""

    note = note_service.create_note("Заметка")
    f1 = make_file("a.txt", b"a")
    f2 = make_file("b.txt", b"b")
    attachment_service.add_attachment(note.id, f1)
    attachment_service.add_attachment(note.id, f2)

    assert len(note_service.get_note(note.id).attachments) == 2
    files_before = set(attachment_service._storage.list_relative_paths())
    assert len(files_before) == 2

    result = note_service.delete_note(note.id)
    assert result.deleted

    files_after = set(attachment_service._storage.list_relative_paths())
    assert files_after - files_before == set()  # никаких сирот


def test_validate_attachment(
    service: AttachmentService,
    make_file: callable,
) -> None:
    f = make_file("file.txt", b"content")
    validated = service.validate_attachment(f)
    assert validated.filename == "file.txt"
    assert validated.size == len(b"content")


def test_path_traversal_in_relative_path(
    service: AttachmentService,
    make_file: callable,
    note_service,
) -> None:
    """Попытка использовать путь с traversal отклоняется."""

    note = note_service.create_note("Заметка")
    f = make_file("file.txt", b"data")
    attachment = service.add_attachment(note.id, f)

    with pytest.raises(AttachmentStorageError):
        service._storage.resolve("../etc/passwd")


def test_integrity_healthy_after_operations(
    service: AttachmentService,
    make_file: callable,
    note_service,
    integrity_service,
) -> None:
    """После всех операций целостность должна быть в порядке."""

    note = note_service.create_note("Заметка")
    f1 = make_file("a.txt", b"first")
    f2 = make_file("b.txt", b"second")
    service.add_attachment(note.id, f1)
    service.add_attachment(note.id, f2)

    # Удалить одно вложение
    att_to_remove = note_service.get_note(note.id).attachments[0]
    service.remove_attachment(note.id, att_to_remove.id)

    # Удалить заметку (и второе вложение)
    note_service.delete_note(note.id)

    report = integrity_service.check()
    assert report.is_healthy


def test_remove_nonexistent_attachment(
    service: AttachmentService,
    note_service,
) -> None:
    note = note_service.create_note("Заметка")
    with pytest.raises(AttachmentNotFoundError):
        service.remove_attachment(note.id, uuid4())


def test_get_nonexistent_attachment(
    service: AttachmentService,
    note_service,
) -> None:
    note = note_service.create_note("Заметка")
    with pytest.raises(AttachmentNotFoundError):
        service.get_attachment(note.id, uuid4())


def test_remove_from_nonexistent_note(
    service: AttachmentService,
    make_file: callable,
    note_service,
) -> None:
    f = make_file("file.txt", b"data")
    attachment = service.add_attachment(note_service.create_note("A").id, f)

    with pytest.raises(NoteNotFoundError):
        service.remove_attachment(uuid4(), attachment.id)
