import logging
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import pdfplumber
import requests

logger = logging.getLogger(__name__)

PDF_DIR = Path(__file__).parent.parent / "data" / "pdfs"
PDF_DIR.mkdir(parents=True, exist_ok=True)

PDF_ALLOWLIST_RE = re.compile(r"instructivo", re.IGNORECASE)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def is_pdf_allowed(url: str) -> bool:
    path = urlparse(url).path
    return bool(PDF_ALLOWLIST_RE.search(path))


def _safe_filename(url: str) -> str:
    name = urlparse(url).path.rstrip("/").split("/")[-1]
    name = re.sub(r"[^\w\-.]", "_", name)
    return name or "documento.pdf"


def extract_pdf(pdf_url: str, categoria: str) -> dict | None:
    filename = _safe_filename(pdf_url)
    dest = PDF_DIR / filename

    try:
        logger.info(f"Descargando PDF: {pdf_url}")
        resp = requests.get(pdf_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
    except Exception as exc:
        logger.warning(f"No se pudo descargar {pdf_url}: {exc}")
        return None

    try:
        texto_paginas = []
        with pdfplumber.open(dest) as pdf:
            for page in pdf.pages:
                texto = page.extract_text()
                if texto:
                    texto_paginas.append(texto)

        if not texto_paginas:
            logger.warning(f"PDF sin texto extraíble (posible imagen escaneada): {pdf_url}")
            return None

        texto_completo = "\n".join(texto_paginas)
        texto_completo = re.sub(r"\n{3,}", "\n\n", texto_completo).strip()

        return {
            "url": pdf_url,
            "categoria": categoria,
            "texto": texto_completo,
            "timestamp": datetime.utcnow().isoformat(),
            "tipo": "pdf",
        }

    except Exception as exc:
        logger.warning(f"Error extrayendo texto de {pdf_url}: {exc}")
        return None
