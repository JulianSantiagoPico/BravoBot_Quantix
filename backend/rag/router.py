import logging
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ROUTER_MODEL = "gemini-2.5-flash"

VALID_CATEGORIES = {
    "admisiones",
    "programas",
    "costos",
    "bienestar",
    "becas",
    "institucional",
    "noticias",
    "general",
}

ROUTER_PROMPT = """Clasifica la siguiente pregunta de un aspirante universitario en una o dos de estas categorías:
- admisiones: preguntas sobre inscripción, fechas, requisitos, proceso de admisión, calendario académico
- programas: preguntas sobre carreras, programas académicos, mallas curriculares, posgrados, maestrías, materias, semestres, pensum, créditos
- costos: preguntas sobre matrículas, derechos pecuniarios, precios, pagos, valor de la matrícula
- bienestar: preguntas sobre servicios, prácticas profesionales, inglés, bienestar universitario
- becas: preguntas sobre becas, financiamiento, apoyo socioeconómico, subsidios
- institucional: preguntas sobre la institución, historia, filosofía, acreditación, misión, visión
- noticias: preguntas sobre novedades, eventos recientes
- general: cualquier otra pregunta

REGLAS:
1. Si la pregunta toca claramente DOS categorías, responde con ambas separadas por "+". Máximo 2 categorías.
2. Si la pregunta es de una sola categoría, responde solo esa etiqueta.
3. Responde ÚNICAMENTE con la(s) etiqueta(s), sin explicación adicional.

EJEMPLOS:
Pregunta: ¿Cuánto cuesta estudiar ingeniería de sistemas? → costos+programas
Pregunta: ¿Qué materias tiene el primer semestre de electrónica industrial? → programas
Pregunta: ¿Cuándo son las inscripciones para el próximo semestre? → admisiones
Pregunta: ¿El Pascual Bravo está acreditado? → institucional
Pregunta: ¿Tienen becas para estratos 1 y 2? → becas
Pregunta: ¿Qué valor tiene la matrícula y qué becas hay disponibles? → costos+becas
Pregunta: ¿Cuáles son los requisitos de admisión para una maestría? → admisiones+programas
Pregunta: ¿Qué servicios ofrece bienestar universitario? → bienestar
Pregunta: ¿Cuántos créditos tiene la malla de ingeniería mecánica? → programas
Pregunta: ¿Hay prácticas profesionales remuneradas? → bienestar
Pregunta: ¿Cuándo empiezan clases el próximo semestre? → admisiones

Pregunta: {query}"""


def classify_query(query: str) -> list[str]:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=ROUTER_MODEL,
            contents=ROUTER_PROMPT.format(query=query),
        )
        raw = response.text.strip().lower().replace(".", "").replace(":", "")
        categorias = [c.strip() for c in raw.split("+") if c.strip() in VALID_CATEGORIES]
        if not categorias:
            logger.warning(f"Categoría(s) desconocida(s) '{raw}', usando 'general'")
            return ["general"]
        logger.info(f"Categorías clasificadas: {categorias}")
        return categorias
    except Exception as exc:
        logger.error(f"Error en router: {exc}")
        return ["general"]
