"""
feedback/models.py — Modelos Pydantic para los endpoints de feedback de BravoBot.
"""
import re

from pydantic import BaseModel, Field, field_validator


class MessageFeedbackRequest(BaseModel):
    """Payload para POST /feedback/message — voto 👍/👎 sobre un mensaje individual."""

    session_id: str = Field(..., max_length=64, description="ID de sesión alfanumérico")
    message_id: str = Field(..., max_length=64, description="ID del mensaje calificado")
    rating: int = Field(..., description="1 para 👍, -1 para 👎")
    query: str | None = Field(None, max_length=500, description="Pregunta del usuario asociada")
    respuesta: str | None = Field(None, max_length=4000, description="Respuesta del bot calificada")
    categoria: str | None = Field(None, max_length=64)
    intent: str | None = Field(None, max_length=64)

    @field_validator("session_id", "message_id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_\-]{1,64}$", v):
            raise ValueError("ID inválido. Solo alfanuméricos, guiones y guiones bajos.")
        return v

    @field_validator("rating")
    @classmethod
    def validate_rating_binary(cls, v: int) -> int:
        if v not in (1, -1):
            raise ValueError("rating debe ser 1 (👍) o -1 (👎)")
        return v


class SessionFeedbackRequest(BaseModel):
    """Payload para POST /feedback/session — calificación 1–5 ⭐ al cerrar el chat."""

    session_id: str = Field(..., max_length=64)
    rating: int = Field(..., ge=1, le=5, description="Calificación de 1 a 5 estrellas")
    comment: str | None = Field(None, max_length=500, description="Comentario opcional")
    n_messages: int = Field(0, ge=0, description="Total de mensajes en la sesión")
    n_bot_messages: int = Field(0, ge=0, description="Mensajes del bot en la sesión")
    categorias: list[str] = Field(default_factory=list, description="Categorías consultadas")

    @field_validator("session_id")
    @classmethod
    def validate_session(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_\-]{1,64}$", v):
            raise ValueError("session_id inválido.")
        return v

    @field_validator("comment")
    @classmethod
    def sanitize_comment(cls, v: str | None) -> str | None:
        if v is None:
            return None
        # Quitar caracteres de control excepto saltos de línea y tabulaciones
        cleaned = re.sub(r"[^\S\n\t ]+", " ", v.strip())
        return cleaned if cleaned else None


class FeedbackResponse(BaseModel):
    """Respuesta estándar para ambos endpoints de feedback."""

    ok: bool
    message: str
