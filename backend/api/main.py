import logging
import os
import sys
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field, field_validator

sys.path.insert(0, str(Path(__file__).parent.parent))

from feedback import store as feedback_store
from feedback.models import (
    FeedbackResponse,
    MessageFeedbackRequest,
    SessionFeedbackRequest,
)
from logger import (
    get_logger,
    set_request_id,
    set_session_id,
    setup_logging,
    time_logged,
)
from rag.pipeline import ask
from rag.retriever import get_collection
from rag.router import VALID_CATEGORIES
from rag.sanitizer import sanitize_query, sanitize_session_id

# Secret para exportar feedback (configurable vía variable de entorno)
_FEEDBACK_EXPORT_SECRET = os.getenv("FEEDBACK_EXPORT_SECRET", "")

# Inicializar logging centralizado
setup_logging()
logger = get_logger("bravobot.api")

app = FastAPI(
    title="BravoBot API",
    description="Asistente inteligente para aspirantes de la I.U. Pascual Bravo",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept", "Authorization"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware que asigna un request_id único a cada petición entrante
    y loggea método, ruta, status y duración.
    """
    req_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
    set_request_id(req_id)

    # Si la request tiene session_id en query param o body, lo extraemos
    # (para POST se lee después en el endpoint, aquí solo ponemos el request_id)

    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start

    # Para rutas con session_id ya seteado, se reflejará; si no, queda "-"
    logger.info(
        "[HTTP] %s %s → %d (%.0fms)%s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed * 1000,
        f" qs={request.url.query}" if request.url.query else "",
    )
    return response


@app.on_event("startup")
async def startup_event():
    # Inicializar base de datos de feedback (SQLite)
    try:
        feedback_store.init_db()
    except Exception as exc:
        logger.warning(f"No se pudo inicializar feedback DB: {exc}")

    # Cargar colección vectorial
    try:
        get_collection()
        logger.debug("ChromaDB cargado correctamente al iniciar.")
    except Exception as exc:
        logger.warning(
            f"No se pudo cargar ChromaDB al iniciar: {exc}. "
            "Ejecuta run_ingestion.py primero."
        )


class ChatRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Pregunta del aspirante (máx 500 caracteres)",
    )
    session_id: str | None = Field(
        None, max_length=64, description="ID de sesión alfanumérico (máx 64 caracteres)"
    )

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("La query no puede ser solo espacios en blanco.")
        return v

    @field_validator("session_id")
    @classmethod
    def session_id_format(cls, v: str | None) -> str | None:
        if v is None:
            return None
        import re

        if not re.match(r"^[a-zA-Z0-9_-]{1,64}$", v):
            raise ValueError(
                "session_id inválido. Solo alfanuméricos, guiones y guiones bajos (máx 64 chars)."
            )
        return v


class ChatResponse(BaseModel):
    respuesta: str
    fuentes: list[str]
    categoria: str
    categorias: list[str]
    intent: str | None = None
    session_id: str | None = None


# Almacenamiento en memoria para el historial de conversaciones
# Formato: { "session_id": [{"role": "user", "text": "..." }, {"role": "model", "text": "..."}] }
sessions: dict[str, list[dict]] = {}
MAX_HISTORY_LENGTH = 10  # Máximo de mensajes por sesión
MAX_SESSIONS = 1000  # Máximo de sesiones activas en memoria


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # Sanitizar inputs (segunda capa de defensa tras la validación Pydantic)
    try:
        clean_query = sanitize_query(request.query)
        clean_session_id = sanitize_session_id(request.session_id)
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))

    try:
        history = []

        # Propagar session_id al contexto de logging
        set_session_id(clean_session_id)

        if clean_session_id:
            # Protección contra memory flooding: limitar sesiones activas
            if clean_session_id not in sessions and len(sessions) >= MAX_SESSIONS:
                logger.warning(
                    "[SECURITY] Límite de sesiones activas (%d) alcanzado. "
                    "Rechazando nueva sesión (último session_id=%s).",
                    MAX_SESSIONS,
                    list(sessions.keys())[-1][:12] if sessions else "?",
                )
                raise HTTPException(
                    status_code=429,
                    detail="Demasiadas sesiones activas. Inténtalo más tarde.",
                )
            if clean_session_id not in sessions:
                logger.info(
                    "[SESSION] Nueva sesión creada (total activas: %d)",
                    len(sessions) + 1,
                )
                sessions[clean_session_id] = []
            history = sessions[clean_session_id]

        logger.info(
            "[CHAT] Query: %.100s | history_turns=%d",
            clean_query,
            len(history) // 2,
        )

        # Llamada al pipeline RAG con historial
        with time_logged("pipeline_completo", logger, level=logging.INFO):
            result = ask(clean_query, history=history)

        # Actualizar historial con rotación FIFO
        if clean_session_id:
            sessions[clean_session_id].append({"role": "user", "text": clean_query})
            sessions[clean_session_id].append(
                {"role": "model", "text": result["respuesta"]}
            )
            # Mantener solo los últimos N mensajes
            if len(sessions[clean_session_id]) > MAX_HISTORY_LENGTH:
                sessions[clean_session_id] = sessions[clean_session_id][
                    -MAX_HISTORY_LENGTH:
                ]
                logger.debug(
                    "[SESSION] Historial rotado a últimos %d mensajes",
                    MAX_HISTORY_LENGTH,
                )

        logger.info(
            "[CHAT] → intent=%s categorias=%s fuentes=%d respuesta_len=%d",
            result.get("intent", "?"),
            result.get("categorias", []),
            len(result.get("fuentes", [])),
            len(result.get("respuesta", "")),
        )

        return ChatResponse(
            respuesta=result["respuesta"],
            fuentes=result["fuentes"],
            categoria=result["categoria"],
            categorias=result.get("categorias", [result["categoria"]]),
            intent=result.get("intent"),
            session_id=clean_session_id,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error en /chat")
        raise HTTPException(status_code=500, detail="Error interno del servidor.")


@app.get("/categorias")
async def get_categorias():
    return {"categorias": list(VALID_CATEGORIES)}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "BravoBot API"}


# ── Endpoints de Feedback ─────────────────────────────────────────────────────


@app.post("/feedback/message", response_model=FeedbackResponse)
async def submit_message_feedback(req: MessageFeedbackRequest):
    """
    Recibe el voto 👍 (rating=1) o 👎 (rating=-1) de un mensaje individual del bot.
    """
    try:
        feedback_store.save_message_feedback(
            session_id=req.session_id,
            message_id=req.message_id,
            rating=req.rating,
            query=req.query,
            respuesta=req.respuesta,
            categoria=req.categoria,
            intent=req.intent,
        )
        return FeedbackResponse(ok=True, message="Feedback de mensaje registrado.")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error en /feedback/message")
        raise HTTPException(status_code=500, detail="No se pudo guardar el feedback.")


@app.post("/feedback/session", response_model=FeedbackResponse)
async def submit_session_feedback(req: SessionFeedbackRequest):
    """
    Recibe la calificación 1–5 ⭐ de una sesión completa de chat.
    Se dispara cuando el usuario cierra el chat tras ≥2 respuestas del bot.
    """
    try:
        feedback_store.save_session_feedback(
            session_id=req.session_id,
            rating=req.rating,
            comment=req.comment,
            n_messages=req.n_messages,
            n_bot_messages=req.n_bot_messages,
            categorias=req.categorias,
        )
        return FeedbackResponse(ok=True, message="¡Gracias por tu calificación!")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error en /feedback/session")
        raise HTTPException(
            status_code=500, detail="No se pudo guardar la calificación."
        )


@app.get("/feedback/export")
async def export_feedback(
    secret: str = Query("", description="Clave de exportación"),
    tabla: str = Query("session", description="'session' o 'message'"),
):
    """
    Exporta los registros de feedback como CSV.
    Requiere el parámetro ?secret= configurado en FEEDBACK_EXPORT_SECRET.
    Uso: GET /feedback/export?secret=tu_clave&tabla=session
    """
    if not _FEEDBACK_EXPORT_SECRET or secret != _FEEDBACK_EXPORT_SECRET:
        raise HTTPException(status_code=403, detail="Acceso no autorizado.")

    if tabla == "message":
        csv_content = feedback_store.export_message_csv()
        filename = "feedback_mensajes.csv"
    else:
        csv_content = feedback_store.export_session_csv()
        filename = "feedback_sesiones.csv"

    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
