"""Pydantic-схема ответа Dashboard.

Агрегация считается в API-слое (согласованное решение), Core не меняется.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.web.schemas.notes import NoteResponse


class CategoryStat(BaseModel):
    """Статистика по одной категории."""

    name: str
    count: int


class TagStat(BaseModel):
    """Статистика по одному тегу."""

    name: str
    count: int


class DashboardResponse(BaseModel):
    """Сводная статистика для главного экрана."""

    total_notes: int
    pinned_notes: int
    total_attachments: int
    total_categories: int
    total_tags: int
    categories: list[CategoryStat] = Field(default_factory=list)
    tags: list[TagStat] = Field(default_factory=list)
    recent_notes: list[NoteResponse] = Field(
        default_factory=list,
        description="Недавно изменённые заметки (до 5).",
    )


__all__ = ["CategoryStat", "TagStat", "DashboardResponse"]
