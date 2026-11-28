"""Общие HTTP-схемы: формат ошибки и пагинация.

``ErrorResponse`` — единый формат тела ошибки для всего API. Он намеренно не
раскрывает traceback и системные пути: наружу уходят только стабильный
машинный ``code`` и безопасное ``message``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Детали одной ошибки."""

    code: str = Field(..., description="Стабильный машинный код ошибки.")
    message: str = Field(..., description="Безопасное для пользователя описание.")


class ErrorResponse(BaseModel):
    """Каноническое тело HTTP-ошибки.

    Пример::

        {"error": {"code": "NOTE_NOT_FOUND", "message": "Note was not found"}}
    """

    error: ErrorDetail


class PageMeta(BaseModel):
    """Метаданные постраничной выборки."""

    total: int = Field(..., description="Общее число элементов без пагинации.")
    limit: int | None = Field(None, description="Размер страницы, если задан.")
    offset: int = Field(0, description="Смещение от начала отсортированного списка.")


class NoteListResponse(BaseModel):
    """Обёртка списка заметок с метаданными пагинации.

    Конкретный элемент задаётся в модуле ``schemas.notes``; здесь живёт только
    обёртка, общая для всех коллекционных эндпоинтов.
    """

    items: list[Any]
    meta: PageMeta


def error_body(code: str, message: str) -> dict[str, Any]:
    """Возвращает готовое к сериализации тело ошибки."""

    return ErrorResponse(error=ErrorDetail(code=code, message=message)).model_dump()


__all__ = [
    "ErrorDetail",
    "ErrorResponse",
    "PageMeta",
    "NoteListResponse",
    "error_body",
]
