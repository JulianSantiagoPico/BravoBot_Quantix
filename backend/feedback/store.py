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
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from logger import get_logger

logger = get_logger("bravobot.feedback.store")

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


@contextmanager
def _connection():
    """Context manager que confirma/rollback y siempre cierra la conexión."""
    conn = _connect()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Crea las tablas si no existen. Llamar en el evento startup de FastAPI."""
    try:
        with _connection() as conn:
            conn.execute(_DDL_MESSAGE_FEEDBACK)
            conn.execute(_DDL_SESSION_FEEDBACK)
        logger.debug(f"[feedback] Base de datos inicializada en: {DB_PATH}")
    except Exception as exc:
        logger.error(f"[feedback] Error inicializando base de datos: {exc}")
        raise


# ── Escritura ─────────────────────────────────────────────────────────────────


def save_message_feedback(
    *,
    session_id: str,
    message_id: str,
    rating: int,  # 1 o -1
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
        with _connection() as conn:
            conn.execute(
                sql,
                (
                    session_id,
                    message_id,
                    rating,
                    query,
                    respuesta,
                    categoria,
                    intent,
                    ts,
                ),
            )
        logger.debug(
            f"[feedback] Mensaje {message_id} calificado: {'👍' if rating == 1 else '👎'} "
            f"(sesión {session_id[:8]}…)"
        )
    except Exception as exc:
        logger.error(f"[feedback] Error guardando feedback de mensaje: {exc}")
        raise


def save_session_feedback(
    *,
    session_id: str,
    rating: int,  # 1-5
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
        with _connection() as conn:
            conn.execute(
                sql,
                (
                    session_id,
                    rating,
                    comment,
                    n_messages,
                    n_bot_messages,
                    categorias_json,
                    ts,
                ),
            )
        stars = "⭐" * rating
        logger.debug(
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
        with _connection() as conn:
            rows = conn.execute(
                "SELECT * FROM message_feedback ORDER BY timestamp DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.error(f"[feedback] Error leyendo message_feedback: {exc}")
        return []


def _tokenize(text: str | None) -> set[str]:
    """Tokenización ligera para comparar queries sin añadir dependencias."""
    if not text:
        return set()
    return set(re.findall(r"[a-záéíóúüñ0-9]{3,}", text.lower()))


def _clip(text: str | None, max_chars: int) -> str | None:
    if text is None:
        return None
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rstrip() + "…"


def get_relevant_message_feedback(
    *,
    query: str,
    categorias: list[str] | None = None,
    intent: str | None = None,
    limit_per_rating: int = 2,
) -> dict[str, list[dict]]:
    """
    Recupera ejemplos de feedback de mensajes relacionados con la query actual.

    El objetivo no es usar el feedback como fuente factual, sino como señal de
    preferencia: qué estilos/respuestas fueron útiles o poco útiles para temas
    similares. Se usa matching léxico simple para evitar nuevas dependencias.
    """
    records = get_all_message_feedback()
    if not records:
        return {"positive": [], "negative": []}

    query_tokens = _tokenize(query)
    category_set = {c.lower() for c in (categorias or [])}
    intent_norm = intent.lower() if intent else None

    scored: list[tuple[int, str, dict]] = []
    for record in records:
        score = len(query_tokens & _tokenize(record.get("query")))

        record_category = (record.get("categoria") or "").lower()
        if record_category and record_category in category_set:
            score += 3

        record_intent = (record.get("intent") or "").lower()
        if intent_norm and record_intent == intent_norm:
            score += 1

        if score <= 0:
            continue

        scored.append((score, record.get("timestamp") or "", record))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)

    result = {"positive": [], "negative": []}
    for _, _, record in scored:
        bucket = "positive" if record.get("rating") == 1 else "negative"
        if bucket not in result or len(result[bucket]) >= limit_per_rating:
            continue
        result[bucket].append(
            {
                "query": _clip(record.get("query"), 300),
                "respuesta": _clip(record.get("respuesta"), 1000),
                "categoria": record.get("categoria"),
                "intent": record.get("intent"),
                "rating": record.get("rating"),
            }
        )

        if all(len(items) >= limit_per_rating for items in result.values()):
            break

    return result


def get_all_session_feedback() -> list[dict]:
    """Retorna todos los registros de feedback de sesiones."""
    try:
        with _connection() as conn:
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
