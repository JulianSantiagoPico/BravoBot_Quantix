import logging
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright

from .pdf_extractor import extract_pdf, is_pdf_allowed
from .urls import PROGRAM_URL_PATTERNS

logger = logging.getLogger(__name__)

CALENDAR_PATTERN = re.compile(r"(\d{4})[^\d]*(1|2)", re.IGNORECASE)


def _is_same_domain(url: str, base: str) -> bool:
    return urlparse(url).netloc == urlparse(base).netloc


def _is_program_url(url: str, parent_url: str) -> bool:
    if url == parent_url or url.rstrip("/") == parent_url.rstrip("/"):
        return False
    return bool(PROGRAM_URL_PATTERNS.search(url))


async def _extract_text_from_page(page) -> str:
    return await page.evaluate(
        """() => {
            const noiseClasses = new Set([
                'site-header','site-footer','site-navigation','main-navigation',
                'top-bar','topbar','header-top','top-header',
                'breadcrumbs','breadcrumb',
                'social-share','social-links',
                'cookie-notice','cookie-banner','cookie-consent',
                'offcanvas','offcanvas-menu',
                'modal-overlay','modal-backdrop'
            ]);
            const toRemove = [];
            document.querySelectorAll('script,style,nav,footer,header,noscript,aside,form').forEach(el => toRemove.push(el));
            document.querySelectorAll('[class]').forEach(el => {
                const classes = Array.from(el.classList).map(c => c.toLowerCase());
                if (classes.some(c => noiseClasses.has(c))) toRemove.push(el);
            });
            toRemove.forEach(el => { try { el.remove(); } catch(e) {} });
            const main = document.querySelector('main') ||
                         document.querySelector('article') ||
                         document.body;
            return main ? main.innerText : document.body.innerText;
        }"""
    )


async def _extract_pdf_links_from_page(page, base_url: str) -> list[str]:
    hrefs = await page.evaluate(
        """() => {
            const results = [];
            document.querySelectorAll('a[href]').forEach(a => {
                if (a.href.toLowerCase().endsWith('.pdf')) results.push(a.href);
            });
            document.querySelectorAll('object[data]').forEach(o => {
                if (o.data.toLowerCase().endsWith('.pdf')) results.push(o.data);
            });
            document.querySelectorAll('embed[src]').forEach(e => {
                if (e.src.toLowerCase().endsWith('.pdf')) results.push(e.src);
            });
            document.querySelectorAll('iframe[src]').forEach(i => {
                if (i.src.toLowerCase().endsWith('.pdf')) results.push(i.src);
            });
            return results;
        }"""
    )
    normalized = [urljoin(base_url, h) for h in hrefs]
    filtered = [u for u in normalized if is_pdf_allowed(u)]
    return list(dict.fromkeys(filtered))


async def scrape_program(page, url: str, categoria: str) -> list[dict]:
    docs = []
    try:
        logger.info(f"[dynamic/program] Scrapeando: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        texto = await _extract_text_from_page(page)
        if texto.strip():
            docs.append(
                {
                    "url": url,
                    "categoria": categoria,
                    "texto": texto.strip(),
                    "timestamp": datetime.utcnow().isoformat(),
                    "tipo": "web",
                }
            )

        for pdf_url in await _extract_pdf_links_from_page(page, url):
            doc = extract_pdf(pdf_url, categoria)
            if doc:
                docs.append(doc)

    except Exception as exc:
        logger.error(f"[dynamic/program] Error en {url}: {exc}")

    return docs


async def _scrape_faculty_index(page, url: str, categoria: str, visited: set) -> list[dict]:
    docs = []
    try:
        logger.info(f"[dynamic/faculty] Indexando: {url}")
        await page.goto(url, wait_until="networkidle", timeout=30000)

        raw_links = await page.evaluate(
            """() => Array.from(document.querySelectorAll('a[href]'))
                         .map(a => a.href)"""
        )

        child_urls = []
        for link in raw_links:
            full = urljoin(url, link)
            if (
                _is_same_domain(full, url)
                and _is_program_url(full, url)
                and full not in visited
            ):
                child_urls.append(full)
                visited.add(full)

        child_urls = list(dict.fromkeys(child_urls))
        logger.info(f"[dynamic/faculty] {len(child_urls)} programas descubiertos en {url}")

        for child_url in child_urls:
            child_docs = await scrape_program(page, child_url, categoria)
            docs.extend(child_docs)

    except Exception as exc:
        logger.error(f"[dynamic/faculty] Error en {url}: {exc}")

    return docs


async def _scrape_calendar(page, url: str, categoria: str) -> list[dict]:
    docs = []
    try:
        logger.info(f"[dynamic/calendar] Descubriendo calendarios en: {url}")
        import requests as _requests
        from bs4 import BeautifulSoup as _BS
        from urllib.parse import urljoin as _urljoin

        resp = _requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        resp.raise_for_status()
        soup = _BS(resp.text, "html.parser")

        best = None
        best_tuple = (-1, -1)

        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            href = _urljoin(url, a["href"])
            if "calendario" not in href.lower() and "calendario" not in text.lower():
                continue
            m = CALENDAR_PATTERN.search(href) or CALENDAR_PATTERN.search(text)
            if m:
                t = (int(m.group(1)), int(m.group(2)))
                if t > best_tuple:
                    best_tuple = t
                    best = {"href": href, "label": f"Calendario {m.group(1)}-{m.group(2)}"}

        if not best:
            logger.warning(f"[dynamic/calendar] No se encontró ningún calendario en {url}")
            return docs

        logger.info(f"[dynamic/calendar] Semestre más reciente: {best['label']} → {best['href']}")

        if best["href"].lower().endswith(".pdf"):
            from .pdf_extractor import extract_pdf
            doc = extract_pdf(best["href"], categoria)
            if doc:
                docs.append(doc)
        else:
            await page.goto(best["href"], wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            texto = await _extract_text_from_page(page)
            if texto.strip():
                docs.append(
                    {
                        "url": best["href"],
                        "categoria": categoria,
                        "texto": texto.strip(),
                        "timestamp": datetime.utcnow().isoformat(),
                        "tipo": "web",
                        "titulo": best["label"],
                    }
                )

    except Exception as exc:
        logger.error(f"[dynamic/calendar] Error en {url}: {exc}")

    return docs


async def scrape_dynamic(
    url: str,
    categoria: str,
    follow_programs: bool = False,
    follow_calendar: bool = False,
    visited: set | None = None,
) -> list[dict]:
    if visited is None:
        visited = set()

    docs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        if follow_programs:
            docs = await _scrape_faculty_index(page, url, categoria, visited)
        elif follow_calendar:
            docs = await _scrape_calendar(page, url, categoria)
        else:
            docs = await scrape_program(page, url, categoria)

        await browser.close()

    return docs
