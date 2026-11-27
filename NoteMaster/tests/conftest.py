"""Общие фикстуры тестов NoteMaster."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import Config
from app.repositories.json_repository import JsonNoteRepository
from app.services.attachment_service import AttachmentService
from app.services.integrity_service import IntegrityService
from app.services.note_service import NoteService
from app.storage.file_storage import LocalAttachmentStorage
from app.storage.json_storage import JsonStorage


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return Config(data_dir=tmp_path / "data")


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path / "data"


@pytest.fixture
def storage(config: Config) -> JsonStorage:
    instance = JsonStorage(config.notes_file, encoding=config.encoding)
    instance.ensure_initialized()
    return instance


@pytest.fixture
def repository(storage: JsonStorage) -> JsonNoteRepository:
    return JsonNoteRepository(storage)


@pytest.fixture
def attachment_storage(config: Config) -> LocalAttachmentStorage:
    return LocalAttachmentStorage(config.attachments_dir)


@pytest.fixture
def note_service(
    repository: JsonNoteRepository,
    attachment_storage: LocalAttachmentStorage,
) -> NoteService:
    return NoteService(repository, attachment_storage)


@pytest.fixture
def attachment_service(
    repository: JsonNoteRepository,
    attachment_storage: LocalAttachmentStorage,
    config: Config,
) -> AttachmentService:
    return AttachmentService(repository, attachment_storage, config)


@pytest.fixture
def integrity_service(
    repository: JsonNoteRepository,
    attachment_storage: LocalAttachmentStorage,
) -> IntegrityService:
    return IntegrityService(repository, attachment_storage)


@pytest.fixture
def make_file(tmp_path: Path):
    """Фабрика временных файлов для загрузки во вложения."""

    def _make(
        name: str = "sample.txt",
        content: bytes = b"hello world",
        directory: Path | None = None,
    ) -> Path:
        base = Path(directory) if directory is not None else tmp_path / "uploads"
        base.mkdir(parents=True, exist_ok=True)
        path = base / name
        path.write_bytes(content)
        return path

    return _make


@pytest.fixture
def run_cli(config, note_service, attachment_service, integrity_service):
    """Запускает CLI с заданной последовательностью ввода и возвращает вывод.

    Ввод подменяется, вывод собирается в список, поэтому тесты не зависят от
    реального терминала и не трогают пользовательские данные.
    """

    from app.cli.interface import NoteMasterCLI

    def _run(inputs: list[str]) -> str:
        output: list[str] = []
        pending = list(inputs)

        def input_fn(_prompt: str) -> str:
            if not pending:
                raise EOFError
            return pending.pop(0)

        cli = NoteMasterCLI(
            note_service,
            attachment_service,
            config,
            integrity_service=integrity_service,
            input_fn=input_fn,
            output_fn=output.append,
            color=False,
            width=100,
        )
        cli.run()
        return "\n".join(output)

    return _run
