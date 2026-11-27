"""Тесты файлового хранилища вложений."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import AttachmentStorageError
from app.storage.file_storage import LocalAttachmentStorage
from uuid import uuid4


def _make_storage(tmp_path: Path) -> LocalAttachmentStorage:
    return LocalAttachmentStorage(tmp_path / "attachments")


def test_save_and_exists(tmp_path: Path) -> None:
    storage = _make_storage(tmp_path)
    source = tmp_path / "source.txt"
    source.write_bytes(b"hello")

    note_id = uuid4()
    att_id = uuid4()
    relative = storage.save(source, note_id, att_id, ".txt")

    assert relative is not None
    assert storage.exists(relative)

    resolved = storage.resolve(relative)
    assert resolved.exists()
    assert resolved.read_bytes() == b"hello"


def test_save_creates_nested_directories(tmp_path: Path) -> None:
    storage = _make_storage(tmp_path)
    source = tmp_path / "source.txt"
    source.write_bytes(b"data")

    note_id = uuid4()
    att_id = uuid4()
    relative = storage.save(source, note_id, att_id, ".txt")

    # Проверяем структуру YYYY/MM/NOTE_UUID/ATTACHMENT_UUID.txt
    parts = Path(relative).parts
    assert len(parts) == 4
    assert parts[0].isdigit() and len(parts[0]) == 4  # год
    assert parts[1].isdigit() and len(parts[1]) == 2  # месяц
    assert len(parts[2]) == 36  # UUID заметки
    assert parts[3].startswith(str(att_id))


def test_delete_removes_file(tmp_path: Path) -> None:
    storage = _make_storage(tmp_path)
    source = tmp_path / "source.txt"
    source.write_bytes(b"data")

    note_id = uuid4()
    att_id = uuid4()
    relative = storage.save(source, note_id, att_id, ".txt")

    assert storage.delete(relative) is True
    assert storage.exists(relative) is False


def test_delete_nonexistent_returns_false(tmp_path: Path) -> None:
    storage = _make_storage(tmp_path)
    assert storage.delete("2024/01/000/att.txt") is False


def test_export_file(tmp_path: Path) -> None:
    storage = _make_storage(tmp_path)
    source = tmp_path / "source.txt"
    source.write_bytes(b"export me")

    note_id = uuid4()
    att_id = uuid4()
    relative = storage.save(source, note_id, att_id, ".txt")

    dest = tmp_path / "exports" / "copy.txt"
    exported = storage.export(relative, dest)

    assert exported.exists()
    assert exported.read_bytes() == b"export me"


def test_export_overwrite_denied(tmp_path: Path) -> None:
    storage = _make_storage(tmp_path)
    source = tmp_path / "source.txt"
    source.write_bytes(b"data")

    note_id = uuid4()
    att_id = uuid4()
    relative = storage.save(source, note_id, att_id, ".txt")

    dest = tmp_path / "dest.txt"
    dest.write_text("old")

    with pytest.raises(AttachmentStorageError):
        storage.export(relative, dest)


def test_export_overwrite_allowed(tmp_path: Path) -> None:
    storage = _make_storage(tmp_path)
    source = tmp_path / "source.txt"
    source.write_bytes(b"data")

    note_id = uuid4()
    att_id = uuid4()
    relative = storage.save(source, note_id, att_id, ".txt")

    dest = tmp_path / "dest.txt"
    dest.write_text("old")

    exported = storage.export(relative, dest, overwrite=True)
    assert exported.exists()


def test_resolve_traversal_absolute(tmp_path: Path) -> None:
    storage = _make_storage(tmp_path)
    with pytest.raises(AttachmentStorageError):
        storage.resolve("/etc/passwd")


def test_resolve_traversal_dotdot(tmp_path: Path) -> None:
    storage = _make_storage(tmp_path)
    with pytest.raises(AttachmentStorageError):
        storage.resolve("../../etc/passwd")


def test_resolve_traversal_encoded(tmp_path: Path) -> None:
    storage = _make_storage(tmp_path)
    with pytest.raises(AttachmentStorageError):
        storage.resolve("2024/01/note/../../etc/passwd")


def test_get_size(tmp_path: Path) -> None:
    storage = _make_storage(tmp_path)
    source = tmp_path / "source.txt"
    source.write_bytes(b"12345")

    note_id = uuid4()
    att_id = uuid4()
    relative = storage.save(source, note_id, att_id, ".txt")

    assert storage.get_size(relative) == 5


def test_list_relative_paths(tmp_path: Path) -> None:
    storage = _make_storage(tmp_path)
    source1 = tmp_path / "a.txt"
    source1.write_bytes(b"a")
    source2 = tmp_path / "b.txt"
    source2.write_bytes(b"b")

    note1 = uuid4()
    note2 = uuid4()
    r1 = storage.save(source1, note1, uuid4(), ".txt")
    r2 = storage.save(source2, note2, uuid4(), ".txt")

    paths = storage.list_relative_paths()
    assert len(paths) == 2
    assert r1 in paths
    assert r2 in paths


def test_list_relative_paths_excludes_parts(tmp_path: Path) -> None:
    storage = _make_storage(tmp_path)
    source = tmp_path / "a.txt"
    source.write_bytes(b"a")

    note_id = uuid4()
    att_id = uuid4()
    relative = storage.save(source, note_id, att_id, ".txt")

    # Создаём имитацию незавершённого копирования
    base = storage.base_dir.resolve()
    target = storage.resolve(relative)
    part = target.with_name(target.name + ".part")
    part.write_text("partial")

    paths = storage.list_relative_paths()
    assert len(paths) == 1
    assert relative in paths


def test_delete_cleans_empty_dirs(tmp_path: Path) -> None:
    storage = _make_storage(tmp_path)
    source = tmp_path / "a.txt"
    source.write_bytes(b"a")

    note_id = uuid4()
    att_id = uuid4()
    relative = storage.save(source, note_id, att_id, ".txt")

    storage.delete(relative)

    # Каталоги YYYY/MM/NOTE_UUID должны быть удалены
    assert not storage.base_dir.exists() or not any(
        storage.base_dir.rglob("*")
    )
