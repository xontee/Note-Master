# NoteMaster Core v1.0

Модульное ядро системы управления заметками и персональными знаниями с
поддержкой категорий, тегов, поиска и файловых вложений.

Проект построен так, чтобы поверх текущего ядра можно было без переписывания
бизнес-логики добавить GUI, REST API, SQLite/PostgreSQL, облачное хранение
вложений и интеллектуальные функции.

## Возможности

- CRUD заметок (создание, чтение, редактирование, удаление).
- Категории, теги, закрепление заметок.
- Поиск по заголовку, содержимому, тегам и категории (без учёта регистра).
- Фильтрация по тегу, категории и признаку закрепления.
- Сортировка по дате создания, дате изменения и заголовку.
- Файловые вложения: добавление, просмотр, экспорт, удаление.
- Отдельное физическое хранилище файлов и JSON-метаданных.
- Атомарная запись JSON с защитой от повреждения данных.
- Проверка целостности связей «заметка — метаданные — файл».
- Резервное копирование данных в zip-архив.
- Полноценный CLI v1.0: Dashboard, экраны заметок, поиска, категорий и тегов,
  вложений и настроек с единой навигацией.

## Архитектура

Слои приложения и направление зависимостей:

```
CLI / main (композиционный корень)
        │
        ▼
Services (NoteService, AttachmentService, IntegrityService)
        │            │
        ▼            ▼
Repositories   AttachmentStorage (абстракция)
        │            │
        ▼            ▼
JsonStorage   LocalAttachmentStorage
        │
        ▼
data/notes.json, data/attachments/
```

Ключевые принципы:

- **SRP** — каждый модуль отвечает за одну задачу.
- **Dependency Injection** — сервисы получают репозиторий, хранилище и
  конфигурацию через конструктор.
- **Separation of Concerns** — CLI не работает с файлами, бизнес-логика не
  знает о JSON.
- **SOLID / DRY / KISS** — общие операции вынесены в модели и утилиты.
- **Type Hints** — все публичные API типизированы.

`NoteService` зависит от абстракции `NoteRepository`, а
`AttachmentService` — от абстракции `AttachmentStorage`. Это позволяет
заменить JSON-репозиторий на SQLite или локальное хранилище файлов на
облачное без изменения сервисов.

## Структура проекта

```
NoteMaster/
├── app/
│   ├── core/
│   │   ├── config.py          # централизованная конфигурация
│   │   └── exceptions.py      # иерархия исключений
│   ├── models/
│   │   ├── note.py            # модель Note
│   │   └── attachment.py      # модель Attachment
│   ├── repositories/
│   │   ├── base.py            # NoteRepository (ABC)
│   │   └── json_repository.py # JSON-реализация
│   ├── storage/
│   │   ├── json_storage.py    # атомарное чтение/запись JSON
│   │   └── file_storage.py    # AttachmentStorage + локальная реализация
│   ├── services/
│   │   ├── note_service.py
│   │   ├── attachment_service.py
│   │   └── integrity_service.py
│   ├── attachments/
│   │   └── validators.py      # валидация и проверка сигнатур файлов
│   ├── utils/
│   │   ├── helpers.py
│   │   └── backup.py
│   ├── cli/
│   │   ├── interface.py       # цикл приложения и сборка контекста
│   │   ├── context.py         # зависимости экранов (AppContext)
│   │   ├── menu.py            # описание и отрисовка меню
│   │   ├── navigation.py      # Nav + стек экранов (Navigator)
│   │   ├── components/        # console, formatting, tables, prompts
│   │   ├── handlers/          # сценарии заметок и вложений
│   │   └── views/             # экраны: dashboard, notes, details, search,
│   │                          #         categories, attachments, settings
│   └── main.py                # сборка зависимостей и точка входа
├── data/
│   ├── notes.json             # создаётся автоматически
│   └── attachments/           # создаётся автоматически
├── docs/
│   └── architecture.md
├── tests/
├── .gitignore
├── pytest.ini
├── requirements.txt
├── run.py
└── README.md
```

## Установка

Требуется Python 3.11+. Runtime-зависимостей нет — используется только
стандартная библиотека.

Все команды ниже выполняются из каталога проекта `NoteMaster/`.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## Запуск

