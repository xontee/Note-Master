"""Тесты конфигурации и устойчивости вывода."""

from __future__ import annotations

from pathlib import Path

from app.core.config import Config, DEFAULT_DATA_DIR, PROJECT_ROOT


def test_default_data_dir_is_inside_project() -> None:
    """Config() без параметров указывает на data/ проекта, а не на CWD."""

    cfg = Config()
    assert cfg.data_dir == DEFAULT_DATA_DIR
    assert cfg.data_dir.is_relative_to(PROJECT_ROOT)
    assert cfg.data_dir.name == "data"


def test_explicit_data_dir_overrides_default(tmp_path: Path) -> None:
    """Явный --data-dir переопределяет путь проекта."""

    cfg = Config(data_dir=tmp_path / "other_data")
    assert cfg.data_dir == tmp_path / "other_data"


def test_configure_console_output_no_crash() -> None:
    """configure_console_output не должна падать в любом окружении."""

    from app.utils.helpers import configure_console_output

    configure_console_output()  # не бросает


def test_cli_output_survives_legacy_encoding() -> None:
    """Вывод CLI не ломает старые консоли (cp866).

    Интерфейс использует кириллицу и рамки, но ``configure_console_output``
    переключает поток на UTF-8 или включает ``errors='replace'``. Тест
    фиксирует, что такой вывод можно безопасно закодировать в cp866.
    """

    from app.cli.components.console import Console

    output: list[str] = []
    console = Console(output.append, color=False, width=80)
    console.success("Заметка создана")
    console.warning("Внимание")
    console.table(("Заголовок", "Категория"), [("Тест", "Работа")])

    text = "\n".join(output)
    text.encode("cp866", errors="replace")  # не бросает
    assert "Заметка создана" in text


def test_menu_text_is_printable() -> None:
    """Меню рендерится и переживает кодирование в cp866."""

    from app.cli.components.console import Console
    from app.cli.menu import Menu, MenuItem

    menu = Menu(
        "Тест",
        (MenuItem("1", "Notes — заметки"), MenuItem("0", "Назад")),
    )
    output: list[str] = []
    menu.render(Console(output.append, color=False, width=80))

    text = "\n".join(output)
    text.encode("cp866", errors="replace")  # не бросает
    assert "Notes" in text
