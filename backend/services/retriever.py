from __future__ import annotations

import os
import time
import hashlib
import numpy as np
from langchain_core.documents import Document
from langchain_classic.retrievers.multi_query import MultiQueryRetriever
from backend.logging_config import get_logger
from .llm import get_llm
from . import vectorstore

logger = get_logger("backend.retriever")

# ---------------------------------------------------------------------------
# BM25 keyword retrieval
# ---------------------------------------------------------------------------

_bm25_index = None
_bm25_docs: list[dict] = []
_bm25_count = 0  # tracks collection count when BM25 was last built
_reranker = None


def _build_bm25_index():
    """Build BM25 index from all documents in ChromaDB."""
    global _bm25_index, _bm25_docs, _bm25_count

    collection = vectorstore.get_collection()
    count = collection.count()
    if count == 0:
        logger.warning("BM25 index build skipped — collection is empty")
        _bm25_index = None
        _bm25_docs = []
        _bm25_count = 0
        return

    # Skip rebuild if count hasn't changed
    if _bm25_index is not None and count == _bm25_count:
        return

    logger.info("Building BM25 index from %d chunks...", count)
    build_start = time.time()

    batch_size = 500
    all_docs = []
    all_metas = []
    all_ids = []
    offset = 0
    while offset < count:
        result = collection.get(
            limit=batch_size,
            offset=offset,
            include=["documents", "metadatas"],
        )
        all_docs.extend(result["documents"])
        all_metas.extend(result["metadatas"])
        all_ids.extend(result["ids"])
        offset += batch_size

    _bm25_docs = [
        {"id": doc_id, "content": doc, "metadata": meta}
        for doc_id, doc, meta in zip(all_ids, all_docs, all_metas)
    ]

    try:
        from rank_bm25 import BM25Okapi
        import nltk
        for pkg in ["punkt_tab", "punkt"]:
            try:
                nltk.data.find(f"tokenizers/{pkg}")
            except LookupError:
                nltk.download(pkg, quiet=True)

        tokenized = [nltk.word_tokenize(doc.lower()) for doc in all_docs]
        _bm25_index = BM25Okapi(tokenized)
        _bm25_count = count
        elapsed = time.time() - build_start
        logger.info("BM25 index built — docs=%d, elapsed=%.2fs", len(all_docs), elapsed)
    except ImportError:
        logger.error("rank_bm25 not installed — BM25 search disabled")
        _bm25_index = None


def _bm25_search(query: str, k: int = 10) -> list[dict]:
    """Keyword search using BM25."""
    global _bm25_index, _bm25_docs

    # Always check if index needs rebuild (handles deletions)
    collection = vectorstore.get_collection()
    if _bm25_index is None or collection.count() != _bm25_count:
        _build_bm25_index()
    if _bm25_index is None or not _bm25_docs:
        logger.debug("BM25 search skipped — index not available")
        return []

    import nltk
    for pkg in ["punkt_tab", "punkt"]:
        try:
            nltk.data.find(f"tokenizers/{pkg}")
        except LookupError:
            nltk.download(pkg, quiet=True)

    tokenized_query = nltk.word_tokenize(query.lower())
    scores = _bm25_index.get_scores(tokenized_query)

    top_indices = np.argsort(scores)[::-1][:k]
    results = []
    for idx in top_indices:
        if scores[idx] > 0:
            results.append({
                "id": _bm25_docs[idx]["id"],
                "content": _bm25_docs[idx]["content"],
                "metadata": _bm25_docs[idx]["metadata"],
                "score": float(scores[idx]),
            })

    logger.debug("BM25 search — query=%s, hits=%d, top_score=%.4f", query[:50], len(results), results[0]["score"] if results else 0)
    return results


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion (RRF)
# ---------------------------------------------------------------------------

