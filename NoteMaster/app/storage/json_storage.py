"""Низкоуровневое JSON-хранилище с атомарной записью.

Слой отвечает только за чтение/запись JSON-документа. Он не знает о моделях
``Note``/``Attachment`` — это ответственность репозитория.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from app.core.exceptions import SerializationError, StorageError

JSON_SCHEMA_VERSION = 1


class JsonStorage:
    """Чтение и атомарная запись JSON-документа.

    Гарантии:
    * каталоги и файл создаются автоматически;
    * запись выполняется через временный файл в том же каталоге и
      ``os.replace`` (атомарная подмена);
    * повреждённый файл никогда не перезаписывается пустыми данными — вместо
      этого поднимается :class:`SerializationError`.
    """

    def __init__(self, path: Path, encoding: str = "utf-8") -> None:
        self._path = Path(path)
        self._encoding = encoding
        self._lock = threading.RLock()

    # ------------------------------------------------------------------ пути
    @property
    def path(self) -> Path:
        return self._path

    @property
    def encoding(self) -> str:
        return self._encoding

    def exists(self) -> bool:
        return self._path.is_file()

    # -------------------------------------------------------------- создание
    @staticmethod
    def empty_payload() -> dict[str, Any]:
        """Возвращает корректную пустую структуру хранилища."""

        return {"version": JSON_SCHEMA_VERSION, "notes": []}

    def ensure_initialized(self) -> None:
        """Создаёт каталог и JSON-файл, если они отсутствуют."""

        with self._lock:
            if self._path.exists():
                if not self._path.is_file():
                    raise StorageError(f"Storage path is not a file: {self._path}")
                return
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._atomic_write(self.empty_payload())

    # ---------------------------------------------------------------- чтение
    def read(self) -> dict[str, Any]:
        """Читает и валидирует структуру JSON-документа."""

        with self._lock:
            if not self._path.exists():
                self.ensure_initialized()

            try:
                raw = self._path.read_text(encoding=self._encoding)
            except OSError as exc:
                raise StorageError(f"Cannot read storage file {self._path}: {exc}") from exc

            if not raw.strip():
                raise SerializationError(
                    f"Storage file {self._path} is empty or corrupted; "
                    "refusing to overwrite it"
                )

            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise SerializationError(
                    f"Storage file {self._path} contains invalid JSON: {exc}"
                ) from exc

            self._validate_payload(payload)
            return payload

    # ---------------------------------------------------------------- запись
    def write(self, payload: dict[str, Any]) -> None:
        """Атомарно записывает документ в файл."""

        self._validate_payload(payload)
        with self._lock:
            self._atomic_write(payload)

    # --------------------------------------------------------------- helpers
    def _validate_payload(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            raise SerializationError("Storage payload must be a JSON object")
        if "notes" not in payload:
            raise SerializationError("Storage payload must contain a 'notes' key")
        if not isinstance(payload["notes"], list):
            raise SerializationError("Storage payload 'notes' must be a list")
        for index, item in enumerate(payload["notes"]):
            if not isinstance(item, dict):
                raise SerializationError(
                    f"Storage payload note at index {index} must be an object"
                )

    def _atomic_write(self, payload: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

        file_descriptor, temp_name = tempfile.mkstemp(
            dir=self._path.parent,
            prefix=f"{self._path.name}.",
            suffix=".tmp",
        )
        temp_path = Path(temp_name)

        try:
            with os.fdopen(file_descriptor, "w", encoding=self._encoding, newline="\n") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self._path)
        except (TypeError, ValueError) as exc:
            raise SerializationError(f"Cannot serialize storage payload: {exc}") from exc
        except OSError as exc:
            raise StorageError(f"Cannot write storage file {self._path}: {exc}") from exc
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    # Временный файл не должен маскировать исходную ошибку.
                    pass


__all__ = ["JsonStorage", "JSON_SCHEMA_VERSION"]
