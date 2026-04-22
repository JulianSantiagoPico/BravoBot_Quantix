import logging

from .generator import generate_response
from .malla_lookup import lookup_course, lookup_malla
from .retriever import retrieve
from .router import classify_query

logger = logging.getLogger(__name__)

_MALLA_KEYWORDS = {
    "malla", "materia", "materias", "asignatura", "asignaturas",
    "semestre", "semestres", "pensum", "credito", "creditos",
    "crédito", "créditos", "curso", "cursos",
}


def _needs_malla(query: str, categorias: list[str]) -> bool:
    if "programas" not in categorias:
        return False
    query_words = set(query.lower().split())
    return bool(query_words & _MALLA_KEYWORDS)


def _build_malla_context(query: str) -> dict | None:
    malla = lookup_malla(query)
    if malla:
        logger.info(f"malla_lookup: programa encontrado → {malla['name']}")
        return malla

    courses = lookup_course(query)
    if courses:
        logger.info(f"malla_lookup: {len(courses)} materia(s) encontrada(s)")
        return {"courses": courses}

    logger.debug("malla_lookup: sin resultado para la query")
    return None


def ask(query: str) -> dict:
    logger.info(f"Query recibida: {query!r}")

    categorias = classify_query(query)
    logger.info(f"Categorías clasificadas: {categorias}")

    chunks = retrieve(query, categorias)
    logger.info(f"Chunks recuperados: {len(chunks)}")

    malla_context = None
    if _needs_malla(query, categorias):
        logger.info("Activando malla_lookup para query de malla/materias")
        malla_context = _build_malla_context(query)

    result = generate_response(query, chunks, malla_context=malla_context)

    return {
        "respuesta": result["respuesta"],
        "fuentes": result["fuentes"],
        "categoria": categorias[0],
        "categorias": categorias,
    }
