import logging
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.pipeline import ask
from rag.retriever import get_collection
from rag.router import VALID_CATEGORIES
from rag.sanitizer import sanitize_query, sanitize_session_id

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("bravobot.api")

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


@app.on_event("startup")
async def startup_event():
    try:
        get_collection()
        logger.info("ChromaDB cargado correctamente al iniciar.")
    except Exception as exc:
        logger.warning(
            f"No se pudo cargar ChromaDB al iniciar: {exc}. "
            "Ejecuta run_ingestion.py primero."
        )


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Pregunta del aspirante (máx 500 caracteres)")
    session_id: str | None = Field(None, max_length=64, description="ID de sesión alfanumérico (máx 64 caracteres)")

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
            raise ValueError("session_id inválido. Solo alfanuméricos, guiones y guiones bajos (máx 64 chars).")
        return v


class ChatResponse(BaseModel):
    respuesta: str
    fuentes: list[str]
    categoria: str
    categorias: list[str]
    session_id: str | None = None


# Almacenamiento en memoria para el historial de conversaciones
# Formato: { "session_id": [{"role": "user", "text": "..." }, {"role": "model", "text": "..."}] }
sessions: dict[str, list[dict]] = {}
MAX_HISTORY_LENGTH = 10   # Máximo de mensajes por sesión
MAX_SESSIONS = 1000       # Máximo de sesiones activas en memoria


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

        if clean_session_id:
            # Protección contra memory flooding: limitar sesiones activas
            if clean_session_id not in sessions and len(sessions) >= MAX_SESSIONS:
                logger.warning(
                    f"[SECURITY] Límite de sesiones activas ({MAX_SESSIONS}) alcanzado. "
                    "Rechazando nueva sesión."
                )
                raise HTTPException(
                    status_code=429,
                    detail="Demasiadas sesiones activas. Inténtalo más tarde.",
                )
            if clean_session_id not in sessions:
                sessions[clean_session_id] = []
            history = sessions[clean_session_id]

        # Llamada al pipeline RAG con historial
        result = ask(clean_query, history=history)

        # Actualizar historial
        if clean_session_id:
            sessions[clean_session_id].append({"role": "user", "text": clean_query})
            sessions[clean_session_id].append({"role": "model", "text": result["respuesta"]})
            # Mantener solo los últimos N mensajes
            if len(sessions[clean_session_id]) > MAX_HISTORY_LENGTH:
                sessions[clean_session_id] = sessions[clean_session_id][-MAX_HISTORY_LENGTH:]

        return ChatResponse(
            respuesta=result["respuesta"],
            fuentes=result["fuentes"],
            categoria=result["categoria"],
            categorias=result.get("categorias", [result["categoria"]]),
            session_id=clean_session_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error en /chat: {exc}")
        raise HTTPException(status_code=500, detail="Error interno del servidor.")


@app.get("/categorias")
async def get_categorias():
    return {"categorias": list(VALID_CATEGORIES)}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "BravoBot API"}