def _rrf_fusion(
    vector_results: list[dict],
    bm25_results: list[dict],
    k: int = 60,
    top_n: int = 10,
) -> list[dict]:
    """Merge two ranked lists using Reciprocal Rank Fusion."""
    rrf_scores: dict[str, float] = {}
    doc_map: dict[str, dict] = {}

    for rank, doc in enumerate(vector_results, start=1):
        doc_id = doc["id"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (k + rank)
        doc_map[doc_id] = doc

    for rank, doc in enumerate(bm25_results, start=1):
        doc_id = doc["id"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (k + rank)
        if doc_id not in doc_map:
            doc_map[doc_id] = doc

    sorted_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:top_n]

    logger.debug(
        "RRF fusion — vector=%d, bm25=%d, merged=%d, top_rrf=%.4f",
        len(vector_results), len(bm25_results), len(sorted_ids),
        rrf_scores[sorted_ids[0]] if sorted_ids else 0,
    )

    return [{"id": doc_id, "rrf_score": rrf_scores[doc_id], **doc_map[doc_id]} for doc_id in sorted_ids]


# ---------------------------------------------------------------------------
# Multi-query retrieval (Tejasva's approach with real LLM)
# ---------------------------------------------------------------------------

def _get_multi_query_retriever():
    """Build a MultiQueryRetriever using our configured LLM and ChromaDB."""
    collection = vectorstore.get_collection()
    count = collection.count()
    if count == 0:
        return None

    from .embeddings import get_embeddings
    embeddings = get_embeddings()

    from langchain_chroma import Chroma

    vectorstore_lc = Chroma(
        client=vectorstore.get_client(),
        collection_name=collection.name,
        embedding_function=embeddings,
    )

    base_retriever = vectorstore_lc.as_retriever(search_kwargs={"k": 5})
    llm = get_llm()

    mq_retriever = MultiQueryRetriever.from_llm(
        retriever=base_retriever,
        llm=llm,
    )
    logger.debug("MultiQueryRetriever built")
    return mq_retriever


def _multi_query_retrieve(query: str, n_results: int = 10) -> list[dict]:
    """Run multi-query retrieval using LangChain's MultiQueryRetriever."""
    mq_retriever = _get_multi_query_retriever()
    if mq_retriever is None:
        logger.debug("Multi-query skipped — no documents in collection")
        return []

    try:
        mq_start = time.time()
        docs = mq_retriever.invoke(query)
        mq_elapsed = time.time() - mq_start
        logger.info("Multi-query done — expanded_docs=%d, elapsed=%.2fs", len(docs), mq_elapsed)
    except Exception as e:
        logger.error("Multi-query failed — %s", e)
        return []

    seen: dict[str, dict] = {}
    for doc in docs:
        meta = doc.metadata if hasattr(doc, "metadata") else {}
        chunk_key = _chunk_key(doc, meta)
        if chunk_key not in seen:
            seen[chunk_key] = {
                "id": meta.get("doc_id", chunk_key),
                "content": doc.page_content,
                "metadata": meta,
            }

    results = list(seen.values())[:n_results]
    logger.debug("Multi-query dedup — raw=%d, deduped=%d", len(docs), len(results))
    return results


def _chunk_key(doc: Document, meta: dict) -> str:
    """Unique key per chunk — keeps multiple chunks from the same doc."""
    doc_id = meta.get("doc_id", "unknown")
    chunk_index = meta.get("chunk_index")
    if chunk_index is not None:
        return f"{doc_id}::chunk_{chunk_index}"
    page = meta.get("page_number", meta.get("page", ""))
    section = meta.get("section", "")
    text_hash = hashlib.sha1(doc.page_content.encode("utf-8")).hexdigest()[:12]
    return f"{doc_id}::{page}::{section}::{text_hash}"


# ---------------------------------------------------------------------------
# Cross-encoder reranking
# ---------------------------------------------------------------------------

RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def _get_reranker():
    """Lazy-load cross-encoder reranker model."""
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        logger.info("Loading reranker — model=%s", RERANK_MODEL)
        _reranker = CrossEncoder(RERANK_MODEL)
        logger.info("Reranker ready")
    return _reranker


def _rerank(query: str, hits: list[dict], top_k: int = 5) -> list[dict]:
    """Rerank hits using cross-encoder. Returns top_k results."""
    if not hits:
        return hits

    reranker = _get_reranker()
    pairs = [(query, h["content"]) for h in hits]
    scores = reranker.predict(pairs)

    for hit, score in zip(hits, scores):
        hit["rerank_score"] = float(score)

    reranked = sorted(hits, key=lambda x: x["rerank_score"], reverse=True)[:top_k]
    logger.debug("Reranked — input=%d, output=%d", len(hits), len(reranked))
    return reranked


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def hybrid_retrieve(
    query: str,
    n_results: int = 10,
    doc_ids: list[str] | None = None,
    use_multi_query: bool = True,
    multi_query_n: int = 3,
) -> list[dict]:
    """
    Hybrid retrieval: BM25 + vector search with RRF fusion.
    Uses LangChain's MultiQueryRetriever for query expansion.

    Returns list of {id, content, metadata, rrf_score}.
    """
    total_start = time.time()
    logger.info(
        "Hybrid retrieval — q=%s, n=%d, doc_ids=%s, multi_query=%s",
        query[:60], n_results, doc_ids, use_multi_query,
    )

    # --- Vector search (direct ChromaDB query) ---
    v_start = time.time()
    v_results = vectorstore.query_documents(query_text=query, n_results=n_results, doc_ids=doc_ids)
    v_elapsed = time.time() - v_start
    vector_hits = []
    if v_results["documents"][0]:
        for doc, meta, dist in zip(
            v_results["documents"][0],
            v_results["metadatas"][0],
            v_results["distances"][0],
        ):
            vector_hits.append({
                "id": meta.get("doc_id", ""),
                "content": doc,
                "metadata": meta,
                "score": 1 - dist,
            })
    logger.debug("Vector search — hits=%d, elapsed=%.2fs", len(vector_hits), v_elapsed)

    # --- BM25 search ---
    bm25_start = time.time()
    bm25_hits = _bm25_search(query, k=n_results)
    if doc_ids:
        bm25_hits = [h for h in bm25_hits if h["metadata"].get("doc_id") in doc_ids]
    bm25_elapsed = time.time() - bm25_start
    logger.debug("BM25 search — hits=%d, elapsed=%.2fs", len(bm25_hits), bm25_elapsed)

    # --- Multi-query expansion (Tejasva's MultiQueryRetriever) ---
    mq_hits = []
    if use_multi_query:
        mq_start = time.time()
        mq_hits = _multi_query_retrieve(query, n_results=n_results)
        if doc_ids:
            mq_hits = [h for h in mq_hits if h["metadata"].get("doc_id") in doc_ids]
        mq_elapsed = time.time() - mq_start
        logger.debug("Multi-query — hits=%d, elapsed=%.2fs", len(mq_hits), mq_elapsed)

    # --- RRF fusion of all three ---
    all_vector = vector_hits + mq_hits
    fused = _rrf_fusion(all_vector, bm25_hits, top_n=n_results)

    # --- Cross-encoder reranking ---
    use_rerank = os.getenv("RERANK_ENABLED", "true").lower() == "true"
    if use_rerank and fused:
        rerank_start = time.time()
        fused = _rerank(query, fused, top_k=n_results)
        rerank_elapsed = time.time() - rerank_start
        logger.debug("Rerank — hits=%d, elapsed=%.2fs", len(fused), rerank_elapsed)

    total_elapsed = time.time() - total_start
    logger.info(
        "Retrieval complete — vector=%d, bm25=%d, mq=%d, fused=%d, elapsed=%.2fs",
        len(vector_hits), len(bm25_hits), len(mq_hits), len(fused), total_elapsed,
    )

    return fused
