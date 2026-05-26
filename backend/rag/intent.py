"""
intent.py
=========
Clasificador de intención conversacional basado en heurísticas de keywords.
No requiere llamada adicional al LLM — cero latencia extra.

Intenciones posibles:
  conversational  → meta-operación sobre la respuesta anterior (resumir, ampliar, simplificar…)
  comparison      → comparación explícita entre dos o más programas/servicios
  recommendation  → solicitud de recomendación personalizada
  followup        → pregunta corta que solo tiene sentido en contexto de la conversación
  informational   → consulta informativa estándar (comportamiento por defecto)
"""

import logging
import re

from logger import get_logger

logger = get_logger("bravobot.intent")

# ── Patrones por intención ────────────────────────────────────────────────────

_CONVERSATIONAL_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bresume\b", re.I),
    re.compile(r"\bresumelo\b|\bresúmelo\b", re.I),
    re.compile(r"\bresumeme\b|\brésumeme\b|\bres[uú]meme\b", re.I),
    re.compile(r"\bresumila\b|\bres[uú]mila\b", re.I),
    re.compile(r"\bresumid[ao]\b|\bres[uú]mid[ao]\b", re.I),
    re.compile(r"\bres[uú]mir\b", re.I),
    re.compile(r"\bsimplifica\b", re.I),
    re.compile(r"\bampl[ií]a\b|\bamplia\b", re.I),
    re.compile(r"\breformula\b", re.I),
    re.compile(
        r"\bexplica\w*\s+(de\s+nuevo|otra\s+vez|m[aá]s\s+(simple|sencillo|claro|f[aá]cil))\b",
        re.I,
    ),
    re.compile(
        r"\bhazlo\s+(m[aá]s\s+)?(corto|breve|simple|sencillo|detallado|largo|claro)\b",
        re.I,
    ),
    re.compile(r"\bes\s+muy\s+largo\b|\bm[aá]s\s+corto\b|\bm[aá]s\s+breve\b", re.I),
    re.compile(r"\ben\s+pocas\s+palabras\b|\ben\s+resumen\b", re.I),
    re.compile(r"\bpuedes\s+(resumir|simplificar|ampliar|explicar\s+m[aá]s)\b", re.I),
    re.compile(
        r"\bm[aá]s\s+simple\b|\bm[aá]s\s+sencillo\b|\bm[aá]s\s+detallado\b", re.I
    ),
    re.compile(
        r"\blo\s+anterior\s+(de\s+forma\s+)?(m[aá]s\s+)?(simple|breve|corta?)\b", re.I
    ),
    re.compile(r"\brepite\b|\brepetir\b", re.I),
    re.compile(r"\bdi(me)?\s+lo\s+mismo\s+pero\b", re.I),
]

_COMPARISON_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bcompara\w*\b", re.I),
    re.compile(r"\bdiferencia[s]?\s+(entre|de)\b", re.I),
    re.compile(r"\bdiferencia\s+(hay|existe)\b", re.I),
    re.compile(r"\bvs\.?\b|\bversus\b", re.I),
    re.compile(r"\bmejor\s+entre\b", re.I),
    re.compile(
        r"\bcu[aá]l\s+(es\s+)?(mejor|m[aá]s\s+\w+)\s+(entre|de\s+(los|las))\b", re.I
    ),
    re.compile(r"\bqu[eé]\s+diferencia\s+(hay|tiene|tienen)\b", re.I),
    re.compile(r"\buno\s+vs\.?\s+otro\b|\buno\s+versus\s+otro\b", re.I),
    re.compile(r"\bcu[aá]l\s+tiene\s+m[aá]s\b", re.I),
    re.compile(r"\bparecidos?\b|\bsimilares?\b|\biguales?\b.*\bprograma\b", re.I),
    re.compile(r"\bcontrasta\w*\b", re.I),
]

_RECOMMENDATION_PATTERNS: list[re.Pattern] = [
    re.compile(r"\brecomiend[ae]\w*\b|\brecomendaci[oó]n\b", re.I),
    re.compile(
        r"\bqu[eé]\s+carrera\s+(me\s+)?(recomiend[ae]|deber[ií]a|conviene|es\s+mejor\s+para)\b",
        re.I,
    ),
    re.compile(
        r"\bcu[aá]l\s+(carrera|programa)\s+(elegir[ií]a|escoger[ií]a|me\s+conviene|me\s+sirve)\b",
        re.I,
    ),
    re.compile(
        r"\bme\s+gusta[n]?\s+(las?\s+)?\b(matem[aá]ticas|programaci[oó]n|electr[oó]nica|f[ií]sica|biolog[ií]a|arte|dise[nñ]o)\b",
        re.I,
    ),
    re.compile(r"\bme\s+interes[ae]\b", re.I),
    re.compile(r"\bpara\s+alguien\s+que\b|\bpara\s+alguien\s+a\s+quien\b", re.I),
    re.compile(
        r"\bqu[eé]\s+perfil\b|\bqu[eé]\s+programa\s+es\s+para\s+(m[ií]|mi)\b", re.I
    ),
    re.compile(r"\bno\s+s[eé]\s+qu[eé]\s+estudiar\b|\bqu[eé]\s+estudiar\b", re.I),
    re.compile(r"\bsoy\s+(bueno|mala?|regular)\s+en\b", re.I),
    re.compile(r"\btengo\s+habilidad(es)?\s+en\b|\bme\s+destaco\s+en\b", re.I),
    re.compile(r"\bcu[aá]l\s+me\s+conviene\b|\bcu[aá]l\s+me\s+va\s+mejor\b", re.I),
    re.compile(r"\bqu[eé]\s+me\s+recomiend[ae]\b", re.I),
    re.compile(r"\borienta\w*me\b", re.I),
    re.compile(r"\bayuda\w*me\s+a\s+elegir\b|\bayuda\w*me\s+a\s+escoger\b", re.I),
]

