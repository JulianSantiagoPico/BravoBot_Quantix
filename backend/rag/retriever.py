import logging
import os

import chromadb
from dotenv import load_dotenv
from google import genai
from sentence_transformers import SentenceTransformer

load_dotenv()

logger = logging.getLogger(__name__)

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "bravobot")
TOP_K = int(os.getenv("TOP_K", "5"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
MIN_SCORE = float(os.getenv("MIN_SCORE", "0.30"))
EXPAND_QUERIES = os.getenv("EXPAND_QUERIES", "true").lower() == "true"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ROUTER_MODEL = "gemini-2.5-flash"

_RRF_K = 60

_model: SentenceTransformer | None = None
_collection: chromadb.Collection | None = None

_EXPAND_PROMPT = """Dado el siguiente texto de consulta, genera exactamente 2 reformulaciones alternativas en español \
que busquen la misma información pero con vocabulario diferente.
Responde SOLO con las 2 reformulaciones, una por línea, sin numeración ni explicación.

Consulta original: {query}"""


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info(f"Cargando modelo de embeddings: {EMBEDDING_MODEL}")
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        _collection = chroma_client.get_collection(COLLECTION_NAME)
        logger.info(f"ChromaDB cargado: colección '{COLLECTION_NAME}'")
    return _collection


def expand_query(query: str) -> list[str]:
    """Genera 2 reformulaciones de la query usando Gemini. Retorna [original, var1, var2]."""
    queries = [query]
    if not EXPAND_QUERIES or not GEMINI_API_KEY:
        return queries
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=ROUTER_MODEL,
            contents=_EXPAND_PROMPT.format(query=query),
        )
        lines = [line.strip() for line in response.text.strip().splitlines() if line.strip()]
        queries.extend(lines[:2])
        logger.info(f"Multi-query expansion: {len(queries)} variantes generadas")
    except Exception as exc:
        logger.warning(f"expand_query falló, usando solo query original: {exc}")
    return queries


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
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]
    ids = results.get("ids", [[]])[0]

    for doc_id, doc, meta, dist in zip(ids, docs, metas, dists):
        ranked.append((
            doc_id,
            {
                "texto": doc,
                "url": meta.get("url", ""),
                "categoria": meta.get("categoria", ""),
                "source_type": meta.get("source_type", ""),
                "program_slug": meta.get("program_slug", ""),
                "score": round(1 - dist, 4),
            },
        ))
    return ranked


def retrieve(query: str, categorias: list[str], top_k: int = TOP_K) -> list[dict]:
    model = _get_model()

    # 1. Multi-query expansion
    queries = expand_query(query)

    # 2. Embeddings para todas las variantes
    try:
        embeddings = model.encode(queries, show_progress_bar=False).tolist()
    except Exception as exc:
        logger.error(f"Error generando embeddings: {exc}")
        return []

    # 3. Construir filtros de categoría
    non_general = [c for c in categorias if c != "general"]
    if len(non_general) == 0:
        filters: list[dict | None] = [None]
    elif len(non_general) == 1:
        filters = [{"categoria": {"$eq": non_general[0]}}]
    else:
        filters = [{"categoria": {"$eq": c}} for c in non_general]

    # 4. Retrieval ampliado: top_k * 3 por cada (query, filtro)
    n_candidates = top_k * 3
    all_ranked_lists: list[list[tuple[str, dict]]] = []

    for emb in embeddings:
        for filt in filters:
            ranked = _query_collection(emb, filt, n_candidates)
            if ranked:
                all_ranked_lists.append(ranked)

    if not all_ranked_lists:
        logger.warning("No se obtuvieron resultados de ChromaDB")
        return []

    # 5. RRF fusion
    fused = _rrf_fuse(all_ranked_lists, top_k=top_k * 2)

    # 6. Umbral mínimo de score (basado en score coseno original, no RRF)
    # Recalcular score coseno real desde la primera lista para el filtrado
    cosine_scores: dict[str, float] = {}
    for ranked in all_ranked_lists:
        for doc_id, chunk in ranked:
            if doc_id not in cosine_scores or chunk["score"] > cosine_scores[doc_id]:
                cosine_scores[doc_id] = chunk["score"]

    filtered = []
    for chunk in fused:
        doc_id = next(
            (did for ranked in all_ranked_lists for did, c in ranked if c is chunk or c["texto"] == chunk["texto"]),
            None,
        )
        best_cosine = cosine_scores.get(doc_id, 0.0) if doc_id else 0.0
        if best_cosine >= MIN_SCORE:
            filtered.append(chunk)
        if len(filtered) == top_k:
            break

    logger.info(
        f"retrieve: {len(queries)} queries × {len(filters)} filtro(s) → "
        f"{sum(len(r) for r in all_ranked_lists)} candidatos → "
        f"{len(fused)} tras RRF → {len(filtered)} tras umbral {MIN_SCORE}"
    )
    return filtered
