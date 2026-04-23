import re
import unicodedata

_URL_RE = re.compile(r"^https?://\S+$")

_BREADCRUMB_RE = re.compile(r"^(\s*\|\s*[\w\s\-áéíóúüñÁÉÍÓÚÜÑ()]+){2,}\s*$")

_BOILERPLATE_EXACT = {
    "tradición - transformación - innovación",
    "tradicion - transformacion - innovacion",
    "inscríbete",
    "inscribete",
    "ver programas",
    "ver más",
    "ver mas",
    "malla curricular",
    "saltar al contenido",
    "soy:",
    "acceso sicau",
    "facebook",
    "instagram",
    "linkedin",
    "youtube",
    "si necesitas información adicional del programa académico, escríbenos.",
    "si necesitas informacion adicional del programa academico, escribenos.",
    "conoce el programa",
    "conoce la universidad",
    "¡comienza ahora!",
    "comienza ahora!",
    "solicita información",
    "solicita informacion",
    "reproducir vídeo",
    "reproducir video",
    "ver más noticias",
    "ver mas noticias",
    "obten tu titulo de posgrado en una universidad prestigiosa, reconocida y acreditada en alta calidad",
}

_BOILERPLATE_STARTSWITH = (
    "soy: aspirante",
    "del 1 de septiembre al",
    "del 2 de marzo al",
    "estarán abiertas las inscripciones",
    "estaran abiertas las inscripciones",
    "hasta",
)

_NEWS_TAGS_RE = re.compile(
    r"aspirantes.*docentes.*empleados.*egresados.*estudiantes.*mujeres.*novedades",
    re.IGNORECASE,
)


def _is_boilerplate_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    lower = stripped.lower()
    if lower in _BOILERPLATE_EXACT:
        return True
    if any(lower.startswith(p) for p in _BOILERPLATE_STARTSWITH):
        return True
    if _URL_RE.match(stripped):
        return True
    if _BREADCRUMB_RE.match(stripped):
        return True
    if _NEWS_TAGS_RE.search(lower):
        return True
    return False


def _remove_boilerplate(texto: str) -> str:
    lines = texto.split("\n")
    return "\n".join(line for line in lines if not _is_boilerplate_line(line))


def _deduplicate_lines(texto: str) -> str:
    seen_short: set[str] = set()
    result = []
    for line in texto.split("\n"):
        stripped = line.strip()
        if not stripped:
            result.append(line)
            continue
        if len(stripped) <= 120 and stripped in seen_short:
            continue
        if len(stripped) <= 120:
            seen_short.add(stripped)
        result.append(line)
    return "\n".join(result)


def clean_text(texto: str) -> str:
    texto = unicodedata.normalize("NFC", texto)

    texto = re.sub(r"\t+", " ", texto)

    texto = re.sub(r"[ ]{2,}", " ", texto)

    texto = _remove_boilerplate(texto)

    texto = re.sub(r"\n{3,}", "\n\n", texto)

    texto = re.sub(r"[^\w\s.,;:¿?¡!()\-/\n\"\'%@#áéíóúüñÁÉÍÓÚÜÑ]", " ", texto)

    texto = re.sub(r" {2,}", " ", texto)

    texto = _deduplicate_lines(texto)

    return texto.strip()
