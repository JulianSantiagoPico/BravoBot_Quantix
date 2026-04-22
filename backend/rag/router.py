import logging
import os

from dotenv import load_dotenv
from google import genai

from .sanitizer import sanitize_query

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ROUTER_MODEL = "gemini-3.1-flash-lite-preview"

VALID_CATEGORIES = {
    "admisiones",
    "programas",
    "costos",
    "bienestar",
    "becas",
    "institucional",
    "general",
}

ROUTER_PROMPT = """Clasifica la siguiente pregunta de un aspirante universitario en hasta TRES de estas categorías:
- admisiones: preguntas sobre inscripción, fechas, requisitos, proceso de admisión, calendario académico
- programas: preguntas sobre carreras, programas académicos, mallas curriculares, posgrados, maestrías, materias, semestres, pensum, créditos
- costos: preguntas sobre matrículas, derechos pecuniarios, precios, pagos, valor de la matrícula, costos de gimnasio, certificados
- bienestar: preguntas sobre servicios, prácticas profesionales, inglés, bienestar universitario, deportes, gimnasio, salud
- becas: preguntas sobre becas, financiamiento, apoyo socioeconómico, subsidios
- institucional: preguntas sobre la institución, historia, filosofía, acreditación, misión, visión
- general: cualquier otra pregunta

REGLAS:
1. Si la pregunta abarca múltiples temas, devuelve todas las categorías correspondientes separadas por "+". Máximo 3 categorías.
2. Si la pregunta es de una sola categoría, responde solo esa etiqueta.
3. Responde ÚNICAMENTE con la(s) etiqueta(s), sin explicación adicional.

EJEMPLOS:
Pregunta: ¿Cuánto cuesta estudiar ingeniería de sistemas? → costos+programas
Pregunta: ¿Qué materias tiene el primer semestre de electrónica industrial? → programas
Pregunta: ¿Cuándo son las inscripciones para el próximo semestre? → admisiones
Pregunta: ¿Tienen becas para estratos 1 y 2 en Mecatrónica? → becas+programas
Pregunta: ¿Cuánto cuesta el semestre de Tecnología en Mecatrónica y qué becas hay? → costos+programas+becas
Pregunta: ¿Qué valor tiene la matrícula y qué becas hay disponibles? → costos+becas
Pregunta: ¿Cuánto vale la entrada al gimnasio? → bienestar+costos
Pregunta: ¿Cuáles son los derechos pecuniarios? → costos
Pregunta: ¿Cuáles son los requisitos de admisión para una maestría? → admisiones+programas
Pregunta: ¿Qué servicios ofrece bienestar universitario? → bienestar

Pregunta: <PREGUNTA_ASPIRANTE>{query}</PREGUNTA_ASPIRANTE>"""


def classify_query(query: str) -> list[str]:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Estrategia de Fallback: Si uno falla, intenta con el siguiente
        modelos_fallback = [ROUTER_MODEL, "gemini-2.5-flash", "gemini-1.5-flash"]
        safe_query = sanitize_query(query)
        response = None

        for model_name in modelos_fallback:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=ROUTER_PROMPT.format(query=safe_query),
                )
                logger.debug(f"Router usó exitosamente: {model_name}")
                break # Éxito, salimos del bucle
            except Exception as e:
                logger.warning(f"Router falló con {model_name}: {e}")
                
        if not response:
            raise Exception("Todos los modelos de fallback fallaron en el router")

        raw = response.text.strip().lower()
        
        categorias = []
        for cat in VALID_CATEGORIES:
            if cat in raw:
                categorias.append(cat)
                
        if not categorias:
            logger.warning(f"Categoría(s) desconocida(s) en respuesta '{raw}', usando 'general'")
            return ["general"]
            
        logger.info(f"Categorías clasificadas: {categorias}")
        return categorias[:3]
    except Exception as exc:
        logger.error(f"Error crítico en router: {exc}")
        return ["general"]
