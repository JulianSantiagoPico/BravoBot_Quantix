import logging
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .pdf_extractor import extract_pdf, is_pdf_allowed

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

CONTENT_TAGS = ["main", "article", "section", "p", "li", "h1", "h2", "h3", "h4"]

PDF_SELECTORS = [
    ("a", "href"),
    ("iframe", "src"),
    ("embed", "src"),
    ("object", "data"),
]

NOISE_TAGS = ["script", "style", "nav", "footer", "header", "noscript", "aside", "form"]

NOISE_DIV_CLASSES = {
    "site-header", "site-footer", "site-navigation", "main-navigation",
    "top-bar", "topbar", "header-top", "top-header",
    "breadcrumbs", "breadcrumb",
    "social-share", "social-links",
    "cookie-notice", "cookie-banner", "cookie-consent",
    "offcanvas", "offcanvas-menu",
    "modal-overlay", "modal-backdrop",
}

def _remove_noise(soup: BeautifulSoup) -> None:
    for tag in soup(NOISE_TAGS):
        tag.decompose()
    to_remove = [
        el for el in soup.find_all(True)
        if set(c.lower() for c in (el.get("class") or [])) & NOISE_DIV_CLASSES
    ]
    for el in to_remove:
        try:
            el.decompose()
        except Exception:
            pass


def _extract_pdf_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    pdf_urls = []
    for tag, attr in PDF_SELECTORS:
        for el in soup.find_all(tag):
            val = el.get(attr, "") or ""
            if val.lower().endswith(".pdf"):
                full = urljoin(base_url, val)
                if is_pdf_allowed(full):
                    pdf_urls.append(full)
    return list(dict.fromkeys(pdf_urls))


def _extract_text(soup: BeautifulSoup) -> str:
    root = soup.find("main") or soup.find("article") or soup
    parts = []
    for tag in root.find_all(CONTENT_TAGS):
        text = tag.get_text(separator=" ", strip=True)
        if text:
            parts.append(text)
    return "\n".join(parts)


_PROGRAM_PAGE_RE = re.compile(
    r"(?:"
    r"/facultades/[^/]+/programas/[^/]{3,}"
    r"|/programas/(?:especializacion|maestria|doctorado|posgrado)[^/]*"
    r")",
    re.IGNORECASE,
)


def _discover_program_urls(soup: BeautifulSoup, base_url: str) -> list[str]:
    base_netloc = urlparse(base_url).netloc
    found = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        parsed = urlparse(href)
        if parsed.netloc != base_netloc:
            continue
        path = parsed.path.rstrip("/")
        if not _PROGRAM_PAGE_RE.search(path):
            continue
        href_clean = href.split("?")[0].split("#")[0]
        href_clean = re.sub(r"(?<!:)//+", "/", href_clean)
        if href_clean.rstrip("/") == base_url.rstrip("/"):
            continue
        found.append(href_clean)
    return list(dict.fromkeys(found))


def scrape_static(
    url: str, categoria: str, follow_programs: bool = False
) -> tuple[list[dict], list[str]]:
    docs: list[dict] = []
    discovered: list[str] = []
    try:
        logger.info(f"[static] Scrapeando: {url}")
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding

        soup = BeautifulSoup(resp.text, "html.parser")

        if follow_programs:
            discovered = _discover_program_urls(soup, url)
            logger.info(f"[static] {len(discovered)} URLs de programa descubiertas en {url}")

        _remove_noise(soup)

        if not follow_programs:
            texto = _extract_text(soup)
            if texto.strip():
                docs.append(
                    {
                        "url": url,
                        "categoria": categoria,
                        "texto": texto,
                        "timestamp": datetime.utcnow().isoformat(),
                        "tipo": "web",
                    }
                )

        for pdf_url in _extract_pdf_links(soup, url):
            doc = extract_pdf(pdf_url, categoria)
            if doc:
                docs.append(doc)

    except Exception as exc:
        logger.error(f"[static] Error en {url}: {exc}")

    return docs, discovered
