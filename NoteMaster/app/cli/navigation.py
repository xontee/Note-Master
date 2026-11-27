"""Стек навигации CLI.

Экраны не знают, кто их открыл. Они возвращают одну из команд :class:`Nav`,
а стек решает, что делать: остаться, вернуться назад, уйти на Dashboard или
завершить приложение. Это исключает копирование навигационной логики в
каждом экране.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - только для типов
    from app.cli.views.base import BaseView


class Nav(Enum):
    """Команда навигации, которую возвращает экран."""

    STAY = "stay"
    BACK = "back"
    HOME = "home"
    EXIT = "exit"


class Navigator:
    """Стек экранов: текущий всегда последний."""

    def __init__(self) -> None:
        self._stack: list["BaseView"] = []

    def reset(self, root: "BaseView") -> None:
        """Задаёт корневой экран (Dashboard)."""

        self._stack = [root]

    @property
    def current(self) -> "BaseView":
        if not self._stack:
            raise RuntimeError("Navigator is not initialized")
        return self._stack[-1]

    @property
    def can_go_back(self) -> bool:
        return len(self._stack) > 1

    def push(self, view: "BaseView") -> None:
        self._stack.append(view)

    def pop(self) -> None:
        if self.can_go_back:
            self._stack.pop()

    def home(self) -> None:
        """Возвращает на Dashboard, сбрасывая вложенные экраны."""

        if self._stack:
            del self._stack[1:]


__all__ = ["Nav", "Navigator"]
