"""Эндпоинты заметок: CRUD, закрепление, фильтрация, сортировка, пагинация.

Все данные из Core — объекты ``Note`` — проходят через ``note_to_response``,
чтобы внутренние поля не утекали в HTTP.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from uuid import UUID

from app.core.exceptions import (
    DuplicateNoteError,
    NoteNotFoundError,
    ValidationError,
)
from app.services.note_service import NoteService
from app.web.dependencies import get_note_service
from app.web.mapper import note_to_response
from app.web.schemas.notes import (
    NoteCreateRequest,
    NoteListResponse,
    NoteResponse,
    NoteUpdateRequest,
    PinRequest,
)

router = APIRouter(tags=["notes"])

# Допустимые поля сортировки — дублируются в сервисе, но API знает о них
# заранее для валидации.
_ALLOWED_SORT = frozenset({"created_at", "updated_at", "title"})


# ─────────────────────────────────────────────────────────────── Коллекция ───


@router.post(
    "",
    response_model=NoteResponse,
    status_code=201,
    summary="Создать заметку",
    description=(
        "Создаёт новую заметку. Поля ``tags`` нормализуются "
        "(дубликаты убираются, регистр не учитывается)."
    ),
)
def create_note(
    body: NoteCreateRequest,
    service: NoteService = Depends(get_note_service),
) -> NoteResponse:
    note = service.create_note(
        title=body.title,
        content=body.content,
        tags=body.tags,
        category=body.category,
        is_pinned=body.is_pinned,
    )
    return note_to_response(note)


@router.get(
    "",
    response_model=NoteListResponse,
    summary="Список заметок",
    description=(
        "Возвращает список заметок с пагинацией, фильтрацией и сортировкой. "
        "Фильтрация выполняется через ``tag``, ``category``, ``pinned``. "
        "Сортировка через ``sort_by`` (по умолчанию ``updated_at desc``)."
    ),
)
def list_notes(
    *,
    service: NoteService = Depends(get_note_service),
    q: str | None = Query(None, description="Текстовый поиск (подстрока)."),
    tag: str | None = Query(None, description="Фильтр по тегу."),
    category: str | None = Query(None, description="Фильтр по категории."),
    pinned: bool | None = Query(None, description="Фильтр по закреплению."),
    sort_by: str | None = Query("updated_at", description="Поле сортировки."),
    descending: bool = Query(True, description="Обратный порядок?"),
    limit: int | None = Query(None, ge=1, le=100, description="Размер страницы."),
    offset: int = Query(0, ge=0, description="Смещение от начала."),
) -> NoteListResponse:
    notes = service.filter_notes(
        query=q,
        tag=tag,
        category=category,
        pinned=pinned,
        sort_by=sort_by,
        descending=descending,
    )
    total = len(notes)
    # Пагинация на уровне API — Core не меняем.
    page = notes[offset : offset + (limit or len(notes))]
    return NoteListResponse(
        items=[note_to_response(n) for n in page],
        total=total,
        limit=limit,
        offset=offset,
    )


# ─────────────────────────────────────────────────────────────── Элемент ─────


@router.get(
    "/{note_id}",
    response_model=NoteResponse,
    summary="Просмотр заметки",
)
def get_note(note_id: UUID, service: NoteService = Depends(get_note_service)) -> NoteResponse:
    note = service.get_note(note_id)
    return note_to_response(note)


@router.put(
    "/{note_id}",
    response_model=NoteResponse,
    summary="Полное обновление",
    description=(
        "PUT: передаются только те поля, которые нужно изменить. "
        "Отсутствующие поля игнорируются (не обнуляются). "
        "Для очистки категории передайте ``category: null``."
    ),
)
def update_note(
    note_id: UUID,
    body: NoteUpdateRequest,
    service: NoteService = Depends(get_note_service),
) -> NoteResponse:
    # ``exclude_unset`` — ключевой момент: только явно переданные поля
    # передаются в сервис, что сохраняет семантику ``UNSET``.
    updates = body.model_dump(exclude_unset=True)
    note = service.update_note(note_id, **updates)
    return note_to_response(note)


@router.delete(
    "/{note_id}",
    status_code=204,
    summary="Удалить заметку",
    description="Удаляет заметку и все её вложения (best-effort).",
)
def delete_note(
    note_id: UUID,
    service: NoteService = Depends(get_note_service),
) -> None:
    result = service.delete_note(note_id, remove_attachments=True)
    if result.failed_attachments:
        # Сбои очистки файлов не препятствуют удалению, но логируем.
        # В продакшене это уйдёт в лог-систему.
        pass


# ─────────────────────────────────────────────────────────────── Закрепление ───

# PATCH используется для целевых операций (pin/unpin), а не частичного
# обновления всех полей — для этого есть PUT.


@router.patch(
    "/{note_id}/pin",
    response_model=NoteResponse,
    summary="Переключить закрепление",
    description="PATCH-запрос с ``is_pinned: true/false`` переключает статус.",
)
def toggle_pin(
    note_id: UUID,
    body: PinRequest,
    service: NoteService = Depends(get_note_service),
) -> NoteResponse:
    if body.is_pinned:
        note = service.pin_note(note_id)
    else:
        note = service.unpin_note(note_id)
    return note_to_response(note)


__all__ = ["router"]
