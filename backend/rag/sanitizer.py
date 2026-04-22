"""
sanitizer.py
============
Sanitización centralizada de entrada de usuario antes de que llegue a cualquier
prompt LLM. Neutraliza prompt-injection y limpia caracteres peligrosos.
"""

import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

# Longitud máxima permitida (en caracteres) para una query de usuario
MAX_QUERY_LENGTH = 500

# Patrones que indican intento de prompt injection.
# Se buscan en minúsculas y sin acentos para mayor cobertura.
_INJECTION_PATTERNS: list[re.Pattern] = [
    # Instrucciones de override en inglés
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.I),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)", re.I),
    re.compile(r"forget\s+(all\s+)?(previous|prior|above|everything)", re.I),
    re.compile(r"you\s+are\s+now\s+a", re.I),
    re.compile(r"act\s+as\s+(if\s+you\s+are|a)\s+", re.I),
    # Instrucciones de override en español
    re.compile(r"ignora\s+(todo|todas|todas\s+las)?\s*(instrucciones?|reglas?|lo\s+anterior)", re.I),
    re.compile(r"olvida\s+(todo|todas|las\s+instrucciones?|lo\s+anterior)", re.I),
    re.compile(r"nueva\s+instrucci[oó]n", re.I),
    re.compile(r"ahora\s+eres\s+", re.I),
    re.compile(r"a\s+partir\s+de\s+ahora\s+(eres|debes|tienes\s+que)", re.I),
    # Marcadores de rol/sistema usados en templates de modelos
    re.compile(r"\[INST\]", re.I),
    re.compile(r"<<\s*SYS\s*>>", re.I),
    re.compile(r"<\|im_start\|>", re.I),
    re.compile(r"<\|im_end\|>", re.I),
    re.compile(r"<SYSTEM>", re.I),
    re.compile(r"</s>"),
    # Intentos de inyectar roles directamente
    re.compile(r"^(system|user|assistant)\s*:", re.I | re.MULTILINE),
    re.compile(r"\n\s*(system|user|assistant)\s*:", re.I),
    # Prompt leaking
    re.compile(r"repeat\s+(the\s+)?(above|everything|all|your\s+instructions?)", re.I),
    re.compile(r"muestra?\s+(el\s+)?(prompt|instrucciones?|sistema)", re.I),
    re.compile(r"print\s+(the\s+)?(system\s+prompt|instructions?)", re.I),
]

# Caracteres de control que deben eliminarse (excepto \n y \t que son legítimos)
_CONTROL_CHARS_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f]"
)


def _normalize(text: str) -> str:
    """Normaliza unicode NFC para comparaciones consistentes."""
    return unicodedata.normalize("NFC", text)


def _strip_control_chars(text: str) -> str:
    """Elimina caracteres de control peligrosos preservando saltos de línea y tabs."""
    return _CONTROL_CHARS_RE.sub("", text)


def _detect_injection(text: str) -> bool:
    """Retorna True si se detecta algún patrón de prompt injection."""
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return True
    return False


def sanitize_query(raw: str) -> str:
    """
    Sanitiza la query del usuario para uso seguro en prompts LLM.

    Pasos:
    1. Normalizar unicode
    2. Eliminar caracteres de control
    3. Strip de whitespace extremo
    4. Truncar a MAX_QUERY_LENGTH caracteres
    5. Detectar y loguear intentos de prompt injection
       (no se bloquea la query, pero queda registrado y se neutralizan
       los marcadores de rol/sistema más peligrosos)

    Returns:
        str: query limpia y segura.
    Raises:
        ValueError: si la query queda vacía tras sanitizar.
    """
    if not isinstance(raw, str):
        raise ValueError("La query debe ser un string.")

    text = _normalize(raw)
    text = _strip_control_chars(text)
    text = text.strip()

    if not text:
        raise ValueError("La query está vacía tras sanitización.")

    # Truncar ANTES de la detección para no analizar texto masivo
    if len(text) > MAX_QUERY_LENGTH:
        logger.warning(
            f"Query truncada de {len(text)} a {MAX_QUERY_LENGTH} caracteres."
        )
        text = text[:MAX_QUERY_LENGTH]

    # Detección de injection (sólo log, no bloqueo — el LLM tiene sus propias guardrails)
    if _detect_injection(text):
        logger.warning(
            f"[SECURITY] Posible prompt-injection detectado en query: {text[:120]!r}"
        )

    # Neutralizar marcadores de sistema más peligrosos que podrían confundir al LLM
    # (se reemplazan por versiones inofensivas)
    text = re.sub(r"\[INST\]", "[inst]", text, flags=re.I)
    text = re.sub(r"<<\s*SYS\s*>>", "", text, flags=re.I)
    text = re.sub(r"<\|im_start\|>", "", text, flags=re.I)
    text = re.sub(r"<\|im_end\|>", "", text, flags=re.I)
    text = re.sub(r"</?SYSTEM>", "", text, flags=re.I)

    return text


def sanitize_session_id(session_id: str | None) -> str | None:
    """
    Valida que el session_id tenga formato seguro.
    Solo permite alfanuméricos, guiones y guiones bajos (máx 64 chars).

    Returns:
        str | None: session_id validado o None si es None/inválido.
    Raises:
        ValueError: si el formato es inválido.
    """
    if session_id is None:
        return None

    if not isinstance(session_id, str):
        raise ValueError("session_id debe ser un string.")

    if not re.match(r"^[a-zA-Z0-9_-]{1,64}$", session_id):
        raise ValueError(
            "session_id inválido. Solo se permiten letras, números, guiones "
            "y guiones bajos (máximo 64 caracteres)."
        )

    return session_id
