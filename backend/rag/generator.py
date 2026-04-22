import logging
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GENERATOR_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """Eres BravoBot, el asistente virtual oficial de la Institución Universitaria Pascual Bravo.
Tu rol es ayudar a los aspirantes a obtener información clara, precisa y confiable sobre la institución.

REGLAS ESTRICTAS:
1. Responde ÚNICAMENTE con base en la información del contexto proporcionado.
2. Si el contexto no contiene información suficiente para responder, di exactamente: "No encontré información sobre eso en el sitio oficial. Te recomiendo consultar directamente en pascualbravo.edu.co o comunicarte con la institución."
3. NUNCA inventes datos, fechas, costos, nombres de programas ni requisitos.
4. Responde siempre en español, con tono amable, profesional e institucional.
5. Sé conciso pero completo. Si la información es extensa, organízala con bullets o secciones cortas.
6. No menciones que estás usando un "contexto" o "fragmentos" — responde como si conocieras la información directamente.
7. Si el contexto incluye una sección "MALLA CURRICULAR ESTRUCTURADA", úsala con prioridad para responder preguntas sobre materias, semestres o créditos. Esa sección contiene datos oficiales estructurados.
8. Cuando respondas sobre mallas curriculares, presenta la información organizada por semestre en formato lista o tabla. Incluye el nombre de la materia y sus créditos.
9. Si la pregunta abarca múltiples temas (por ejemplo costos y programas), responde todos los aspectos con la información disponible en el contexto.

CONTEXTO:
{contexto}

PREGUNTA DEL ASPIRANTE:
{query}

RESPUESTA:"""

NO_INFO_RESPONSE = (
    "No encontré información sobre eso en el sitio oficial. "
    "Te recomiendo consultar directamente en pascualbravo.edu.co "
    "o comunicarte con la institución."
)


def _build_contexto(chunks: list[dict], malla_context: dict | None) -> str:
    parts = []

    if chunks:
        parts.append("## Información recuperada del sitio oficial")
        for i, chunk in enumerate(chunks, 1):
            parts.append(f"[{i}] {chunk['texto']}")

    if malla_context:
        parts.append("\n## MALLA CURRICULAR ESTRUCTURADA")
        if "semesters" in malla_context:
            prog = malla_context
            parts.append(
                f"Programa: {prog['name']} | "
                f"Nivel: {prog.get('level', 'N/A')} | "
                f"Duración: {prog.get('duration', 'N/A')}"
            )
            for sem in prog["semesters"]:
                materias = ", ".join(
                    f"{c['name']} ({c['credits']} cr)"
                    for c in sem.get("courses", [])
                )
                parts.append(f"Semestre {sem['semester']}: {materias}")
        elif "courses" in malla_context:
            for c in malla_context["courses"]:
                parts.append(
                    f"- {c['course_name']} | Programa: {c['program_name']} "
                    f"| Semestre {c['semester']} | {c['credits']} créditos"
                )

    return "\n\n".join(parts)


def generate_response(
    query: str,
    chunks: list[dict],
    malla_context: dict | None = None,
) -> dict:
    if not chunks and not malla_context:
        return {"respuesta": NO_INFO_RESPONSE, "fuentes": []}

    contexto = _build_contexto(chunks, malla_context)
    fuentes = list(dict.fromkeys(c["url"] for c in chunks if c.get("url")))

    prompt = SYSTEM_PROMPT.format(contexto=contexto, query=query)

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GENERATOR_MODEL,
            contents=prompt,
        )
        respuesta = response.text.strip()
    except Exception as exc:
        logger.error(f"Error en generator: {exc}")
        respuesta = NO_INFO_RESPONSE
        fuentes = []

    return {"respuesta": respuesta, "fuentes": fuentes}