```bash
python run.py                 # интерактивный CLI
python run.py --data-dir mydata
python run.py --check         # проверка целостности и выход
python run.py --debug         # проброс непредвиденных ошибок
```

По умолчанию данные хранятся в `<папка проекта>/data` и **не зависят от
текущего каталога запуска**: `python NoteMaster/run.py` из любого места
работает с одним и тем же хранилищем. Каталог можно переопределить через
`--data-dir`.

При первом запуске автоматически создаются `data/notes.json` и
`data/attachments/`.

### Навигация CLI

Интерфейс построен как стек экранов: Dashboard — корень, остальные экраны
открываются поверх него.

| Команда | Действие |
|---|---|
| `1`…`6` | Выбор пункта текущего меню |
| `0` | Назад (на Dashboard — выход) |
| `M` | Вернуться на главный экран |
| `Q` | Выход с подтверждением |

Пустой ввод и неизвестные команды не завершают приложение: выводится
подсказка и меню показывается снова. Выход требует подтверждения, чтобы
защитить от случайного нажатия.

### Экраны

- **Dashboard** — количество заметок, закреплённых, вложений, статус
  хранилища, версия и главное меню.
- **Notes** — создание, таблица всех заметок, подробный просмотр, открытие
  по номеру/ID/префиксу, редактирование, удаление, закрепление.
- **Search** — поиск по тексту, тегу и категории через `NoteService`, с
  повторным поиском и открытием найденной заметки.
- **Pinned notes** — закреплённые заметки, открытие и снятие закрепления.
- **Categories & Tags** — используемые категории и теги с количеством
  заметок/использований, фильтрация по ним.
- **Attachments** — добавление, таблица вложений, информация, удаление,
  экспорт и проверка доступности файлов.
- **Settings** — версия, Python, пути хранилища, лимиты, разрешённые и
  запрещённые расширения, статистика и проверка хранилища.

### Пример сценария

```text
1  → Notes
1  → Создать заметку
Заголовок: Архитектура NoteMaster
Содержимое: описание слоёв            (пустая строка — завершить)
Теги: python, architecture
Категория: Работа
Закрепить заметку? (y/N): y
```

После создания CLI показывает ID заметки. Дальше можно открыть её по номеру
строки из таблицы, полному ID или однозначному префиксу.

### Цепочка вызова

```
Пользователь → View → Handler → NoteService/AttachmentService
             → Repository/AttachmentStorage → JsonStorage/FileStorage
```

CLI не читает `notes.json`, не создаёт объекты `Note` вручную и не управляет
каталогом вложений: это ответственность Core.

## Примеры использования (Python API)

```python
from app.core.config import Config
from app.main import build_application

app = build_application(Config(data_dir="data"))
notes = app.note_service
attachments = app.attachment_service

# Создание
note = notes.create_note(
    title="Архитектура NoteMaster",
    content="Описание слоёв и зависимостей.",
    tags=["python", "architecture"],
    category="Работа",
    is_pinned=True,
)

# Чтение
same = notes.get_note(note.id)
all_notes = notes.get_all_notes(sort_by="updated_at", descending=True)

# Редактирование
notes.update_note(note.id, content="Обновлённое содержимое")
notes.update_note(note.id, category=None)  # очистить категорию

# Поиск и фильтрация
found = notes.search_notes("архитектура")
filtered = notes.filter_notes(tag="python", pinned=True)

# Закрепление
notes.pin_note(note.id)
notes.unpin_note(note.id)

# Удаление (вложения удаляются вместе с заметкой)
result = notes.delete_note(note.id)
if result.failed_attachments:
    print("Не удалось удалить файлы:", result.failed_attachments)
```

### Работа с вложениями

```python
attachment = attachments.add_attachment(note.id, "docs/specification.pdf")

items = attachments.list_attachments(note.id)
one = attachments.get_attachment(note.id, attachment.id)

# Экспорт в файл
attachments.export_attachment(note.id, attachment.id, "exports/specification.pdf")

# Экспорт в существующий каталог (имя файла сохраняется)
attachments.export_attachment(note.id, attachment.id, "exports/")

# Удаление
attachments.remove_attachment(note.id, attachment.id)
```

## JSON-структура

`data/notes.json`:

