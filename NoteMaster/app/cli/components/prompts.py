"""Ввод пользователя: единые правила для всех экранов."""

from __future__ import annotations

from collections.abc import Callable

from app.cli.components.console import Console

InputFn = Callable[[str], str]


class InputCancelled(Exception):
    """Пользователь прервал ввод (Ctrl+C, EOF или исчерпанный input_fn)."""


class Prompter:
    """Обёртка над ``input`` с валидацией формата ответа.

    Бизнес-валидация (например, существование файла) сюда не входит — её
    выполняют сервисы Core. Здесь проверяется только то, что относится к
    пользовательскому вводу: пустая строка, yes/no, выбор из диапазона.
    """

    def __init__(self, console: Console, input_fn: InputFn | None = None) -> None:
        self._console = console
        self._input: InputFn = input_fn or input

    def _read(self, prompt: str) -> str:
        try:
            return self._input(prompt)
        except (EOFError, KeyboardInterrupt, StopIteration) as exc:
            raise InputCancelled from exc

    def ask(self, label: str, *, default: str | None = None) -> str:
        """Читает строку. Пустой ввод возвращает ``default`` (если задан)."""

        prompt = label
        if default is not None:
            prompt += f" [{default}]"
        value = (self._read(f"{prompt}: ") or "").strip()
        if not value and default is not None:
            return default
        return value

    def required(self, label: str) -> str:
        """Читает непустую строку, повторяя запрос при ошибке."""

        while True:
            value = self.ask(label)
            if value:
                return value
            self._console.warning("Значение не может быть пустым.")

    def confirm(self, label: str, *, default: bool = False) -> bool:
        """Запрашивает подтверждение y/n."""

        hint = "Y/n" if default else "y/N"
        while True:
            value = self.ask(f"{label} ({hint})")
            if not value:
                return default
            lowered = value.lower()
            if lowered in {"y", "yes", "д", "да", "1"}:
                return True
            if lowered in {"n", "no", "н", "нет", "0"}:
                return False
            self._console.warning("Ответьте «y» (да) или «n» (нет).")

    def multiline(self, label: str) -> str:
        """Читает многострочный текст до пустой строки."""

        self._console.muted(f"{label}. Пустая строка — завершить ввод.")
        lines: list[str] = []
        while True:
            line = self._read("  > ")
            if line == "":
                break
            lines.append(line)
        return "\n".join(lines)


__all__ = ["InputCancelled", "Prompter", "InputFn"]
