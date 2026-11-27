"""Повторно используемые компоненты терминального интерфейса."""

from __future__ import annotations

from app.cli.components.console import Console, enable_windows_ansi
from app.cli.components.formatting import (
    describe_error,
    display_width,
    format_timestamp,
    parse_bool,
    tags_text,
    truncate,
    wrap_block,
)
from app.cli.components.prompts import InputCancelled, Prompter
from app.cli.components.tables import render_table

__all__ = [
    "Console",
    "enable_windows_ansi",
    "Prompter",
    "InputCancelled",
    "render_table",
    "display_width",
    "truncate",
    "wrap_block",
    "format_timestamp",
    "tags_text",
    "parse_bool",
    "describe_error",
]
