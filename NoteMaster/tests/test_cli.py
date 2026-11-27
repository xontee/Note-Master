"""Тесты CLI: Dashboard, навигация и управление заметками."""

from __future__ import annotations


# ---------------------------------------------------------------- Dashboard
def test_dashboard_shows_stats(run_cli, note_service) -> None:
    note_service.create_note("Заметка", is_pinned=True)

    text = run_cli(["0", "y"])

    assert "NOTE MASTER" in text
    assert "Заметок: 1" in text
    assert "Закреплённых: 1" in text
    assert "Operational" in text
    assert "ГЛАВНОЕ МЕНЮ" in text
    assert "До встречи" in text


def test_dashboard_empty_offers_create(run_cli) -> None:
    text = run_cli(["0", "y"])
    assert "Заметок пока нет" in text


def test_dashboard_invalid_command_then_exit(run_cli) -> None:
    text = run_cli(["abc", "0", "y"])
    assert "Неизвестная команда" in text
    assert "До встречи" in text


def test_empty_input_keeps_app_running(run_cli) -> None:
    text = run_cli(["", "0", "y"])
    assert "Введите номер команды" in text
    assert "До встречи" in text


def test_exit_requires_confirmation(run_cli) -> None:
    text = run_cli(["0", "n"])
    # Отказ от выхода возвращает на Dashboard, а не завершает приложение.
    assert text.count("ГЛАВНОЕ МЕНЮ") >= 2


def test_navigation_back_returns_to_dashboard(run_cli) -> None:
    text = run_cli(["1", "0", "0", "y"])
    assert text.count("ГЛАВНОЕ МЕНЮ") >= 2


def test_home_command_returns_to_dashboard(run_cli) -> None:
    text = run_cli(["1", "m", "0", "y"])
    assert text.count("ГЛАВНОЕ МЕНЮ") >= 2


# -------------------------------------------------------------------- Notes
def test_create_note(run_cli, note_service) -> None:
    text = run_cli(
        ["1", "1", "Моя заметка", "Текст заметки", "", "python, cli", "Работа", "y"]
    )

    assert "Заметка создана" in text
    notes = note_service.get_all_notes()
    assert len(notes) == 1
    assert notes[0].title == "Моя заметка"
    assert notes[0].content == "Текст заметки"
    assert notes[0].tags == ["python", "cli"]
    assert notes[0].category == "Работа"
    assert notes[0].is_pinned is True


def test_create_note_requires_title(run_cli, note_service) -> None:
    text = run_cli(["1", "1", "", "Заголовок", "", "", "", ""])

    assert "Значение не может быть пустым" in text
    assert note_service.get_all_notes()[0].title == "Заголовок"


def test_list_notes(run_cli, note_service) -> None:
    note_service.create_note("Первая")
    note_service.create_note("Вторая")

    text = run_cli(["1", "2"])

    assert "Первая" in text
    assert "Вторая" in text
    assert "Всего: 2" in text


def test_list_notes_empty(run_cli) -> None:
    text = run_cli(["1", "2"])
    assert "Заметок не найдено" in text


def test_open_note_details(run_cli, note_service) -> None:
    note = note_service.create_note("Детали", content="Полное содержимое")

    text = run_cli(["1", "3", "1"])

    assert "Детали" in text
    assert str(note.id) in text
    assert "Полное содержимое" in text
    assert "ДЕЙСТВИЯ" in text


def test_open_note_by_id_prefix(run_cli, note_service) -> None:
    note = note_service.create_note("По префиксу")

    text = run_cli(["1", "3", str(note.id)[:8]])
    assert "По префиксу" in text


def test_open_note_invalid_row(run_cli, note_service) -> None:
    note_service.create_note("Единственная")

    text = run_cli(["1", "3", "5"])
    assert "Нет заметки с номером 5" in text


def test_open_note_not_found(run_cli, note_service) -> None:
    note_service.create_note("Существующая")

    text = run_cli(["1", "3", "deadbeef-dead"])
    assert "Заметка не найдена" in text


def test_select_note_cancel(run_cli, note_service) -> None:
    note_service.create_note("Не трогать")

    text = run_cli(["1", "3", "0"])
    assert "Отменено" in text


def test_edit_note(run_cli, note_service) -> None:
    note = note_service.create_note("Старый заголовок")

    text = run_cli(
        ["1", "4", "1", "Новый заголовок", "n", "", "", ""]
    )

    assert "Заметка обновлена" in text
    assert note_service.get_note(note.id).title == "Новый заголовок"


def test_edit_note_content(run_cli, note_service) -> None:
    note = note_service.create_note("Заметка", content="старое")

    text = run_cli(
        ["1", "4", "1", "", "y", "новое содержимое", "", "", "", ""]
    )

    assert "Заметка обновлена" in text
    assert note_service.get_note(note.id).content == "новое содержимое"


def test_edit_note_without_changes(run_cli, note_service) -> None:
    note = note_service.create_note("Без изменений")

    text = run_cli(["1", "4", "1", "", "n", "", "", ""])

    assert "Изменений нет" in text
    assert note_service.get_note(note.id).title == "Без изменений"


def test_delete_note(run_cli, note_service) -> None:
    note_service.create_note("Удаляемая")

    text = run_cli(["1", "5", "1", "y"])

    assert "Заметка удалена" in text
    assert note_service.get_all_notes() == []


def test_delete_note_cancelled(run_cli, note_service) -> None:
    note_service.create_note("Остаётся")

    text = run_cli(["1", "5", "1", "n"])

    assert "Удаление отменено" in text
    assert len(note_service.get_all_notes()) == 1


def test_toggle_pin(run_cli, note_service) -> None:
    note = note_service.create_note("Закрепляемая")

    text = run_cli(["1", "6", "1"])

    assert "закреплена" in text
    assert note_service.get_note(note.id).is_pinned is True


def test_pinned_view_and_unpin(run_cli, note_service) -> None:
    note = note_service.create_note("Закреплённая", is_pinned=True)

    text = run_cli(["3", "2", "1"])

    assert "Закреплённая" in text
    assert "откреплена" in text
    assert note_service.get_note(note.id).is_pinned is False


def test_pinned_view_empty(run_cli) -> None:
    text = run_cli(["3"])
    assert "Закреплённых заметок нет" in text
