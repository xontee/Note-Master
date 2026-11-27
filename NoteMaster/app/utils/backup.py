"""Резервное копирование и восстановление данных NoteMaster."""

from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from app.core.exceptions import StorageError
from app.utils.helpers import utc_now


def _default_backup_name() -> str:
    return f"notemaster-backup-{utc_now().strftime('%Y%m%d-%H%M%S')}.zip"


def create_backup(data_dir: Path, destination: Path | None = None) -> Path:
    """Создаёт zip-архив ``notes.json`` и каталога вложений.

    Архив пишется атомарно: сначала во временный ``.part``, затем
    переименовывается.
    """

    source_dir = Path(data_dir)
    if not source_dir.is_dir():
        raise StorageError(f"Data directory does not exist: {source_dir}")

    if destination is None:
        destination_path = source_dir / "backups" / _default_backup_name()
    else:
        destination_path = Path(destination)
        if destination_path.is_dir():
            destination_path = destination_path / _default_backup_name()
        elif destination_path.suffix.lower() != ".zip":
            destination_path = destination_path.with_name(
                destination_path.name + ".zip"
            )

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    destination_resolved = destination_path.resolve()
    temp_path = destination_path.with_name(destination_path.name + ".part")

    try:
        with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(source_dir.rglob("*")):
                if not path.is_file():
                    continue
                if path.name.endswith(".part"):
                    continue
                if path.resolve() == destination_resolved:
                    continue
                archive.write(path, path.relative_to(source_dir).as_posix())
        os.replace(temp_path, destination_path)
    except OSError as exc:
        _safe_unlink(temp_path)
        raise StorageError(f"Cannot create backup: {exc}") from exc
    except zipfile.BadZipFile as exc:  # pragma: no cover - защитная ветка
        _safe_unlink(temp_path)
        raise StorageError(f"Cannot create backup: {exc}") from exc

    return destination_path


def restore_backup(
    backup_path: Path,
    data_dir: Path,
    *,
    overwrite: bool = False,
) -> None:
    """Восстанавливает данные из архива.

    По умолчанию отказывается работать с непустым каталогом данных, чтобы не
    затереть текущее состояние незаметно.
    """

    archive_path = Path(backup_path)
    if not archive_path.is_file():
        raise StorageError(f"Backup file does not exist: {archive_path}")

    target_dir = Path(data_dir)
    if target_dir.exists() and any(target_dir.iterdir()) and not overwrite:
        raise StorageError(
            f"Data directory is not empty: {target_dir}. "
            "Pass overwrite=True to restore anyway"
        )

    temp_dir = Path(tempfile.mkdtemp(prefix="notemaster-restore-"))
    try:
        try:
            with zipfile.ZipFile(archive_path) as archive:
                for member in archive.infolist():
                    member_target = (temp_dir / member.filename).resolve()
                    if not member_target.is_relative_to(temp_dir.resolve()):
                        raise StorageError(
                            f"Unsafe path in backup archive: {member.filename}"
                        )
                archive.extractall(temp_dir)
        except zipfile.BadZipFile as exc:
            raise StorageError(f"Backup archive is corrupted: {exc}") from exc

        target_dir.mkdir(parents=True, exist_ok=True)
        for item in temp_dir.iterdir():
            destination = target_dir / item.name
            if destination.exists():
                if destination.is_dir():
                    shutil.rmtree(destination)
                else:
                    destination.unlink()
            if item.is_dir():
                shutil.copytree(item, destination)
            else:
                shutil.copy2(item, destination)
    except OSError as exc:
        raise StorageError(f"Cannot restore backup: {exc}") from exc
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _safe_unlink(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


__all__ = ["create_backup", "restore_backup"]
