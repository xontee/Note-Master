"""Тесты CLI: поиск, категории/теги и настройки."""

from __future__ import annotations


# ------------------------------------------------------------------- Search
def test_search_by_text(run_cli, note_service) -> None:
    note_service.create_note("Python заметка", content="про asyncio")
    note_service.create_note("Другая", content="без совпадений")

    text = run_cli(["2", "1", "asyncio"])

    assert "Python заметка" in text
    assert "Другая" not in text


def test_search_no_results(run_cli, note_service) -> None:
    note_service.create_note("Заметка")

    text = run_cli(["2", "1", "нет-такого"])
    assert "Ничего не найдено" in text


def test_search_by_tag(run_cli, note_service) -> None:
    note_service.create_note("С тегом", tags=["python"])
    note_service.create_note("Без тега")

    text = run_cli(["2", "2", "python"])

    assert "С тегом" in text
    assert "Без тега" not in text


def test_search_by_category(run_cli, note_service) -> None:
    note_service.create_note("Рабочая", category="Работа")
    note_service.create_note("Личная", category="Дом")

    text = run_cli(["2", "3", "Работа"])

    assert "Рабочая" in text
    assert "Личная" not in text


def test_open_search_result(run_cli, note_service) -> None:
    note_service.create_note("Найденная", content="уникальное слово")

    text = run_cli(["2", "1", "уникальное", "4", "1"])

    assert "Найденная" in text
    assert "ДЕЙСТВИЯ" in text


def test_repeat_search(run_cli, note_service) -> None:
    note_service.create_note("Первая", content="alpha")
    note_service.create_note("Вторая", content="beta")

    text = run_cli(["2", "1", "alpha", "5", "beta"])

    assert "Вторая" in text


def test_open_result_without_search(run_cli) -> None:
    text = run_cli(["2", "4"])
    assert "Сначала выполните поиск" in text


# --------------------------------------------------------- Categories & Tags
def test_categories_and_tags_view(run_cli, note_service) -> None:
    note_service.create_note("Первая", tags=["python", "cli"], category="Работа")
    note_service.create_note("Вторая", tags=["python"], category="Работа")

    text = run_cli(["4"])

    assert "КАТЕГОРИИ" in text
    assert "Работа: 2" in text
    assert "python: 2" in text
    assert "cli: 1" in text


def test_filter_notes_by_category(run_cli, note_service) -> None:
    note_service.create_note("Рабочая", category="Работа")
    note_service.create_note("Домашняя", category="Дом")

    text = run_cli(["4", "1", "Работа"])

    assert "Рабочая" in text
    assert "Домашняя" not in text


def test_filter_notes_by_tag(run_cli, note_service) -> None:
    note_service.create_note("С тегом", tags=["python"])
    note_service.create_note("Без тега")

    text = run_cli(["4", "2", "python"])

    assert "С тегом" in text
    assert "Без тега" not in text


# ----------------------------------------------------------------- Settings
def test_settings_view(run_cli, note_service) -> None:
    note_service.create_note("Заметка")

    text = run_cli(["6"])

    assert "Python:" in text
    assert "Путь к хранилищу" in text
    assert "Заметок: 1" in text
    assert "Макс. размер вложения" in text


def test_settings_storage_check(run_cli) -> None:
    text = run_cli(["6", "1"])
    assert "ДОСТУПНОСТЬ ВЛОЖЕНИЙ" in text