```json
{
  "version": 1,
  "notes": [
    {
      "id": "0b6f0d4e-3f4c-4f0e-9d2a-1f2b3c4d5e6f",
      "title": "Заголовок заметки",
      "content": "Текст заметки",
      "tags": ["python", "notes"],
      "category": "Работа",
      "is_pinned": false,
      "created_at": "2026-11-26T10:00:00+00:00",
      "updated_at": "2026-11-26T10:05:00+00:00",
      "attachments": [
        {
          "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
          "filename": "specification.pdf",
          "stored_filename": "7c9e6679-7425-40de-944b-e07fc1f90ae7.pdf",
          "relative_path": "2026/11/0b6f0d4e-3f4c-4f0e-9d2a-1f2b3c4d5e6f/7c9e6679-7425-40de-944b-e07fc1f90ae7.pdf",
          "mime_type": "application/pdf",
          "extension": ".pdf",
          "size": 102400,
          "created_at": "2026-11-26T10:03:00+00:00"
        }
      ]
    }
  ]
}
```

Физические файлы лежат отдельно:

```
data/attachments/2026/11/<NOTE_UUID>/<ATTACHMENT_UUID>.pdf
```

В JSON хранятся только метаданные и относительные пути — содержимое файлов
никогда не сериализуется в JSON и не кодируется в Base64.

## Ограничения и безопасность

Значения по умолчанию (настраиваются через `Config`):

| Параметр | По умолчанию |
|---|---|
| Максимальный размер файла | 25 MiB |
| Максимум вложений на заметку | 20 |
| Пустые файлы | запрещены |
| Разрешённые расширения | не ограничены (кроме запрещённых) |
| Запрещённые расширения | исполняемые и скриптовые форматы |

Реализованные меры защиты:

- Проверка существования и читаемости исходного файла.
- Проверка размера и количества вложений.
- Чёрный список потенциально опасных расширений и опциональный белый список.
- Проверка сигнатур известных форматов (PDF, PNG, JPEG, GIF, ZIP-контейнеры и др.).
- Блокировка исполняемых сигнатур (`MZ`, `ELF`, Mach-O) независимо от расширения.
- Защита от path traversal при разрешении относительных путей.
- Уникальные имена файлов на основе UUID — коллизии и перезапись исключены.
- Атомарная запись JSON через временный файл и `os.replace`.
- Повреждённый JSON никогда не перезаписывается пустыми данными.
- Компенсация частичных операций: если метаданные не сохранились, скопированный файл удаляется.

Настройка лимитов:

```python
from app.core.config import Config

config = Config(
    data_dir="data",
    max_attachment_size=50 * 1024 * 1024,
    max_attachments_per_note=50,
    allowed_extensions=frozenset({".pdf", ".png", ".txt", ".md"}),
    allow_empty_files=False,
)
app = build_application(config)
```

## Тестирование

```bash
python -m pytest -q
```

Покрыты модели, JSON-хранилище, репозиторий, сервисы, валидация вложений,
файловое хранилище, проверка целостности и CLI. Тесты CLI подменяют ввод и
вывод и работают во временных каталогах, поэтому реальные данные не
затрагиваются.

## Проверка целостности и резервное копирование

```bash
python run.py --check
```

Отчёт содержит количество заметок и вложений, отсутствующие файлы, файлы
без метаданных, несовпадения размеров и дубликаты ID.

Резервная копия создаётся программно (в CLI резервное копирование не вынесено
в меню, чтобы не смешивать повседневные операции с обслуживанием):

```python
from app.utils.backup import create_backup, restore_backup

archive = create_backup("data", "backups/manual.zip")
restore_backup(archive, "data", overwrite=True)
```

## Расширение

- **SQLite/PostgreSQL** — реализуйте `NoteRepository` и передайте его в
  `NoteService`; остальной код не меняется.
- **Облачное хранилище вложений** — реализуйте `AttachmentStorage` и
  передайте его в `AttachmentService` и `NoteService`.
- **GUI / REST API** — используйте сервисы как готовый слой бизнес-логики.
- **Полнотекстовый/семантический поиск** — замените реализацию
  `NoteRepository.search` или добавьте отдельный индексный сервис.

Подробнее о слоях и сценариях сбоев — в `docs/architecture.md`.
