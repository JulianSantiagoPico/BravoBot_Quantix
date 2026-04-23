"""
Pipeline de ingesta: scraping → limpieza → chunking → embeddings → ChromaDB.

Uso:
    python run_ingestion.py           # corre todo (acumulativo)
    python run_ingestion.py --reset   # borra ChromaDB y regenera desde cero
    python run_ingestion.py --scrape-only   # solo scraping, sin indexar
    python run_ingestion.py --index-only    # indexar raw_pages.json existente
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_ingestion")

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "backend" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
RAW_PAGES_PATH = DATA_DIR / "raw_pages.json"

load_dotenv(BASE_DIR / "backend" / ".env")

sys.path.insert(0, str(BASE_DIR / "backend"))

from scraper.urls import URLS  # noqa: E402
from scraper.static_scraper import scrape_static  # noqa: E402
from scraper.dynamic_scraper import scrape_dynamic  # noqa: E402


async def run_scraping() -> list[dict]:
    all_docs: list[dict] = []
    visited: set[str] = set()

    for entry in URLS:
        url = entry["url"]
        categoria = entry["categoria"]
        scraper_type = entry["scraper"]
        follow_programs = entry.get("follow_programs", False)
        follow_calendar = entry.get("follow_calendar", False)

        if url in visited:
            logger.info(f"Omitiendo URL ya visitada: {url}")
            continue
        visited.add(url)

        if scraper_type == "static":
            docs, discovered = scrape_static(url, categoria, follow_programs=follow_programs)
            logger.info(f"  → {len(docs)} documento(s) obtenidos de {url}")
            for doc in docs:
                visited.add(doc["url"])
            all_docs.extend(docs)

            for prog_url in discovered:
                if prog_url in visited:
                    continue
                visited.add(prog_url)
                logger.info(f"  [programa] Scrapeando con Playwright: {prog_url}")
                prog_docs = await scrape_dynamic(
                    url=prog_url,
                    categoria=categoria,
                )
                logger.info(f"    → {len(prog_docs)} documento(s) de {prog_url}")
                for doc in prog_docs:
                    visited.add(doc["url"])
                all_docs.extend(prog_docs)
        else:
            docs = await scrape_dynamic(
                url=url,
                categoria=categoria,
                follow_programs=follow_programs,
                follow_calendar=follow_calendar,
                visited=visited,
            )
            logger.info(f"  → {len(docs)} documento(s) obtenidos de {url}")
            for doc in docs:
                visited.add(doc["url"])
            all_docs.extend(docs)

    # Deduplicar por URL preservando el primer documento encontrado
    seen: set[str] = set()
    unique_docs = []
    for doc in all_docs:
        doc_url = doc.get("url", "")
        if doc_url not in seen:
            seen.add(doc_url)
            unique_docs.append(doc)

    if len(unique_docs) < len(all_docs):
        logger.info(f"Deduplicación: {len(all_docs)} → {len(unique_docs)} documentos únicos")

    logger.info(f"\nTotal documentos scrapeados: {len(unique_docs)}")
    return unique_docs


def save_raw(docs: list[dict]) -> None:
    RAW_PAGES_PATH.write_text(
        json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(f"raw_pages.json guardado: {RAW_PAGES_PATH}")


def load_raw() -> list[dict]:
    if not RAW_PAGES_PATH.exists():
        logger.error(f"No se encontró {RAW_PAGES_PATH}. Ejecuta primero sin --index-only.")
        sys.exit(1)
    return json.loads(RAW_PAGES_PATH.read_text(encoding="utf-8"))


def run_indexing(docs: list[dict], reset: bool) -> None:
    from ingestion.embedder import build_index
    build_index(docs, reset=reset)


async def main() -> None:
    parser = argparse.ArgumentParser(description="BravoBot ingestion pipeline")
    parser.add_argument("--reset", action="store_true", help="Borrar ChromaDB antes de indexar")
    parser.add_argument("--scrape-only", action="store_true", help="Solo scraping, sin indexar")
    parser.add_argument("--index-only", action="store_true", help="Solo indexar raw_pages.json existente")
    args = parser.parse_args()

    if args.scrape_only and args.index_only:
        logger.error("No puedes usar --scrape-only y --index-only al mismo tiempo.")
        sys.exit(1)

    if args.index_only:
        docs = load_raw()
        logger.info(f"Cargados {len(docs)} documentos desde {RAW_PAGES_PATH}")
        run_indexing(docs, reset=args.reset)
        return

    docs = await run_scraping()
    save_raw(docs)

    if not args.scrape_only:
        run_indexing(docs, reset=args.reset)


if __name__ == "__main__":
    asyncio.run(main())
