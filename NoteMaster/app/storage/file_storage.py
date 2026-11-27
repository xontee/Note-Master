"""Файловое хранилище вложений.

Физические файлы хранятся отдельно от JSON-метаданных. Интерфейс
:class:`AttachmentStorage` позволяет заменить локальное хранилище на облачное
без изменения :class:`AttachmentService`.
"""

from __future__ import annotations

import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from uuid import UUID

from app.core.exceptions import AttachmentStorageError
from app.utils.helpers import utc_now


class AttachmentStorage(ABC):
    """Абстракция хранилища физических файлов вложений."""

    @abstractmethod
    def save(
        self,
        source: Path,
        note_id: UUID,
        attachment_id: UUID,
        extension: str,
    ) -> str:
        """Копирует файл в хранилище и возвращает относительный путь."""

    @abstractmethod
    def delete(self, relative_path: str) -> bool:
        """Удаляет файл. Возвращает ``True``, если файл был удалён."""

    @abstractmethod
    def exists(self, relative_path: str) -> bool:
        """Проверяет наличие физического файла."""

    @abstractmethod
    def resolve(self, relative_path: str) -> Path:
        """Преобразует относительный путь в абсолютный внутри хранилища."""

    @abstractmethod
    def export(
        self, relative_path: str, destination: Path, overwrite: bool = False
    ) -> Path:
        """Копирует файл в указанное место назначения."""

    @abstractmethod
    def get_size(self, relative_path: str) -> int:
        """Возвращает размер файла в байтах."""

    @abstractmethod
    def list_relative_paths(self) -> list[str]:
        """Перечисляет все файлы хранилища относительными путями."""


class LocalAttachmentStorage(AttachmentStorage):
    """Локальное хранилище с иерархией ``YYYY/MM/NOTE_UUID/ATTACHMENT_UUID.ext``."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    # ---------------------------------------------------------------- запись
    def save(
        self,
        source: Path,
        note_id: UUID,
        attachment_id: UUID,
        extension: str,
    ) -> str:
        source_path = Path(source)
        if not source_path.is_file():
            raise AttachmentStorageError(f"Source file does not exist: {source_path}")

        relative_path = self._build_relative_path(note_id, attachment_id, extension)
        target = self.resolve(relative_path)

        if target.exists():
            raise AttachmentStorageError(
                f"Attachment file already exists: {relative_path}"
            )

        temp_path = target.with_name(target.name + ".part")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, temp_path)
            os.replace(temp_path, target)
        except OSError as exc:
            self._safe_unlink(temp_path)
            raise AttachmentStorageError(
                f"Cannot copy attachment to storage: {exc}"
            ) from exc

        return relative_path

    def _build_relative_path(
        self,
        note_id: UUID,
        attachment_id: UUID,
        extension: str,
    ) -> str:
        if not isinstance(note_id, UUID):
            raise AttachmentStorageError("note_id must be a UUID")
        if not isinstance(attachment_id, UUID):
            raise AttachmentStorageError("attachment_id must be a UUID")

        suffix = (extension or "").strip().lower()
        if suffix and not suffix.startswith("."):
            suffix = "." + suffix

        now = utc_now()
        relative = (
            Path(f"{now.year:04d}")
            / f"{now.month:02d}"
            / str(note_id)
            / f"{attachment_id}{suffix}"
        )
        return relative.as_posix()

    # ---------------------------------------------------------------- чтение
    def exists(self, relative_path: str) -> bool:
        try:
            return self.resolve(relative_path).is_file()
        except AttachmentStorageError:
            return False

    def resolve(self, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise AttachmentStorageError("relative_path must be a non-empty string")

        candidate = Path(relative_path)
        if candidate.is_absolute():
            raise AttachmentStorageError(
                f"Absolute paths are not allowed: {relative_path}"
            )
        if any(part == ".." for part in candidate.parts):
            raise AttachmentStorageError(
                f"Path traversal is not allowed: {relative_path}"
            )

        base = self._base_dir.resolve()
        target = (self._base_dir / candidate).resolve()
        if not target.is_relative_to(base):
            raise AttachmentStorageError(
                f"Path escapes attachment storage: {relative_path}"
            )
        return target

    def get_size(self, relative_path: str) -> int:
        target = self.resolve(relative_path)
        if not target.is_file():
            raise AttachmentStorageError(f"Attachment file not found: {relative_path}")
        try:
            return target.stat().st_size
        except OSError as exc:
            raise AttachmentStorageError(f"Cannot read attachment size: {exc}") from exc

    # -------------------------------------------------------------- удаление
    def delete(self, relative_path: str) -> bool:
        target = self.resolve(relative_path)
        if not target.exists():
            return False
        if not target.is_file():
            raise AttachmentStorageError(
                f"Attachment path is not a file: {relative_path}"
            )
        try:
            target.unlink()
        except OSError as exc:
            raise AttachmentStorageError(
                f"Cannot delete attachment file: {exc}"
            ) from exc

        self._cleanup_empty_dirs(target.parent)
        return True

    # ---------------------------------------------------------------- экспорт
    def export(
        self,
        relative_path: str,
        destination: Path,
        overwrite: bool = False,
    ) -> Path:
        source = self.resolve(relative_path)
        if not source.is_file():
            raise AttachmentStorageError(f"Attachment file not found: {relative_path}")

        destination_path = Path(destination)
        if destination_path.exists() and not overwrite:
            raise AttachmentStorageError(
                f"Destination already exists: {destination_path}"
            )

        try:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination_path)
        except OSError as exc:
            raise AttachmentStorageError(f"Cannot export attachment: {exc}") from exc
        return destination_path

    # -------------------------------------------------------------- служебное
    def list_relative_paths(self) -> list[str]:
        base = self._base_dir.resolve()
        if not base.exists():
            return []

        result: list[str] = []
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.name.endswith(".part"):
                continue
            try:
                result.append(path.relative_to(base).as_posix())
            except ValueError:  # pragma: no cover - защита от симлинков
                continue
        return sorted(result)

    def _cleanup_empty_dirs(self, start: Path) -> None:
        base = self._base_dir.resolve()
        current = start.resolve()
        while current != base and base in current.parents:
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent

    @staticmethod
    def _safe_unlink(path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass


__all__ = ["AttachmentStorage", "LocalAttachmentStorage"]
