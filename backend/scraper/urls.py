import re

PROGRAM_URL_PATTERNS = re.compile(
    r"pascualbravo\.edu\.co/"
    r"(programas|especializacion|maestria|tecnologia|ingenieria|"
    r"facultad[^/]*/[^/]+(?!/programas$))",
    re.IGNORECASE,
)

URLS = [
    # ── ALTA PRIORIDAD ── Admisiones y Oferta Académica ──────────────────────
    {
        "url": "https://pascualbravo.edu.co/aspirantes/",
        "categoria": "admisiones",
        "scraper": "static",
        "follow_programs": False,
        "follow_calendar": False,
    },
    {
        "url": "https://pascualbravo.edu.co/pregrados/",
        "categoria": "programas",
        "scraper": "static",
        "follow_programs": True,
        "follow_calendar": False,
    },
    {
        "url": "https://pascualbravo.edu.co/posgrados/",
        "categoria": "programas",
        "scraper": "static",
        "follow_programs": True,
        "follow_calendar": False,
    },
    {
        "url": "https://pascualbravo.edu.co/academico/vicerrectoria-de-docencia/micro-y-macrocredenciales/",
        "categoria": "programas",
        "scraper": "static",
        "follow_programs": False,
        "follow_calendar": False,
    },
    {
        "url": "https://sicau.pascualbravo.edu.co/SICAU/Aspirante/General/InstruccionesDeInicioDeInscripcion",
        "categoria": "admisiones",
        "scraper": "static",
        "follow_programs": False,
        "follow_calendar": False,
    },
    # ── ALTA PRIORIDAD ── Costos y Calendario ────────────────────────────────
    {
        "url": "https://pascualbravo.edu.co/ayuda/derechos-pecunarios/",
        "categoria": "costos",
        "scraper": "static",
        "follow_programs": False,
        "follow_calendar": False,
    },
    {
        "url": "https://pascualbravo.edu.co/academico/calendario-academico/",
        "categoria": "admisiones",
        "scraper": "dynamic",
        "follow_programs": False,
        "follow_calendar": True,
    },
    # ── MEDIA PRIORIDAD ── Becas, Bienestar y Servicios ──────────────────────
    {
        "url": "https://sites.google.com/pascualbravo.edu.co/bienestariupascual/inicio/socioecon%C3%B3mica?authuser=0",
        "categoria": "becas",
        "scraper": "static",
        "follow_programs": False,
        "follow_calendar": False,
    },
    {
        "url": "https://pascualbravo.edu.co/academico/bienestar-universitario/servicios/",
        "categoria": "bienestar",
        "scraper": "static",
        "follow_programs": False,
        "follow_calendar": False,
    },
    {
        "url": "https://pascualbravo.edu.co/academico/vicerrectoria-de-docencia/practicas-profesionales/",
        "categoria": "bienestar",
        "scraper": "static",
        "follow_programs": False,
        "follow_calendar": False,
    },
    {
        "url": "https://pascualbravo.edu.co/academico/vicerrectoria-de-docencia/programa-de-ingles/",
        "categoria": "bienestar",
        "scraper": "static",
        "follow_programs": False,
        "follow_calendar": False,
    },
    # ── MEDIA PRIORIDAD ── Ayuda y Referencia ────────────────────────────────
    {
        "url": "https://pascualbravo.edu.co/ayuda/preguntas-frecuentes/",
        "categoria": "admisiones",
        "scraper": "static",
        "follow_programs": False,
        "follow_calendar": False,
    },
    {
        "url": "https://pascualbravo.edu.co/extension/educacion-continua/programa-sillas-vacias/",
        "categoria": "becas",
        "scraper": "static",
        "follow_programs": False,
        "follow_calendar": False,
    },
    {
        "url": "https://pascualbravo.edu.co/ayuda/directorio/",
        "categoria": "institucional",
        "scraper": "static",
        "follow_programs": False,
        "follow_calendar": False,
    },
    # ── BAJA PRIORIDAD ── Contexto Institucional ─────────────────────────────
    {
        "url": "https://pascualbravo.edu.co/acerca-del-pascual/identidad-institucional/",
        "categoria": "institucional",
        "scraper": "static",
        "follow_programs": False,
        "follow_calendar": False,
    },
    {
        "url": "https://pascualbravo.edu.co/acerca-del-pascual/historia/",
        "categoria": "institucional",
        "scraper": "static",
        "follow_programs": False,
        "follow_calendar": False,
    },
    {
        "url": "https://pascualbravo.edu.co/acreditacioninstitucional/",
        "categoria": "institucional",
        "scraper": "static",
        "follow_programs": False,
        "follow_calendar": False,
    },
]
