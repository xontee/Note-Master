"""Централизованное преобразование ошибок Core в HTTP-ответы.

Единая точка, где доменное исключение превращается в паре
``(HTTP status, ErrorResponse)``. Эндпоинты не пишут ``try/except`` — они
просто вызывают сервисы, а FastAPI маршрутизирует исключение сюда.

Направление зависимости: Web знает о Core-исключениях, Core не знает о Web.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import (
    AttachmentLimitExceededError,
    AttachmentNotFoundError,
    AttachmentSizeLimitError,
    AttachmentStorageError,
    AttachmentValidationError,
    DuplicateNoteError,
    NoteMasterError,
    NoteNotFoundError,
    SerializationError,
    StorageError,
    ValidationError,
)
from app.web.schemas.common import error_body

logger = logging.getLogger("notemaster.web")

# Порядок важен: дочерние классы раньше родительских (dict проверяется по
# точному типу, а не по isinstance, поэтому маппинг разрешает иерархию ниже).
_STATUS_BY_ERROR: dict[type[BaseException], tuple[int, str]] = {
    ValidationError: (status.HTTP_400_BAD_REQUEST, "VALIDATION_ERROR"),
    NoteNotFoundError: (status.HTTP_404_NOT_FOUND, "NOTE_NOT_FOUND"),
    DuplicateNoteError: (status.HTTP_409_CONFLICT, "DUPLICATE_NOTE"),
    AttachmentNotFoundError: (status.HTTP_404_NOT_FOUND, "ATTACHMENT_NOT_FOUND"),
    AttachmentSizeLimitError: (413, "ATTACHMENT_TOO_LARGE"),
    AttachmentLimitExceededError: (
        status.HTTP_409_CONFLICT,
        "ATTACHMENT_LIMIT_EXCEEDED",
    ),
    AttachmentValidationError: (status.HTTP_400_BAD_REQUEST, "ATTACHMENT_INVALID"),
    AttachmentStorageError: (
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "ATTACHMENT_STORAGE_ERROR",
    ),
    SerializationError: (status.HTTP_500_INTERNAL_SERVER_ERROR, "STORAGE_CORRUPTED"),
    StorageError: (status.HTTP_500_INTERNAL_SERVER_ERROR, "STORAGE_ERROR"),
}

# Нейтральные сообщения: доменные тексты (в т.ч. русские) не протекают наружу.
_SAFE_MESSAGE: dict[str, str] = {
    "VALIDATION_ERROR": "Request data failed validation.",
    "NOTE_NOT_FOUND": "Note was not found.",
    "DUPLICATE_NOTE": "Note already exists.",
    "ATTACHMENT_NOT_FOUND": "Attachment was not found.",
    "ATTACHMENT_TOO_LARGE": "Attachment exceeds the size limit.",
    "ATTACHMENT_LIMIT_EXCEEDED": "Attachment count limit exceeded.",
    "ATTACHMENT_INVALID": "Attachment failed validation.",
    "ATTACHMENT_STORAGE_ERROR": "Attachment file is unavailable.",
    "STORAGE_CORRUPTED": "Storage data is corrupted.",
    "STORAGE_ERROR": "Storage operation failed.",
}


def _resolve(exc: BaseException) -> tuple[int, str]:
    """Находит (status, code) по типу исключения с учётом иерархии.

    Ищем наиболее специфичный предок в словаре — так
    ``AttachmentSizeLimitError`` (дочерний ``ValidationError``? нет — дочерний
    ``AttachmentValidationError``) получает свой код, а не общий.
    """

    for error_type, mapping in _STATUS_BY_ERROR.items():
        if isinstance(exc, error_type):
            return mapping
    # Неизвестная доменная ошибка — безопасный 500.
    return status.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_ERROR"


def register_exception_handlers(app: FastAPI) -> None:
    """Регистрирует все обработчики ошибок на приложении FastAPI."""

    @app.exception_handler(NoteMasterError)
    async def handle_core_error(_: Request, exc: NoteMasterError) -> JSONResponse:
        code_status, code = _resolve(exc)
        message = _SAFE_MESSAGE.get(code, "Request could not be processed.")
        # Подробности (внутренний текст, стек) — только в лог, не в ответ.
        logger.warning(
            "Core error %s -> HTTP %s: %s", type(exc).__name__, code_status, exc
        )
        return JSONResponse(status_code=code_status, content=error_body(code, message))

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # 422 — ошибка схемы запроса Pydantic. Возвращаем безопасный список
        # полей без значений, чтобы не эхо-лить потенциально чувствительный ввод.
        fields = [
            ".".join(str(part) for part in error.get("loc", ())[1:]) or "body"
            for error in exc.errors()
        ]
        logger.debug("Request validation failed: %s", exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_body(
                "REQUEST_VALIDATION_ERROR",
                "Request payload failed schema validation.",
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        _: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        # Единый формат и для штатных HTTP-исключений (404 маршрута, 405 и т.п.).
        code = {
            status.HTTP_404_NOT_FOUND: "NOT_FOUND",
            status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
        }.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(code, str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        # Финальный предохранитель: traceback — только в лог (в debug — полный).
        logger.exception("Unhandled server error")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_body("INTERNAL_ERROR", "Internal server error."),
        )


__all__ = ["register_exception_handlers"]
