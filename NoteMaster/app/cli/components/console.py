"""Единый слой вывода CLI NoteMaster.

Весь вывод приложения проходит через :class:`Console`. Это даёт одинаковый
визуальный стиль и позволяет тестам подменять функцию вывода, не перехватывая
stdout. Цвета включаются только для интерактивного терминала: при
перенаправлении вывода и в тестах строки остаются чистыми.
"""

from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Callable, Sequence

from app.cli.components.formatting import display_width, truncate
from app.cli.components.tables import render_table

RESET = "\x1b[0m"

_STYLES: dict[str, str] = {
    "bold": "1",
    "dim": "2",
    "blue": "94",
    "cyan": "96",
    "green": "92",
    "yellow": "93",
    "red": "91",
    "gray": "90",
}

MIN_WIDTH = 60
MAX_WIDTH = 120

WriteFn = Callable[[str], None]


def supports_color(stream: object) -> bool:
    """Определяет, уместно ли использовать ANSI-цвета."""

    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return bool(getattr(stream, "isatty", lambda: False)())


def enable_windows_ansi() -> None:
    """Включает обработку ANSI-последовательностей в консоли Windows.

    Без этого современные версии Windows показывают escape-коды как текст.
    Сбой настройки не должен мешать работе приложения, поэтому ошибки
    игнорируются: интерфейс останется читаемым и без цвета.
    """

    if os.name != "nt" or not supports_color(sys.stdout):
        return

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:  # noqa: BLE001 - оформление не является критичным
        return


class Console:
    """Вывод с единым стилем: заголовки, панели, таблицы, уведомления."""

    def __init__(
        self,
        write: WriteFn | None = None,
        *,
        color: bool | None = None,
        width: int | None = None,
    ) -> None:
        self._write: WriteFn = write or print
        if color is None:
            # При подменённой функции вывода (тесты, скрипты) цвета выключаем.
            color = supports_color(sys.stdout) and write is None
        self.color = bool(color)

        if width is None:
            width = shutil.get_terminal_size(fallback=(100, 24)).columns
        self.width = max(MIN_WIDTH, min(int(width), MAX_WIDTH))

    # ------------------------------------------------------------------ база
    def write(self, text: str = "") -> None:
        self._write(text)

    def line(self, text: str = "") -> None:
        """Синоним :meth:`write` для читаемости в экранах."""

        self._write(text)

    def blank(self) -> None:
        self.write("")

    def style(self, text: str, *styles: str) -> str:
        """Окрашивает текст, если цвета включены."""

        if not self.color or not styles:
            return text
        prefix = "".join(
            f"\x1b[{_STYLES[style]}m" for style in styles if style in _STYLES
        )
        return f"{prefix}{text}{RESET}"

    def rule(self, char: str = "─") -> None:
        self.write(self.style(char * self.width, "gray"))

    # ------------------------------------------------------------- структура
    def app_header(self, title: str, subtitle: str, version: str) -> None:
        """Шапка приложения в рамке."""

        inner = min(self.width - 4, 62)
        border = self.style("│", "blue")
        right = f"v{version}"
        gap = max(1, inner - display_width(title) - display_width(right))

        self.write(self.style("╭" + "─" * (inner + 2) + "╮", "blue"))
        self.write(
            f"{border} {self.style(title, 'bold', 'blue')}"
            f"{' ' * gap}{self.style(right, 'gray')} {border}"
        )
        self.write(
            f"{border} {self.style(subtitle, 'gray')}"
            f"{' ' * max(0, inner - display_width(subtitle))} {border}"
        )
        self.write(self.style("╰" + "─" * (inner + 2) + "╯", "blue"))

    def heading(self, text: str) -> None:
        self.write(self.style(text, "bold", "blue"))

    def panel(
        self,
        title: str,
        lines: Sequence[str],
        *,
        border: str = "blue",
    ) -> None:
        """Компактная панель с заголовком и содержимым."""

        title_plain = title.upper()
        content = list(lines) or [""]
        inner = max(
            [display_width(title_plain), 20] + [display_width(line) for line in content]
        )
        inner = min(inner, self.width - 4)

        self.write(self.style("╭" + "─" * (inner + 2) + "╮", border))
        self.write(
            self._row(
                self.style(title_plain, "bold", border),
                display_width(title_plain),
                inner,
                border,
            )
        )
        self.write(self.style("├" + "─" * (inner + 2) + "┤", border))
        for line in content:
            clipped = truncate(line, inner) if display_width(line) > inner else line
            self.write(self._row(clipped, display_width(clipped), inner, border))
        self.write(self.style("╰" + "─" * (inner + 2) + "╯", border))

    def _row(self, content: str, plain_width: int, inner: int, border: str) -> str:
        padding = " " * max(0, inner - plain_width)
        return f"{self.style('│', border)} {content}{padding} {self.style('│', border)}"

    # ------------------------------------------------------------ уведомления
    def success(self, text: str) -> None:
        self.write(f"  {self.style('✔', 'green')} {text}")

    def error(self, text: str) -> None:
        self.write(f"  {self.style('✖', 'red')} {text}")

    def warning(self, text: str) -> None:
        self.write(f"  {self.style('!', 'yellow')} {text}")

    def info(self, text: str) -> None:
        self.write(f"  {self.style('•', 'blue')} {text}")

    def muted(self, text: str) -> None:
        self.write(f"  {self.style(text, 'gray')}")

    # ---------------------------------------------------------------- таблицы
    def table(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[str]],
        *,
        aligns: Sequence[str] | None = None,
        min_widths: Sequence[int] | None = None,
    ) -> None:
        """Печатает таблицу: заголовок синий, разделитель серый."""

        lines = render_table(
            headers,
            rows,
            max_width=self.width,
            aligns=aligns,
            min_widths=min_widths,
        )
        if not lines:
            return
        self.write(self.style(lines[0], "bold", "blue"))
        self.write(self.style(lines[1], "gray"))
        for line in lines[2:]:
            self.write(line)


__all__ = ["Console", "WriteFn", "enable_windows_ansi", "supports_color"]
