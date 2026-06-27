from __future__ import annotations

import os
import numpy as np
from langchain_core.documents import Document
from langchain_classic.retrievers.multi_query import MultiQueryRetriever
from .llm import get_llm
from . import vectorstore

# ---------------------------------------------------------------------------
# BM25 keyword retrieval
# ---------------------------------------------------------------------------

_bm25_index = None
_bm25_docs: list[dict] = []


def _build_bm25_index():
    """Build BM25 index from all documents in ChromaDB."""
    global _bm25_index, _bm25_docs

    collection = vectorstore.get_collection()
    count = collection.count()
    if count == 0:
        return

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
    except ImportError:
        _bm25_index = None


def _bm25_search(query: str, k: int = 10) -> list[dict]:
    """Keyword search using BM25."""
    global _bm25_index, _bm25_docs

    if _bm25_index is None:
        _build_bm25_index()
    if _bm25_index is None or not _bm25_docs:
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

    # Build langchain Chroma from existing collection
    from langchain_chroma import Chroma
    from .embeddings import get_embeddings

    embedding_fn = get_embeddings()
    vectorstore_lc = Chroma(
        client=vectorstore.get_client(),
        collection_name=collection.name,
        embedding_function=embedding_fn,
    )

    base_retriever = vectorstore_lc.as_retriever(search_kwargs={"k": 5})
    llm = get_llm()

    mq_retriever = MultiQueryRetriever.from_llm(
        retriever=base_retriever,
        llm=llm,
    )
    return mq_retriever


def _multi_query_retrieve(query: str, n_results: int = 10) -> list[dict]:
    """Run multi-query retrieval using LangChain's MultiQueryRetriever."""
    mq_retriever = _get_multi_query_retriever()
    if mq_retriever is None:
        return []

    try:
        docs = mq_retriever.invoke(query)
    except Exception:
        return []

    seen: dict[str, dict] = {}
    for doc in docs:
        meta = doc.metadata if hasattr(doc, "metadata") else {}
        doc_id = meta.get("doc_id", doc.page_content[:50])
        if doc_id not in seen:
            seen[doc_id] = {
                "id": doc_id,
                "content": doc.page_content,
                "metadata": meta,
            }

    return list(seen.values())[:n_results]


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
    # --- Vector search (direct ChromaDB query) ---
    v_results = vectorstore.query_documents(query_text=query, n_results=n_results, doc_ids=doc_ids)
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

    # --- BM25 search ---
    bm25_hits = _bm25_search(query, k=n_results)
    if doc_ids:
        bm25_hits = [h for h in bm25_hits if h["metadata"].get("doc_id") in doc_ids]

    # --- Multi-query expansion (Tejasva's MultiQueryRetriever) ---
    mq_hits = []
    if use_multi_query:
        mq_hits = _multi_query_retrieve(query, n_results=n_results)
        if doc_ids:
            mq_hits = [h for h in mq_hits if h["metadata"].get("doc_id") in doc_ids]

    # --- RRF fusion of all three ---
    all_vector = vector_hits + mq_hits
    fused = _rrf_fusion(all_vector, bm25_hits, top_n=n_results)
    return fused
