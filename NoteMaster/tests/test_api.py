"""Комплексные API-тесты: CRUD заметок, вложений, поиска и Dashboard.

Тесты используют временные каталоги и не трогают реальные данные пользователя.
"""

import tempfile
import pathlib
import pytest
from fastapi.testclient import TestClient

from app.core.config import Config
from app.web.config import WebConfig
from app.web.container import build_container
from app.web.main import create_app


@pytest.fixture
def app() -> TestClient:
    """Возвращает TestClient с активным lifespan-контейнером.

    Используется ``yield`` с контекстным менеджером, чтобы lifespan
    FastAPI выполнялся (создаёт ``app.state.container``) и корректно
    завершался после каждого теста.
    """

    d = pathlib.Path(tempfile.mkdtemp())
    cfg = WebConfig(core=Config(data_dir=d))
    container = build_container(cfg)
    client = TestClient(create_app(cfg, container))
    with client:
        yield client


# ═══════════════════════════════════════════════════════════ Notes CRUD ═══════


def test_create_and_get(app: TestClient) -> None:
    r = app.post(
        "/api/v1/notes",
        json={
            "title": "API Note",
            "content": "Содержимое",
            "tags": ["api", "test"],
            "category": "Работа",
        },
    )
    assert r.status_code == 201, r.json()
    data = r.json()
    assert data["title"] == "API Note"
    assert data["content"] == "Содержимое"
    assert set(data["tags"]) == {"api", "test"}
    assert data["category"] == "Работа"
    assert data["is_pinned"] is False
    assert data["attachments"] == []
    note_id = data["id"]

    r2 = app.get(f"/api/v1/notes/{note_id}")
    assert r2.status_code == 200
    assert r2.json()["id"] == note_id


def test_list_and_pagination(app: TestClient) -> None:
    for i in range(5):
        app.post("/api/v1/notes", json={"title": f"Note {i}"})

    r = app.get("/api/v1/notes", params={"limit": 2, "offset": 0})
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5

    r2 = app.get("/api/v1/notes", params={"limit": 2, "offset": 3})
    assert r2.status_code == 200
    assert len(r2.json()["items"]) == 2


def test_update_partial(app: TestClient) -> None:
    r = app.post("/api/v1/notes", json={"title": "Original"})
    note_id = r.json()["id"]

    r2 = app.put(f"/api/v1/notes/{note_id}", json={"title": "Updated"})
    assert r2.status_code == 200
    assert r2.json()["title"] == "Updated"
    assert r2.json()["content"] == ""  # не затронуто

    # Очистка категории через null
    r3 = app.put(f"/api/v1/notes/{note_id}", json={"category": None})
    assert r3.json()["category"] is None


def test_delete_204(app: TestClient) -> None:
    r = app.post("/api/v1/notes", json={"title": "Delete me"})
    note_id = r.json()["id"]

    r2 = app.delete(f"/api/v1/notes/{note_id}")
    assert r2.status_code == 204

    r3 = app.get(f"/api/v1/notes/{note_id}")
    assert r3.status_code == 404


def test_pin_toggle(app: TestClient) -> None:
    r = app.post("/api/v1/notes", json={"title": "Pin test"})
    note_id = r.json()["id"]

    r2 = app.patch(f"/api/v1/notes/{note_id}/pin", json={"is_pinned": True})
    assert r2.json()["is_pinned"] is True

    r3 = app.patch(f"/api/v1/notes/{note_id}/pin", json={"is_pinned": False})
    assert r3.json()["is_pinned"] is False


def test_404_for_missing_note(app: TestClient) -> None:
    from uuid import uuid4

    r = app.get(f"/api/v1/notes/{uuid4()}")
    assert r.status_code == 404
    body = r.json()
    assert body["error"]["code"] == "NOTE_NOT_FOUND"


# ═══════════════════════════════════════════════════════════ Search ═══════════


def test_search(app: TestClient) -> None:
    app.post("/api/v1/notes", json={"title": "Python", "content": "ООП"})
    app.post("/api/v1/notes", json={"title": "JavaScript", "content": "Прототипы"})

    r = app.get("/api/v1/search", params={"q": "python"})
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["title"] == "Python"


# ═══════════════════════════════════════════════════════════ Dashboard ═══════


def test_dashboard(app: TestClient) -> None:
    app.post("/api/v1/notes", json={"title": "A", "tags": ["x"], "category": "Work"})
    app.post("/api/v1/notes", json={"title": "B", "is_pinned": True})

    r = app.get("/api/v1/dashboard")
    assert r.status_code == 200
    data = r.json()
    assert data["total_notes"] == 2
    assert data["pinned_notes"] == 1
    assert data["total_categories"] == 1
    assert data["total_tags"] == 1
    assert len(data["recent_notes"]) == 2


# ═══════════════════════════════════════════════════════════ Error format ═════


def test_error_response_format(app: TestClient) -> None:
    """Все ошибки имеют единый формат {"error": {"code": ..., "message": ...}}."""

    # 422 — невалидный запрос
    r = app.post("/api/v1/notes", json={"title": ""})
    assert r.status_code == 422
    body = r.json()
    assert "error" in body
    assert body["error"]["code"] == "REQUEST_VALIDATION_ERROR"

    # 404 — несуществующий ресурс
    from uuid import uuid4

    r = app.delete(f"/api/v1/notes/{uuid4()}")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOTE_NOT_FOUND"

    # Не раскрываем системные пути
    assert "data/" not in str(r.json())
