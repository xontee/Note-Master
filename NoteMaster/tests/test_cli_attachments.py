"""Тесты CLI: вложения и базовые компоненты интерфейса."""

from __future__ import annotations

from pathlib import Path

from app.cli.components.console import Console
from app.cli.components.formatting import (
    describe_error,
    display_width,
    parse_bool,
    truncate,
)
from app.cli.components.tables import render_table
from app.cli.navigation import Nav, Navigator
from app.core.exceptions import NoteNotFoundError, ValidationError


# -------------------------------------------------------------- Attachments
def test_add_attachment(run_cli, note_service, attachment_service, make_file) -> None:
    note = note_service.create_note("С вложением")
    source = make_file("sample.txt", b"hello")

    text = run_cli(["5", "1", "1", str(source)])

    assert "Вложение добавлено" in text
    assert len(attachment_service.list_attachments(note.id)) == 1


def test_add_attachment_missing_file(
    run_cli, note_service, attachment_service
) -> None:
    note = note_service.create_note("С вложением")

    text = run_cli(["5", "1", "1", str(Path("C:/no/such/file.txt"))])

    assert "Файл не найден" in text
    assert attachment_service.list_attachments(note.id) == []


def test_add_attachment_rejected_extension(
    run_cli, note_service, attachment_service, make_file
) -> None:
    note = note_service.create_note("С вложением")
    source = make_file("script.exe", b"MZ fake executable")

    text = run_cli(["5", "1", "1", str(source)])

    assert "не прошло проверку" in text
    assert attachment_service.list_attachments(note.id) == []


def test_list_attachments(run_cli, note_service, attachment_service, make_file) -> None:
    note = note_service.create_note("С вложением")
    attachment_service.add_attachment(note.id, make_file("list.txt", b"data"))

    text = run_cli(["5", "2", "1"])

    assert "ВЛОЖЕНИЯ" in text
    assert "list.txt" in text
    assert "OK" in text


def test_attachment_info(run_cli, note_service, attachment_service, make_file) -> None:
    note = note_service.create_note("С вложением")
    attachment_service.add_attachment(note.id, make_file("doc.txt", b"data"))

    text = run_cli(["5", "3", "1", "1"])

    assert "doc.txt" in text
    assert "MIME-тип" in text
    assert "Статус" in text
    assert "файл доступен" in text


def test_remove_attachment(
    run_cli, note_service, attachment_service, make_file
) -> None:
    note = note_service.create_note("С вложением")
    attachment_service.add_attachment(note.id, make_file("remove.txt", b"data"))

    text = run_cli(["5", "4", "1", "1", "y"])

    assert "удалено" in text
    assert attachment_service.list_attachments(note.id) == []


def test_remove_attachment_cancelled(
    run_cli, note_service, attachment_service, make_file
) -> None:
    note = note_service.create_note("С вложением")
    attachment_service.add_attachment(note.id, make_file("keep.txt", b"data"))

    text = run_cli(["5", "4", "1", "1", "n"])

    assert "Удаление отменено" in text
    assert len(attachment_service.list_attachments(note.id)) == 1


def test_export_attachment(
    run_cli,
    note_service,
    attachment_service,
    make_file,
    tmp_path: Path,
) -> None:
    note = note_service.create_note("С вложением")
    attachment_service.add_attachment(note.id, make_file("export.txt", b"payload"))
    destination = tmp_path / "exported.txt"

    text = run_cli(["5", "5", "1", "1", str(destination)])

    assert "экспортировано" in text
    assert destination.read_bytes() == b"payload"


def test_check_attachment_availability(
    run_cli, note_service, attachment_service, make_file
) -> None:
    note = note_service.create_note("С вложением")
    attachment_service.add_attachment(note.id, make_file("ok.txt", b"data"))

    text = run_cli(["5", "6"])

    assert "ДОСТУПНОСТЬ ВЛОЖЕНИЙ" in text
    assert "Все файлы вложений доступны" in text


# ---------------------------------------------------------------- Компоненты
def test_display_width_cyrillic() -> None:
    assert display_width("Привет") == 6
    assert display_width("ABC") == 3


def test_truncate_respects_width() -> None:
    assert truncate("abcdef", 4) == "abc…"
    assert truncate("abc", 5) == "abc"


def test_parse_bool() -> None:
    assert parse_bool("y", default=False) is True
    assert parse_bool("да", default=False) is True
    assert parse_bool("n", default=True) is False
    assert parse_bool("", default=True) is True
    assert parse_bool("непонятно", default=False) is False


def test_render_table_fits_width() -> None:
    lines = render_table(("A", "B"), [("x" * 50, "y" * 50)], max_width=40)
    assert len(lines) == 3  # заголовок, разделитель, строка данных
    assert all(display_width(line) <= 40 for line in lines)


def test_render_table_cyrillic_alignment() -> None:
    lines = render_table(("Имя", "Значение"), [("Заметка", "12")], max_width=80)
    assert display_width(lines[0]) == display_width(lines[2])


def test_console_without_color_has_no_ansi() -> None:
    output: list[str] = []
    console = Console(output.append, color=False, width=80)
    console.success("ok")
    console.error("bad")
    console.table(("H",), [("v",)])
    assert not any("\x1b" in line for line in output)


def test_console_color_adds_ansi() -> None:
    output: list[str] = []
    console = Console(output.append, color=True, width=80)
    console.success("ok")
    assert "\x1b" in output[0]


def test_describe_error_uses_core_types() -> None:
    title, detail = describe_error(NoteNotFoundError("нет такой"))
    assert "не найдена" in title.lower()
    assert "нет такой" in detail

    title, _ = describe_error(ValidationError("плохо"))
    assert "Некорректные данные" in title


def test_navigator_stack() -> None:
    navigator = Navigator()
    root = object()
    child = object()

    navigator.reset(root)  # type: ignore[arg-type]
    assert navigator.current is root
    assert navigator.can_go_back is False

    navigator.push(child)  # type: ignore[arg-type]
    assert navigator.current is child
    assert navigator.can_go_back is True

    navigator.pop()
    assert navigator.current is root

    navigator.push(child)  # type: ignore[arg-type]
    navigator.home()
    assert navigator.current is root


def test_nav_enum_values() -> None:
    assert Nav.BACK.value == "back"
    assert Nav.EXIT.value == "exit"