# Deícticos/pronombres que indican que la pregunta necesita contexto previo
_DEICTIC_PATTERNS: list[re.Pattern] = [
    re.compile(r"\besa\s+carrera\b|\bese\s+programa\b|\besa\s+opci[oó]n\b", re.I),
    re.compile(r"\blo\s+mismo\b|\beso\s+mismo\b", re.I),
    re.compile(r"\beso\s+que\s+(dijiste|mencionaste|nombraste)\b", re.I),
    re.compile(r"\b(de\s+)?ah[ií]\b", re.I),
    re.compile(r"\bde\s+esa\s+carrera\b|\bde\s+ese\s+programa\b", re.I),
    re.compile(r"\btambi[eé]n\s+(de\s+)?(ella|ese|esa|ellos)\b", re.I),
]

# Palabras que, al inicio de una query corta, indican followup
_FOLLOWUP_STARTERS: list[re.Pattern] = [
    re.compile(r"^y\s+", re.I),
    re.compile(r"^tambi[eé]n\b", re.I),
    re.compile(r"^qu[eé]\s+m[aá]s\b", re.I),
    re.compile(r"^algo\s+m[aá]s\b", re.I),
    re.compile(r"^(y\s+)?los?\s+costos?\b", re.I),
    re.compile(r"^(y\s+)?las?\s+fechas?\b", re.I),
    re.compile(r"^(y\s+)?los?\s+requisitos?\b", re.I),
    re.compile(r"^(y\s+)?las?\s+becas?\b", re.I),
    re.compile(r"^(y\s+)?el\s+precio\b", re.I),
    re.compile(r"^(y\s+)?la\s+duraci[oó]n\b", re.I),
    re.compile(r"^(y\s+)?cu[aá]nto\b", re.I),
    re.compile(r"^(y\s+)?cu[aá]ndo\b", re.I),
    re.compile(r"^(y\s+)?d[oó]nde\b", re.I),
    re.compile(r"^m[aá]s\s+info\b|\bm[aá]s\s+informaci[oó]n\b", re.I),
    re.compile(r"^(y\s+)?(en\s+)?presencial\b", re.I),
    re.compile(r"^(y\s+)?(en\s+)?virtual\b", re.I),
]

_FOLLOWUP_MAX_WORDS = 7


def _matches_any(text: str, patterns: list[re.Pattern]) -> bool:
    return any(p.search(text) for p in patterns)


def classify_intent(query: str, history: list[dict] | None = None) -> str:
    """
    Clasifica la intención de la query del usuario.

    Args:
        query: Texto de la consulta del usuario.
        history: Historial de conversación del formato [{"role": ..., "text": ...}].

    Returns:
        str: Una de: "conversational", "comparison", "recommendation", "followup", "informational"
    """
    q = query.strip()
    word_count = len(q.split())
    has_history = bool(history)

    # 1. Conversacional — tiene prioridad sobre todo lo demás
    if _matches_any(q, _CONVERSATIONAL_PATTERNS):
        logger.debug("[intent] conversational")
        return "conversational"

    # 2. Comparación
    if _matches_any(q, _COMPARISON_PATTERNS):
        logger.debug("[intent] comparison")
        return "comparison"

    # 3. Recomendación
    if _matches_any(q, _RECOMMENDATION_PATTERNS):
        logger.debug("[intent] recommendation")
        return "recommendation"

    # 4. Followup — query corta con historial O deícticos presentes
    if has_history:
        if word_count <= _FOLLOWUP_MAX_WORDS:
            logger.debug("[intent] followup (short query + history)")
            return "followup"
        if _matches_any(q, _DEICTIC_PATTERNS) or _matches_any(q, _FOLLOWUP_STARTERS):
            logger.debug("[intent] followup (deictic/starter)")
            return "followup"

    # 5. Default
    logger.debug("[intent] informational")
    return "informational"
