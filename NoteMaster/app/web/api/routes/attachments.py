"""Эндпоинты вложений: список, загрузка, скачивание, удаление.

Пути построены вокруг заметки (``/notes/{note_id}/attachments/...``), потому
что контракт Core ищет вложение внутри конкретной заметки. Это исключает
полное сканирование хранилища ради одного ``attachment_id``.

Файл никогда не отдаётся напрямую из хранилища: путь предоставляет
:class:`AttachmentService` через аддитивный метод ``resolve_for_download``.
Внутренние пути (``relative_path``/``stored_filename``) в ответы не попадают.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from app.core.exceptions import NoteNotFoundError
from app.models.attachment import Attachment
from app.services.attachment_service import AttachmentService
from app.services.note_service import NoteService
from app.web.config import WebConfig
from app.web.dependencies import (
    get_attachment_service,
    get_note_service,
    get_web_config,
)
from app.web.schemas.attachments import (
    AttachmentListResponse,
    AttachmentResponse,
)
from app.web.schemas.common import error_body

router = APIRouter(tags=["attachments"])


def _to_response(
    note_id: UUID, attachment: Attachment, api_prefix: str
) -> AttachmentResponse:
    """Core-вложение → безопасный DTO (без внутренних путей)."""

    return AttachmentResponse(
        id=attachment.id,
        note_id=note_id,
        filename=attachment.filename,
        extension=attachment.extension,
        mime_type=attachment.mime_type,
        size=attachment.size,
        created_at=attachment.created_at,
        download_url=f"{api_prefix}/notes/{note_id}/attachments/{attachment.id}/download",
    )


# ─────────────────────────────────────────────────────────────── Список ──────


@router.get(
    "/{note_id}/attachments",
    response_model=AttachmentListResponse,
    summary="Список вложений заметки",
)
def list_attachments(
    note_id: UUID,
    service: AttachmentService = Depends(get_attachment_service),
    web_config: WebConfig = Depends(get_web_config),
) -> AttachmentListResponse:
    items = service.list_attachments(note_id)
    return AttachmentListResponse(
        items=[_to_response(note_id, a, web_config.api_prefix) for a in items],
        total=len(items),
    )


# ─────────────────────────────────────────────────────────────── Загрузка ─────


@router.post(
    "/{note_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Загрузить вложение",
    description=(
        "Принимает файл через multipart. Поток ограничивается по размеру до "
        "записи на диск, затем файл проходит Core-валидацию (расширение, "
        "сигнатура, лимиты) и сохраняется в хранилище. Временный файл загрузки "
        "удаляется. Тело файла не попадает в JSON и не кодируется в Base64."
    ),
)
def upload_attachment(
    note_id: UUID,
    file: UploadFile = File(...),
    service: AttachmentService = Depends(get_attachment_service),
    note_service: NoteService = Depends(get_note_service),
    web_config: WebConfig = Depends(get_web_config),
) -> AttachmentResponse:
    # Заметка-владелец должна существовать.
    try:
        note_service.get_note(note_id)
    except NoteNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_body("NOTE_NOT_FOUND", "Note was not found."),
        )

    # Ограничение размера на приёме потока — до записи на диск.
    max_size = web_config.core.max_attachment_size
    tmp_path: str | None = None
    try:
        fd, tmp_path = tempfile.mkstemp(prefix="nm-upload-")
        total = 0
        with open(fd, "wb") as handle:
            while True:
                chunk = file.file.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=error_body(
                            "ATTACHMENT_TOO_LARGE",
                            "Attachment exceeds the size limit.",
                        ),
                    )
                handle.write(chunk)
        # Вся валидация (имя, расширение, сигнатура, лимиты) — в Core.
        attachment = service.add_attachment(note_id, tmp_path)
    finally:
        if tmp_path is not None:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass

    return _to_response(note_id, attachment, web_config.api_prefix)


# ─────────────────────────────────────────────────────────────── Метаданные ───


@router.get(
    "/{note_id}/attachments/{attachment_id}",
    response_model=AttachmentResponse,
    summary="Метаданные вложения",
)
def get_attachment(
    note_id: UUID,
    attachment_id: UUID,
    service: AttachmentService = Depends(get_attachment_service),
    web_config: WebConfig = Depends(get_web_config),
) -> AttachmentResponse:
    attachment = service.get_attachment(note_id, attachment_id)
    return _to_response(note_id, attachment, web_config.api_prefix)


# ─────────────────────────────────────────────────────────────── Скачивание ───


@router.get(
    "/{note_id}/attachments/{attachment_id}/download",
    summary="Скачать вложение",
    description="Отдаёт файл потоком. Путь определяет Core-сервис, Web не читает хранилище напрямую.",
)
def download_attachment(
    note_id: UUID,
    attachment_id: UUID,
    service: AttachmentService = Depends(get_attachment_service),
) -> FileResponse:
    file_path = service.resolve_for_download(note_id, attachment_id)
    attachment = service.get_attachment(note_id, attachment_id)
    return FileResponse(
        path=str(file_path),
        filename=attachment.filename,
        media_type=attachment.mime_type or "application/octet-stream",
    )


# ─────────────────────────────────────────────────────────────── Удаление ─────


@router.delete(
    "/{note_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить вложение",
)
def delete_attachment(
    note_id: UUID,
    attachment_id: UUID,
    service: AttachmentService = Depends(get_attachment_service),
) -> None:
    service.remove_attachment(note_id, attachment_id)


__all__ = ["router"]
