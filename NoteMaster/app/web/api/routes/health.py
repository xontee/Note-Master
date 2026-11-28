"""Служебный эндпоинт состояния приложения.

``GET /api/v1/health`` — минимальная диагностика для проверки, что приложение
собрано, контейнер инициализирован, а хранилище читается. Используется
frontend-проверкой доступности бэкенда и дымовыми тестами.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app import __version__
from app.core.exceptions import NoteMasterError
from app.services.integrity_service import IntegrityService
from app.web.dependencies import get_integrity_service
from pydantic import BaseModel

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    """Ответ проверки доступности."""

    status: str
    storage: str
    version: str


@router.get("/health", response_model=HealthResponse, summary="Health check")
def health(
    integrity: IntegrityService = Depends(get_integrity_service),
) -> HealthResponse:
    try:
        report = integrity.check()
        storage = "operational" if report.is_healthy else "attention_required"
    except NoteMasterError:
        storage = "unavailable"

    return HealthResponse(status="ok", storage=storage, version=__version__)


__all__ = ["router", "HealthResponse"]
