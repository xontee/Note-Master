#!/usr/bin/env python
"""Точка запуска NoteMaster Web v1.0 (FastAPI + Uvicorn).

Запуск:
    python run_web.py                 # http://127.0.0.1:8000
    NOTEMASTER_WEB_PORT=9000 python run_web.py
    NOTEMASTER_WEB_DEBUG=1 python run_web.py

Документация OpenAPI: http://127.0.0.1:8000/api/v1/docs
"""

from __future__ import annotations

import uvicorn

from app.web.config import WebConfig


def main() -> None:
    config = WebConfig.from_env()
    # reload намеренно выключен: Web и CLI работают с одним JSON-хранилищем,
    # а перезагрузка воркера во время записи недопустима (см. ADR про конкурентный доступ).
    uvicorn.run(
        "app.web.main:app_factory",
        factory=True,
        host=config.host,
        port=config.port,
        reload=False,
        workers=1,
    )


if __name__ == "__main__":
    main()
