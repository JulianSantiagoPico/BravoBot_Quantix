import logging
import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from logger import get_logger, time_logged
from sentence_transformers import SentenceTransformer

load_dotenv()

logger = get_logger("bravobot.retriever")

_DEFAULT_CHROMA = str(Path(__file__).resolve().parent.parent / "chroma_db")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", _DEFAULT_CHROMA)
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "bravobot")
TOP_K = int(os.getenv("TOP_K", "5"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
MIN_SCORE = float(os.getenv("MIN_SCORE", "0.30"))

_RRF_K = 60

_model: SentenceTransformer | None = None
_collection: chromadb.Collection | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.debug(f"Cargando modelo de embeddings: {EMBEDDING_MODEL}")
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        _collection = chroma_client.get_collection(COLLECTION_NAME)
        logger.debug(f"ChromaDB cargado: colección '{COLLECTION_NAME}'")
    return _collection


def _rrf_fuse(ranked_lists: list[list[tuple[str, dict]]], top_k: int) -> list[dict]:
    """
    Reciprocal Rank Fusion sobre múltiples listas rankeadas.
    Cada lista es [(doc_id, chunk_dict), ...] ya ordenada de mejor a peor.
    Retorna los top_k chunks fusionados y ordenados por score RRF.
    """
    scores: dict[str, float] = {}
    chunks_by_id: dict[str, dict] = {}

    for ranked in ranked_lists:
        for rank, (doc_id, chunk) in enumerate(ranked):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (rank + _RRF_K)
            if doc_id not in chunks_by_id:
                chunks_by_id[doc_id] = chunk

    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)

    result = []
    for doc_id in sorted_ids[:top_k]:
        chunk = chunks_by_id[doc_id].copy()
        chunk["score"] = round(scores[doc_id], 6)
        result.append(chunk)
    return result


def _query_collection(
    query_embedding: list[float],
    where_filter: dict | None,
    n_results: int,
) -> list[tuple[str, dict]]:
    """Ejecuta una query en ChromaDB y retorna lista de (doc_id, chunk_dict)."""
    collection = get_collection()
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        logger.error(f"Error en query ChromaDB: {exc}")
        return []

    ranked = []
    docs = (results.get("documents") or [[]])[0]
    metas = (results.get("metadatas") or [[]])[0]
    dists = (results.get("distances") or [[]])[0]
    ids = (results.get("ids") or [[]])[0]

    for doc_id, doc, meta, dist in zip(ids, docs, metas, dists):
        safe_meta = meta or {}
        ranked.append(
            (
                doc_id,
                {
                    "texto": doc,
                    "url": safe_meta.get("url", ""),
                    "categoria": safe_meta.get("categoria", ""),
                    "source_type": safe_meta.get("source_type", ""),
                    "program_slug": safe_meta.get("program_slug", ""),
                    "score": round(1 - dist, 4),
                },
            )
        )
    return ranked


def retrieve(query: str, categorias: list[str], top_k: int = TOP_K) -> list[dict]:
    model = _get_model()

    # Inyección rápida de sinónimos para alinear nombres comunes con programas reales.
    search_query = query
    q_lower = query.lower()
    if "sistemas" in q_lower and "software" not in q_lower:
        search_query += " ingeniería de software desarrollo de software"
        logger.debug("[RETRIEVER] Sinónimos inyectados para 'sistemas'")

    # 1. Embedding de una sola query de búsqueda.
    try:
        with time_logged("embedding", logger, level=logging.DEBUG):
            embeddings = [model.encode(search_query, show_progress_bar=False).tolist()]
    except Exception as exc:
        logger.error("[RETRIEVER] Error generando embeddings: %s", exc)
        return []

    # 2. Construir filtros de categoría
    non_general = [c for c in categorias if c != "general"]
    if len(non_general) == 0:
        filters: list[dict | None] = [None]
    elif len(non_general) == 1:
        filters = [{"categoria": {"$eq": non_general[0]}}]
    else:
        filters = [{"categoria": {"$eq": c}} for c in non_general]

    logger.debug(
        "[RETRIEVER] Query con filtros=%s candidates_per_query=%d",
        [
            f.get("categoria", {}).get("$eq", "sin_filtro") if f else "ninguno"
            for f in filters
        ],
        top_k * 3,
    )

    # 3. Retrieval ampliado: búsqueda dual (con filtro + sin filtro)
    n_candidates = top_k * 3
    all_ranked_lists: list[list[tuple[str, dict]]] = []

    with time_logged("chromadb_queries", logger, level=logging.INFO):
        # 3a. Búsqueda CON filtro de categoría
        for emb in embeddings:
            for filt in filters:
                ranked = _query_collection(emb, filt, n_candidates)
                if ranked:
                    all_ranked_lists.append(ranked)

        # 3b. Búsqueda SIN filtro (para capturar PDFs relevantes sin restricción de categoría)
        for emb in embeddings:
            ranked = _query_collection(emb, None, n_candidates)
            if ranked:
                all_ranked_lists.append(ranked)

    if not all_ranked_lists:
        logger.warning("[RETRIEVER] No se obtuvieron resultados de ChromaDB")
        return []

    logger.debug(
        "[RETRIEVER] %d listas rankeadas obtenidas (antes de RRF)",
        len(all_ranked_lists),
    )

    # 4. RRF fusion
    with time_logged("rrf_fusion", logger, level=logging.DEBUG):
        fused = _rrf_fuse(all_ranked_lists, top_k=top_k * 2)

    # 5. Umbral mínimo de score (basado en score coseno original, no RRF)
    cosine_scores: dict[str, float] = {}
    for ranked in all_ranked_lists:
        for doc_id, chunk in ranked:
            if doc_id not in cosine_scores or chunk["score"] > cosine_scores[doc_id]:
                cosine_scores[doc_id] = chunk["score"]

    filtered = []
    for chunk in fused:
        doc_id = next(
            (
                did
                for ranked in all_ranked_lists
                for did, c in ranked
                if c is chunk or c["texto"] == chunk["texto"]
            ),
            None,
        )
        best_cosine = cosine_scores.get(doc_id, 0.0) if doc_id else 0.0
        if best_cosine >= MIN_SCORE:
            filtered.append(chunk)
        if len(filtered) == top_k:
            break

    logger.info(
        "[RETRIEVER] %d/%d chunks tras filtrado (umbral=%.2f, listas_entrada=%d)",
        len(filtered),
        top_k,
        MIN_SCORE,
        len(all_ranked_lists),
    )
    return filtered
