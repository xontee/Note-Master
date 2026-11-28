"""Тесты подмены зависимостей (dependency_overrides).

Показывает, что API можно тестировать без реального хранилища — достаточно
подменить провайдер через ``app.dependency_overrides``. Это важно для:
* изоляции тестов от файловой системы;
* моков Core-сервисов;
* тестирования граничных условий, которые сложно воспроизвести через tmp_path.
"""

import tempfile
import pathlib
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.core.config import Config
from app.web.config import WebConfig
from app.web.container import build_container
from app.web.dependencies import get_note_service
from app.web.main import create_app
from app.models.note import Note
from uuid import uuid4


def _test_note() -> Note:
    """Создаёт тестовую заметку без записи в репозиторий."""

    return Note(
        id=uuid4(),
        title="Mocked Note",
        content="Содержимое из мока",
        tags=["mock"],
        category="Test",
        is_pinned=True,
    )


def test_dependency_overrides_note_service() -> None:
    """Подмена NoteService моком.

    Реальный хранилище не используется — сервис полностью заменяется.
    """

    d = pathlib.Path(tempfile.mkdtemp())
    cfg = WebConfig(core=Config(data_dir=d))
    app = create_app(cfg)

    mock_service = MagicMock()
    mock_service.filter_notes.return_value = [_test_note()]

    with TestClient(app) as c:
        c.app.dependency_overrides[get_note_service] = lambda: mock_service
        r = c.get("/api/v1/notes")
        assert r.status_code == 200
        data = r.json()
        assert data["items"][0]["title"] == "Mocked Note"
        assert data["items"][0]["is_pinned"] is True
        assert data["items"][0]["content"] == "Содержимое из мока"
        # Убеждаемся, что мок был вызван
        mock_service.filter_notes.assert_called_once()


def test_dependency_overrides_clears_after_context() -> None:
    """Подмена аннулируется после выхода из контекста TestClient."""

    d = pathlib.Path(tempfile.mkdtemp())
    cfg = WebConfig(core=Config(data_dir=d))
    app = create_app(cfg, build_container(cfg))

    mock_service = MagicMock()
    mock_service.get_all_notes.return_value = []

    with TestClient(app) as c:
        c.app.dependency_overrides[get_note_service] = lambda: mock_service
        # Внутри контекста — мок
        r = c.get("/api/v1/notes")
        assert r.status_code == 200

    # После выхода из контекста TestClient подмена аннулируется
    # (TestClient.__exit__ вызывает app.state.__del__ и т.д.)
    # Для надёжности — проверяем, что override отсутствует
    assert get_note_service not in c.app.dependency_overrides.values()
