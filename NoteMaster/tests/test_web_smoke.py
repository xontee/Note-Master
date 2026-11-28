"""Быстрая проверка сборки Web-приложения (Phase 2)."""
import tempfile
import pathlib
from fastapi.testclient import TestClient
from app.core.config import Config
from app.web.config import WebConfig
from app.web.container import build_container
from app.web.main import create_app


def test_health_endpoint() -> None:
    d = pathlib.Path(tempfile.mkdtemp())
    cfg = WebConfig(core=Config(data_dir=d))
    app = create_app(cfg, build_container(cfg))

    with TestClient(app) as c:
        r = c.get("/api/v1/health")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"


def test_404_format() -> None:
    d = pathlib.Path(tempfile.mkdtemp())
    cfg = WebConfig(core=Config(data_dir=d))
    app = create_app(cfg, build_container(cfg))

    with TestClient(app) as c:
        r = c.get("/api/v1/nonexistent")
        assert r.status_code == 404
        data = r.json()
        # Единый формат ErrorResponse
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        # Не раскрываем внутренние пути
        body_text = str(data)
        assert "data/" not in body_text


if __name__ == "__main__":
    test_health_endpoint()
    print("✓ health OK")
    test_404_format()
    print("✓ 404 format OK")
