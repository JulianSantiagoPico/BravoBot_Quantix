"""
feedback/store.py — Capa de persistencia SQLite para el sistema de feedback de BravoBot.

Tablas:
  message_feedback  → 👍/👎 por mensaje individual
  session_feedback  → calificación 1–5 ⭐ al cerrar el chat

El archivo feedback.db se crea automáticamente en FEEDBACK_DB_PATH
(default: ./feedback/feedback.db relativo al directorio de trabajo del backend).
"""
import csv
import io
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("bravobot.feedback.store")

# ── Ruta del archivo SQLite ───────────────────────────────────────────────────
_DEFAULT_DB_PATH = str(Path(__file__).parent / "feedback.db")
DB_PATH = os.getenv("FEEDBACK_DB_PATH", _DEFAULT_DB_PATH)


# ── DDL ───────────────────────────────────────────────────────────────────────
_DDL_MESSAGE_FEEDBACK = """
CREATE TABLE IF NOT EXISTS message_feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT    NOT NULL,
    message_id  TEXT    NOT NULL,
    rating      INTEGER NOT NULL,   -- 1 (👍) o -1 (👎)
    query       TEXT,
    respuesta   TEXT,
    categoria   TEXT,
    intent      TEXT,
    timestamp   TEXT    NOT NULL
);
"""

_DDL_SESSION_FEEDBACK = """
CREATE TABLE IF NOT EXISTS session_feedback (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT    NOT NULL,
    rating          INTEGER NOT NULL,   -- 1-5 estrellas
    comment         TEXT,
    n_messages      INTEGER DEFAULT 0,
    n_bot_messages  INTEGER DEFAULT 0,
    categorias      TEXT    DEFAULT '[]',  -- JSON array
    timestamp       TEXT    NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    """Abre (o crea) la conexión SQLite y activa WAL para concurrencia básica."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Crea las tablas si no existen. Llamar en el evento startup de FastAPI."""
    try:
        with _connect() as conn:
            conn.execute(_DDL_MESSAGE_FEEDBACK)
            conn.execute(_DDL_SESSION_FEEDBACK)
        logger.info(f"[feedback] Base de datos inicializada en: {DB_PATH}")
    except Exception as exc:
        logger.error(f"[feedback] Error inicializando base de datos: {exc}")
        raise


# ── Escritura ─────────────────────────────────────────────────────────────────

def save_message_feedback(
    *,
    session_id: str,
    message_id: str,
    rating: int,         # 1 o -1
    query: str | None = None,
    respuesta: str | None = None,
    categoria: str | None = None,
    intent: str | None = None,
) -> None:
    """Persiste un voto 👍/👎 sobre un mensaje individual del bot."""
    ts = datetime.now(timezone.utc).isoformat()
    sql = """
        INSERT INTO message_feedback
            (session_id, message_id, rating, query, respuesta, categoria, intent, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    try:
        with _connect() as conn:
            conn.execute(sql, (session_id, message_id, rating, query, respuesta, categoria, intent, ts))
        logger.info(
            f"[feedback] Mensaje {message_id} calificado: {'👍' if rating == 1 else '👎'} "
            f"(sesión {session_id[:8]}…)"
        )
    except Exception as exc:
        logger.error(f"[feedback] Error guardando feedback de mensaje: {exc}")
        raise


def save_session_feedback(
    *,
    session_id: str,
    rating: int,               # 1-5
    comment: str | None = None,
    n_messages: int = 0,
    n_bot_messages: int = 0,
    categorias: list[str] | None = None,
) -> None:
    """Persiste la calificación 1–5 ⭐ de una sesión completa."""
    ts = datetime.now(timezone.utc).isoformat()
    categorias_json = json.dumps(categorias or [], ensure_ascii=False)
    sql = """
        INSERT INTO session_feedback
            (session_id, rating, comment, n_messages, n_bot_messages, categorias, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    try:
        with _connect() as conn:
            conn.execute(sql, (session_id, rating, comment, n_messages, n_bot_messages, categorias_json, ts))
        stars = "⭐" * rating
        logger.info(
            f"[feedback] Sesión {session_id[:8]}… calificada: {stars} "
            f"({n_bot_messages} mensajes del bot)"
        )
    except Exception as exc:
        logger.error(f"[feedback] Error guardando feedback de sesión: {exc}")
        raise


# ── Lectura / exportación ─────────────────────────────────────────────────────

def get_all_message_feedback() -> list[dict]:
    """Retorna todos los registros de feedback por mensaje."""
    try:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT * FROM message_feedback ORDER BY timestamp DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.error(f"[feedback] Error leyendo message_feedback: {exc}")
        return []


def get_all_session_feedback() -> list[dict]:
    """Retorna todos los registros de feedback de sesiones."""
    try:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT * FROM session_feedback ORDER BY timestamp DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.error(f"[feedback] Error leyendo session_feedback: {exc}")
        return []


def export_message_csv() -> str:
    """Exporta message_feedback como CSV (string)."""
    records = get_all_message_feedback()
    if not records:
        return "id,session_id,message_id,rating,query,respuesta,categoria,intent,timestamp\n"
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=records[0].keys())
    writer.writeheader()
    writer.writerows(records)
    return output.getvalue()


def export_session_csv() -> str:
    """Exporta session_feedback como CSV (string)."""
    records = get_all_session_feedback()
    if not records:
        return "id,session_id,rating,comment,n_messages,n_bot_messages,categorias,timestamp\n"
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=records[0].keys())
    writer.writeheader()
    writer.writerows(records)
    return output.getvalue()
