"""Базовый экран CLI.

Экран умеет:
* отрисовать себя;
* прочитать команду;
* обработать глобальные команды навигации;
* вернуть :class:`Nav`, который интерпретирует стек навигации.

Вся обработка ошибок Core сосредоточена в :meth:`BaseView._guard`, поэтому
экраны не повторяют ``try/except`` в каждом действии.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

from app.cli.context import AppContext
from app.cli.components.prompts import InputCancelled
from app.cli.menu import Menu
from app.cli.navigation import Nav
from app.core.exceptions import NoteMasterError

_EXIT_COMMANDS = frozenset({"q", "quit", "exit", "выход"})
_HOME_COMMANDS = frozenset({"m", "home", "00"})


class BaseView(ABC):
    """Абстрактный экран с меню и обработчиком команды."""

    title: str = ""

    #: Что означает команда «0» на этом экране. На Dashboard это выход,
    #: на остальных экранах — возврат назад.
    zero_nav: Nav = Nav.BACK

    def __init__(self, context: AppContext) -> None:
        self.ctx = context

    # ------------------------------------------------------------------ вывод
    def render(self) -> None:
        console = self.ctx.console
        console.blank()
        console.heading(self.title)
        self.render_body()
        console.blank()
        self.build_menu().render(console)

    def render_body(self) -> None:
        """Содержимое экрана до меню. По умолчанию пусто."""

    # ---------------------------------------------------------------- команды
    @abstractmethod
    def build_menu(self) -> Menu:
        """Возвращает меню текущего состояния экрана."""

    @abstractmethod
    def handle(self, key: str) -> Nav:
        """Обрабатывает команду меню."""

    def run_once(self) -> Nav:
        """Один цикл: отрисовать, прочитать команду, выполнить."""

        self.render()
        command = self.ctx.prompter.ask("Команда")
        if not command:
            self.ctx.console.warning("Введите номер команды из меню.")
            return Nav.STAY

        lowered = command.lower()
        if lowered in _EXIT_COMMANDS:
            return Nav.EXIT
        if lowered in _HOME_COMMANDS:
            return Nav.HOME
        if command == "0":
            return self.zero_nav

        if command not in self.build_menu().keys():
            self.ctx.console.warning("Неизвестная команда. Введите номер из меню.")
            return Nav.STAY

        return self._guard(lambda: self.handle(command))

    # --------------------------------------------------------------- защита
    def _guard(self, action: Callable[[], Nav]) -> Nav:
        try:
            return action()
        except InputCancelled:
            raise
        except NoteMasterError as exc:
            self.ctx.report_error(exc)
            return Nav.STAY
        except OSError as exc:
            self.ctx.console.error(f"Ошибка файловой системы: {exc}")
            return Nav.STAY
        except Exception as exc:  # noqa: BLE001 - CLI не должен падать
            if self.ctx.config.debug:
                raise
            self.ctx.console.error(f"Непредвиденная ошибка: {exc}")
            return Nav.STAY


__all__ = ["BaseView"]
