"""
logger.py
=========
Configuración centralizada de logging para todo el backend de BravoBot.

Proporciona:
  - Configuración unificada de formato y nivel (vía LOG_LEVEL)
  - Soporte para logging estructurado en JSON (vía LOG_FORMAT=json)
  - Contexto de correlación (request_id) automático vía contextvars
  - Context manager y decorador para medir tiempo de ejecución
  - Supresión de librerías ruidosas en producción

Uso:
    from logger import get_logger, time_logged

    logger = get_logger("bravobot.modulo")

    with time_logged("consulta_chromadb"):
        resultados = chroma.query(...)

    @time_logged("pipeline_completo")
    def ask(...):
        ...
"""

import json
import logging
import logging.config
import os
import time
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable

# ── Contexto de correlación ───────────────────────────────────────────────────
# Se propaga automáticamente a través de contextvars (sin acoplar a FastAPI/Telegram)
_request_id: ContextVar[str] = ContextVar("request_id", default="-")
_session_id: ContextVar[str] = ContextVar("session_id", default="-")


def set_request_id(request_id: str) -> None:
    """Establece el request_id para el contexto actual (p.ej. desde middleware)."""
    _request_id.set(request_id)


def get_request_id() -> str:
    return _request_id.get()


def set_session_id(session_id: str | None) -> None:
    """Establece el session_id para el contexto actual."""
    _session_id.set(session_id or "-")


def get_session_id() -> str:
    return _session_id.get()


# ── Formateador con contexto de correlación ───────────────────────────────────


class CorrelationFormatter(logging.Formatter):
    """Formateador que inyecta request_id y session_id del contextvars."""

    def format(self, record: logging.LogRecord) -> str:
        record.request_id = get_request_id()
        record.session_id = get_session_id()
        return super().format(record)


# ── Formateador JSON ──────────────────────────────────────────────────────────


class JSONFormatter(logging.Formatter):
    """Formateador que produce salida JSON estructurada (ideal para producción/centralizado)."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
            "session_id": get_session_id(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_entry.update(record.extra)
        return json.dumps(log_entry, ensure_ascii=False)


# ── Configuración ─────────────────────────────────────────────────────────────

_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_LOG_FORMAT = os.getenv("LOG_FORMAT", "text").lower()  # "text" | "json"

_TEXT_FORMAT = "%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s"
_TEXT_DATE_FORMAT = "%H:%M:%S"

_JSON_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

_NOISY_LOGGERS = {
    "uvicorn.access": logging.WARNING,
    "httpx": logging.WARNING,
    "httpcore": logging.WARNING,
    "chromadb": logging.WARNING,
    "sentence_transformers": logging.WARNING,
    "urllib3": logging.WARNING,
    "PIL": logging.WARNING,
    "pdfminer": logging.WARNING,
}


def setup_logging() -> None:
    """Configura el logging de forma centralizada. Llamar una vez al iniciar la app."""
    level = getattr(logging, _LOG_LEVEL, logging.INFO)

    if _LOG_FORMAT == "json":
        formatter = JSONFormatter(datefmt=_JSON_DATE_FORMAT)
    else:
        formatter = CorrelationFormatter(
            fmt=_TEXT_FORMAT,
            datefmt=_TEXT_DATE_FORMAT,
        )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    # Raíz: limpia configuraciones previas (p.ej. basicConfig en telegram_bot.py)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    # Reemplazar handlers en vez de añadir duplicados
    root_logger.handlers = [handler]

    # Silenciar librerías ruidosas
    for logger_name, logger_level in _NOISY_LOGGERS.items():
        logging.getLogger(logger_name).setLevel(logger_level)


def get_logger(name: str) -> logging.Logger:
    """Obtiene un logger con el nombre dado, ya configurado."""
    logger = logging.getLogger(name)
    # Si el logger raíz no tiene handlers (setup no se ha llamado), configurar por defecto
    if not logging.getLogger().handlers:
        setup_logging()
    return logger


# ── Decorador y context manager para timed logging ────────────────────────────


@contextmanager
def time_logged(
    operation: str,
    logger: logging.Logger | None = None,
    level: int = logging.DEBUG,
    **extra: Any,
):
    """
    Context manager que mide y loguea el tiempo de ejecución de un bloque.

    Args:
        operation: Nombre descriptivo de la operación (p.ej. "chromadb.query").
        logger: Logger a usar. Si es None, se usa un logger default.
        level: Nivel de logging (DEBUG por defecto).
        **extra: Campos adicionales para incluir en el log.

    Uso:
        with time_logged("chromadb.query", logger, coleccion="bravobot"):
            results = collection.query(...)
    """
    _logger = logger or get_logger("bravobot.performance")
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        _logger.log(
            level,
            "[PERF] %s ─ %.3fs %s",
            operation,
            elapsed,
            f"({extra})" if extra else "",
        )


def timed(
    operation: str | None = None,
    logger: logging.Logger | None = None,
    level: int = logging.DEBUG,
):
    """
    Decorador que mide y loguea el tiempo de ejecución de una función.

    Args:
        operation: Nombre de la operación (por defecto usa <módulo>.<función>).
        logger: Logger a usar.
        level: Nivel de logging.

    Uso:
        @timed("chromadb.query")
        def retrieve(...):
            ...
    """

    def decorator(func: Callable) -> Callable:
        op_name = operation or f"{func.__module__}.{func.__qualname__}"
        _logger = logger or get_logger("bravobot.performance")

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                _logger.log(level, "[PERF] %s ─ %.3fs", op_name, elapsed)

        return wrapper

    return decorator
