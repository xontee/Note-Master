"""Тесты JSON-хранилища."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.exceptions import SerializationError, StorageError
from app.storage.json_storage import JsonStorage


def test_ensure_initialized_creates_file(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "notes.json"
    storage = JsonStorage(path)
    storage.ensure_initialized()

    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["notes"] == []


def test_read_missing_file_creates_it(tmp_path: Path) -> None:
    storage = JsonStorage(tmp_path / "notes.json")
    payload = storage.read()
    assert payload["notes"] == []
    assert storage.path.is_file()


def test_write_and_read_roundtrip(tmp_path: Path) -> None:
    storage = JsonStorage(tmp_path / "notes.json")
    payload = {"version": 1, "notes": [{"id": "1", "title": "Кириллица"}]}
    storage.write(payload)
    assert storage.read() == payload

    raw = storage.path.read_text(encoding="utf-8")
    assert "Кириллица" in raw  # ensure_ascii=False


def test_corrupted_json_not_overwritten(tmp_path: Path) -> None:
    path = tmp_path / "notes.json"
    path.write_text("{ this is not json", encoding="utf-8")
    storage = JsonStorage(path)

    with pytest.raises(SerializationError):
        storage.read()

    assert path.read_text(encoding="utf-8") == "{ this is not json"


def test_empty_file_is_treated_as_corrupted(tmp_path: Path) -> None:
    path = tmp_path / "notes.json"
    path.write_text("   ", encoding="utf-8")
    storage = JsonStorage(path)

    with pytest.raises(SerializationError):
        storage.read()
    assert path.read_text(encoding="utf-8") == "   "


def test_invalid_structure_rejected(tmp_path: Path) -> None:
    path = tmp_path / "notes.json"
    path.write_text('{"notes": "oops"}', encoding="utf-8")
    storage = JsonStorage(path)

    with pytest.raises(SerializationError):
        storage.read()


def test_write_rejects_invalid_payload(tmp_path: Path) -> None:
    storage = JsonStorage(tmp_path / "notes.json")
    with pytest.raises(SerializationError):
        storage.write({"notes": [1, 2, 3]})  # type: ignore[list-item]


def test_atomic_write_leaves_no_temp_files(tmp_path: Path) -> None:
    storage = JsonStorage(tmp_path / "notes.json")
    storage.write({"version": 1, "notes": []})
    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == []


def test_serialization_error_keeps_previous_content(tmp_path: Path) -> None:
    storage = JsonStorage(tmp_path / "notes.json")
    good = {"version": 1, "notes": [{"id": "ok"}]}
    storage.write(good)

    broken = {"version": 1, "notes": [{"id": object()}]}
    with pytest.raises(SerializationError):
        storage.write(broken)  # type: ignore[dict-item]

    assert storage.read() == good


def test_storage_path_must_be_file(tmp_path: Path) -> None:
    directory = tmp_path / "notes.json"
    directory.mkdir()
    storage = JsonStorage(directory)
    with pytest.raises(StorageError):
        storage.ensure_initialized()
