"""Описание и отрисовка меню.

Меню — данные, а не набор ``print``. Благодаря этому навигация и проверка
команд работают одинаково на всех экранах.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.cli.components.console import Console

DEFAULT_HINT = "0 — назад · M — главный экран · Q — выход"


@dataclass(frozen=True, slots=True)
class MenuItem:
    """Одна команда меню."""

    key: str
    label: str


@dataclass(frozen=True, slots=True)
class Menu:
    """Набор команд с заголовком и подсказкой по навигации."""

    title: str
    items: tuple[MenuItem, ...]
    hint: str = DEFAULT_HINT

    def keys(self) -> frozenset[str]:
        return frozenset(item.key for item in self.items)

    def render(self, console: Console) -> None:
        console.line(console.style(self.title.upper(), "bold", "blue"))
        key_width = max((len(item.key) for item in self.items), default=1)
        for item in self.items:
            key = console.style(item.key.rjust(key_width), "cyan")
            console.line(f"  {key}  {item.label}")
        console.muted(self.hint)


__all__ = ["MenuItem", "Menu", "DEFAULT_HINT"]
