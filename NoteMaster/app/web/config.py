"""Конфигурация Web-слоя NoteMaster.

Отделяет HTTP-настройки (хост, порт, CORS, лимиты загрузки) от доменной
:class:`app.core.config.Config`. Core ничего не знает об этих параметрах —
они нужны только слою FastAPI.

Все значения читаются из переменных окружения (префикс ``NOTEMASTER_WEB_``),
чтобы в продакшене не хранить секреты и пути в исходном коде. Для локального
использования предусмотрены безопасные значения по умолчанию.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import DEFAULT_MAX_ATTACHMENT_SIZE, Config

# Переменные окружения Web-слоя.
_ENV_PREFIX = "NOTEMASTER_WEB_"


def _env(name: str, default: str) -> str:
    return os.environ.get(_ENV_PREFIX + name, default)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(_ENV_PREFIX + name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{_ENV_PREFIX + name} must be an integer, got {raw!r}") from exc


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(_ENV_PREFIX + name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_origins(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.environ.get(_ENV_PREFIX + name)
    if raw is None or not raw.strip():
        return default
    return tuple(origin.strip() for origin in raw.split(",") if origin.strip())


@dataclass(frozen=True, slots=True)
class WebConfig:
    """Настройки HTTP-сервера и политики Web-слоя."""

    host: str = "127.0.0.1"
    port: int = 8000
    # Web v1.0 — локальный однопользовательский интерфейс. CORS ограничен
    # адресами Vite-дева; прод-домен добавляется через переменную окружения.
    cors_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )
    # Жёсткий потолок тела запроса на приёме (чуть выше доменного лимита,
    # чтобы Core-валидатор давал понятную ошибку раньше, чем оборвётся HTTP).
    max_upload_size: int = DEFAULT_MAX_ATTACHMENT_SIZE
    api_prefix: str = "/api/v1"
    debug: bool = False
    # Пути/доменные лимиты берутся из единого Core-конфига.
    core: Config = field(default_factory=Config.default)

    @classmethod
    def from_env(cls, core: Config | None = None) -> "WebConfig":
        """Собирает конфигурацию из переменных окружения."""

        data_dir = _env("DATA_DIR", "")
        if data_dir:
            core = Config(data_dir=Path(data_dir), debug=_env_bool("DEBUG", False))
        elif core is None:
            core = Config(debug=_env_bool("DEBUG", False))

        return cls(
            host=_env("HOST", "127.0.0.1"),
            port=_env_int("PORT", 8000),
            cors_origins=_env_origins(
                "CORS_ORIGINS",
                ("http://localhost:5173", "http://127.0.0.1:5173"),
            ),
            max_upload_size=_env_int("MAX_UPLOAD_SIZE", DEFAULT_MAX_ATTACHMENT_SIZE),
            debug=bool(core.debug),
            core=core,
        )


__all__ = ["WebConfig"]
