"""Эндпоинт Dashboard-агрегации.

Агрегация считается в API-слое (согласованное решение Phase 2).
Core не меняется — ``NoteService.get_all_notes`` отдаёт список,
который маппится на DTO и подсчитывает статистику.
"""

from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends

from app.services.note_service import NoteService
from app.web.dependencies import get_note_service
from app.web.mapper import note_to_response
from app.web.schemas.dashboard import (
    CategoryStat,
    DashboardResponse,
    TagStat,
)

router = APIRouter(tags=["dashboard"])


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Dashboard-статистика",
    description=(
        "Сводка: количество заметок, закреплённых, вложений, категорий, тегов. "
        "Включает топ-5 недавно изменённых заметок."
    ),
)
def dashboard(
    service: NoteService = Depends(get_note_service),
) -> DashboardResponse:
    notes = service.get_all_notes(sort_by="updated_at", descending=True)

    total = len(notes)
    pinned = sum(1 for n in notes if n.is_pinned)
    attachments = sum(len(n.attachments) for n in notes)

    categories: dict[str, int] = {}
    tags: dict[str, int] = Counter()
    for note in notes:
        if note.category:
            categories[note.category] = categories.get(note.category, 0) + 1
        for tag in note.tags:
            tags[tag] += 1

    return DashboardResponse(
        total_notes=total,
        pinned_notes=pinned,
        total_attachments=attachments,
        total_categories=len(categories),
        total_tags=len(tags),
        categories=[
            CategoryStat(name=name, count=count)
            for name, count in sorted(categories.items(), key=lambda x: -x[1])
        ],
        tags=[
            TagStat(name=name, count=count)
            for name, count in sorted(tags.items(), key=lambda x: (-x[1], x[0]))
        ],
        recent_notes=[note_to_response(n) for n in notes[:5]],
    )


__all__ = ["router"]
