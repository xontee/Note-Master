"""Отрисовка компактных таблиц с учётом ширины терминала."""

from __future__ import annotations

from collections.abc import Sequence

from app.cli.components.formatting import display_width, pad, truncate

_GAP = "  "


def render_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    *,
    max_width: int,
    aligns: Sequence[str] | None = None,
    min_widths: Sequence[int] | None = None,
) -> list[str]:
    """Возвращает готовые строки таблицы: заголовок, разделитель, данные.

    Ширины колонок сначала вычисляются по содержимому, затем «сжимаются»,
    чтобы таблица помещалась в терминал. Сначала уменьшаются самые широкие
    колонки — так заголовок заметки остаётся читаемым.
    """

    header_cells = [str(header) for header in headers]
    column_count = len(header_cells)
    if column_count == 0:
        return []

    data_rows = [[str(cell) for cell in row] for row in rows]
    column_aligns = list(aligns or ["left"] * column_count)
    if len(column_aligns) != column_count:
        column_aligns = ["left"] * column_count

    minimums = list(min_widths or [3] * column_count)
    if len(minimums) != column_count:
        minimums = [3] * column_count

    widths = [display_width(header) for header in header_cells]
    for row in data_rows:
        for index in range(column_count):
            widths[index] = max(widths[index], display_width(row[index]))
    for index in range(column_count):
        widths[index] = max(widths[index], minimums[index])

    gap_width = len(_GAP) * (column_count - 1)

    while sum(widths) + gap_width > max_width:
        candidates = [
            index for index in range(column_count) if widths[index] > minimums[index]
        ]
        if not candidates:
            break
        widest = max(candidates, key=lambda index: widths[index])
        widths[widest] -= 1

    def build_line(cells: Sequence[str]) -> str:
        return _GAP.join(
            pad(
                truncate(cells[index], widths[index]),
                widths[index],
                column_aligns[index],
            )
            for index in range(column_count)
        )

    lines = [
        build_line(header_cells),
        _GAP.join("─" * width for width in widths),
    ]
    lines.extend(build_line(row) for row in data_rows)
    return lines


__all__ = ["render_table"]
