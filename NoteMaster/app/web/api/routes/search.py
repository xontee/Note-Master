"""Эндпоинт полнотекстового поиска.

Использует ``NoteService.search_notes`` — второй движок не создаётся.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.services.note_service import NoteService
from app.web.dependencies import get_note_service
from app.web.mapper import note_to_response
from app.web.schemas.notes import NoteListResponse

router = APIRouter(tags=["search"])


@router.get(
    "/search",
    response_model=NoteListResponse,
    summary="Поиск заметок",
    description=(
        "Регистронезависимый поиск по заголовку, содержимому, тегам и категории. "
        "Пустой запрос возвращает все заметки (эквивалентно GET /notes без фильтров)."
    ),
)
def search_notes(
    *,
    service: NoteService = Depends(get_note_service),
    q: str = Query(..., min_length=1, max_length=200, description="Поисковый запрос."),
    sort_by: str | None = Query("updated_at", description="Поле сортировки."),
    descending: bool = Query(True, description="Обратный порядок?"),
    limit: int | None = Query(None, ge=1, le=100, description="Размер страницы."),
    offset: int = Query(0, ge=0, description="Смещение."),
) -> NoteListResponse:
    notes = service.search_notes(q, sort_by=sort_by, descending=descending)
    total = len(notes)
    page = notes[offset : offset + (limit or len(notes))]
    return NoteListResponse(
        items=[note_to_response(n) for n in page],
        total=total,
        limit=limit,
        offset=offset,
    )


__all__ = ["router"]
