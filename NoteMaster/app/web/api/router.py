"""Агрегатор версионированного API-роутера.

Единая точка подключения всех эндпоинтов ``/api/v1``. В будущем ``/api/v2``
добавляется отдельным роутером без изменения Core и существующих маршрутов.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.web.api.routes import attachments, dashboard, health, notes, search

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(notes.router, prefix="/notes")
api_router.include_router(search.router)
api_router.include_router(attachments.router, prefix="/notes")
api_router.include_router(dashboard.router)

# Зарегистрированные домены (Phase 3):
# - /api/v1/health
# - /api/v1/notes (CRUD + pin + filters + pagination)
# - /api/v1/search
# - /api/v1/notes/{id}/attachments (upload/download/delete)
# - /api/v1/attachments/{id}/download
# - /api/v1/dashboard


__all__ = ["api_router"]
