import difflib
import json
import logging
import unicodedata
from pathlib import Path

from logger import get_logger

logger = get_logger("bravobot.malla")

_DATA_PATH = Path(__file__).parent.parent / "data" / "mallas_curriculares.json"

_programs: list[dict] = []
_normalized_names: list[str] = []


def _normalize(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text


def _load() -> None:
    global _programs, _normalized_names
    if _programs:
        return
    try:
        data = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
        _programs = data.get("programs", [])
        _normalized_names = [_normalize(p["name"]) for p in _programs]
        logger.debug(f"[malla_lookup] {len(_programs)} programas cargados.")
    except Exception as exc:
        logger.error(f"[malla_lookup] Error cargando mallas: {exc}")


def lookup_malla(query: str, cutoff: float = 0.4) -> dict | None:
    """
    Busca el programa más cercano al query y retorna su información de malla.

    Returns dict con keys: name, level, duration, url_pdf, semesters
    o None si no se encuentra match suficientemente bueno.
    """
    _load()
    if not _programs:
        return None

    normalized_query = _normalize(query)

    matches = difflib.get_close_matches(
        normalized_query, _normalized_names, n=1, cutoff=cutoff
    )

    if not matches:
        logger.debug(f"[malla_lookup] Sin match para: {query!r}")
        return None

    idx = _normalized_names.index(matches[0])
    prog = _programs[idx]

    return {
        "name": prog.get("name", ""),
        "level": prog.get("level", ""),
        "duration": prog.get("duration", ""),
        "url_pdf": prog.get("url_pdf", ""),
        "semesters": prog.get("semesters", []),
    }


def lookup_course(course_query: str, cutoff: float = 0.5) -> list[dict]:
    """
    Busca una materia por nombre en todos los programas.

    Returns lista de dicts con: program_name, level, semester, course_name, credits
    """
    _load()
    normalized_query = _normalize(course_query)
    results = []

    for prog in _programs:
        for sem in prog.get("semesters", []):
            for course in sem.get("courses", []):
                normalized_course = _normalize(course.get("name", ""))
                matches = difflib.get_close_matches(
                    normalized_query, [normalized_course], n=1, cutoff=cutoff
                )
                if matches:
                    results.append(
                        {
                            "program_name": prog.get("name", ""),
                            "level": prog.get("level", ""),
                            "semester": sem.get("semester"),
                            "course_name": course.get("name", ""),
                            "credits": course.get("credits"),
                            "url_pdf": prog.get("url_pdf", ""),
                        }
                    )

    return results
