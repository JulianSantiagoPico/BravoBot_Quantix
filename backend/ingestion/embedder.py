import logging
import os
import re
import uuid
from pathlib import Path
from urllib.parse import urlparse

import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from .cleaner import clean_text
from .chunker import chunk_text

load_dotenv()

logger = logging.getLogger(__name__)

_DEFAULT_CHROMA = str(Path(__file__).resolve().parent.parent / "chroma_db")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", _DEFAULT_CHROMA)
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "bravobot")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")

_model: SentenceTransformer | None = None

_POSGRADO_RE = re.compile(
    r"/programas/(?:especializacion|maestria|doctorado|posgrado)",
    re.IGNORECASE,
)


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info(f"Cargando modelo de embeddings: {EMBEDDING_MODEL}")
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def _get_collection(reset: bool = False) -> chromadb.Collection:
    chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    if reset:
        try:
            chroma_client.delete_collection(COLLECTION_NAME)
            logger.info(f"Colección '{COLLECTION_NAME}' eliminada.")
        except Exception:
            pass
    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def _extract_titulo(texto_limpio: str) -> str:
    for line in texto_limpio.split("\n"):
        stripped = line.strip()
        if len(stripped) > 10:
            return stripped[:120]
    return ""


def _extract_program_name(url: str, texto_limpio: str) -> str:
    path = urlparse(url).path.rstrip("/")
    slug = path.split("/")[-1]
    if not slug:
        return ""
    name = slug.replace("-", " ").replace("_", " ").title()
    return name


def _extract_level(url: str, categoria: str) -> str:
    if categoria != "programas":
        return ""
    if _POSGRADO_RE.search(url):
        return "posgrado"
    return "pregrado"


def _extract_source_type(categoria: str, tipo: str) -> str:
    if tipo == "pdf":
        return "pdf"
    if categoria == "programas":
        return "web_program"
    return "web_general"


def _extract_program_slug(url: str, categoria: str) -> str:
    if categoria != "programas":
        return ""
    path = urlparse(url).path.rstrip("/")
    slug = path.split("/")[-1]
    return slug.replace("-", " ").replace("_", " ").lower()


def build_index(raw_pages: list[dict], reset: bool = False) -> None:
    if not raw_pages:
        logger.warning("No hay documentos para indexar.")
        return

    model = _get_model()
    collection = _get_collection(reset=reset)

    total_chunks = 0

    for doc in raw_pages:
        url = doc.get("url", "")
        categoria = doc.get("categoria", "general")
        texto_raw = doc.get("texto", "")
        tipo = doc.get("tipo", "web")

        if not texto_raw.strip():
            continue

        texto_limpio = clean_text(texto_raw)
        chunks = chunk_text(texto_limpio, tipo=tipo)

        if not chunks:
            continue

        titulo = _extract_titulo(texto_limpio)
        program_name = _extract_program_name(url, texto_limpio) if categoria == "programas" else ""
        level = _extract_level(url, categoria)
        source_type = _extract_source_type(categoria, tipo)
        program_slug = _extract_program_slug(url, categoria)

        logger.info(f"Indexando {len(chunks)} chunks de: {url}")

        try:
            embeddings = model.encode(chunks, show_progress_bar=False, batch_size=32).tolist()
        except Exception as exc:
            logger.error(f"Error generando embeddings para {url}: {exc}")
            continue

        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [
            {
                "url": url,
                "categoria": categoria,
                "tipo": tipo,
                "chunk_index": i,
                "titulo": titulo,
                "program_name": program_name,
                "level": level,
                "source_type": source_type,
                "program_slug": program_slug,
            }
            for i in range(len(chunks))
        ]

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )
        total_chunks += len(chunks)

    logger.info(f"\nIndexación completa. Total chunks en ChromaDB: {total_chunks}")
