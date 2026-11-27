"""Иерархия исключений NoteMaster.

Все ошибки приложения наследуются от :class:`NoteMasterError`, что позволяет
верхним слоям (CLI, будущий REST API) единообразно обрабатывать сбои, не
скрывая при этом конкретную причину.
"""

from __future__ import annotations


class NoteMasterError(Exception):
    """Базовое исключение для всех ошибок NoteMaster."""


class ValidationError(NoteMasterError):
    """Нарушены правила валидации входных данных или модели."""


class NoteNotFoundError(NoteMasterError):
    """Заметка с указанным идентификатором не найдена."""


class DuplicateNoteError(NoteMasterError):
    """Попытка создать заметку с уже существующим идентификатором."""


class StorageError(NoteMasterError):
    """Ошибка чтения/записи хранилища."""


class SerializationError(StorageError):
    """Данные хранилища повреждены или не могут быть (де)сериализованы."""


class AttachmentError(NoteMasterError):
    """Базовое исключение для ошибок работы с вложениями."""


class AttachmentNotFoundError(AttachmentError):
    """Вложение не найдено у заметки."""


class AttachmentStorageError(AttachmentError):
    """Ошибка файлового хранилища вложений."""


class AttachmentValidationError(AttachmentError):
    """Вложение не прошло валидацию."""


class AttachmentSizeLimitError(AttachmentValidationError):
    """Размер вложения превышает допустимый лимит."""


class AttachmentLimitExceededError(AttachmentValidationError):
    """Превышено максимальное количество вложений у заметки."""


__all__ = [
    "NoteMasterError",
    "ValidationError",
    "NoteNotFoundError",
    "DuplicateNoteError",
    "StorageError",
    "SerializationError",
    "AttachmentError",
    "AttachmentNotFoundError",
    "AttachmentStorageError",
    "AttachmentValidationError",
    "AttachmentSizeLimitError",
    "AttachmentLimitExceededError",
]
