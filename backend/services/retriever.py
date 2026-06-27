from __future__ import annotations

import os
import numpy as np
from langchain_core.prompts import PromptTemplate
from .llm import get_llm
from . import vectorstore

# ---------------------------------------------------------------------------
# BM25 keyword retrieval
# ---------------------------------------------------------------------------

_bm25_index = None
_bm25_docs: list[dict] = []  # [{id, content, metadata}]


def _build_bm25_index():
    """Build BM25 index from all documents in ChromaDB."""
    global _bm25_index, _bm25_docs

    collection = vectorstore.get_collection()
    count = collection.count()
    if count == 0:
        return

    # Fetch all docs in batches (ChromaDB limit)
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
        try:
            nltk.data.find("tokenizers/punkt_tab")
        except LookupError:
            nltk.download("punkt_tab", quiet=True)
        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            nltk.download("punkt", quiet=True)

        tokenized = [nltk.word_tokenize(doc.lower()) for doc in all_docs]
        _bm25_index = BM25Okapi(tokenized)
    except ImportError:
        _bm25_index = None


def _bm25_search(query: str, k: int = 10) -> list[dict]:
    """Keyword search using BM25. Returns list of {id, content, metadata, score}."""
    global _bm25_index, _bm25_docs

    if _bm25_index is None:
        _build_bm25_index()
    if _bm25_index is None or not _bm25_docs:
        return []

    import nltk
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab", quiet=True)
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt", quiet=True)

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
# Multi-query reformulation
# ---------------------------------------------------------------------------

MULTI_QUERY_PROMPT = PromptTemplate.from_template(
    """You are a mortgage document retrieval assistant. Given the user question, generate {n} diverse reformulations that would help find relevant mortgage/compliance documents. Each reformulation should approach the topic from a different angle.

Original question: {question}

Return ONLY the reformulated questions, one per line, no numbering or bullets:"""
)


def _generate_queries(question: str, n: int = 3) -> list[str]:
    """Use LLM to generate N reformulated queries."""
    llm = get_llm()
    prompt = MULTI_QUERY_PROMPT.format(question=question, n=n)
    response = llm.invoke(prompt)
    if hasattr(response, "content"):
        response = response.content
    queries = [q.strip().lstrip("0123456789.-) ") for q in response.strip().split("\n") if q.strip()]
    return queries[:n]


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
    Optionally uses multi-query reformulation.

    Returns list of {id, content, metadata, rrf_score, source}.
    """
    all_results: list[dict] = []

    if use_multi_query:
        queries = _generate_queries(query, n=multi_query_n)
        all_queries = [query] + queries
    else:
        all_queries = [query]

    for q in all_queries:
        # Vector search
        v_results = vectorstore.query_documents(query_text=q, n_results=n_results, doc_ids=doc_ids)
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
                    "score": 1 - dist,  # cosine distance → similarity
                })

        # BM25 search
        bm25_hits = _bm25_search(q, k=n_results)
        if doc_ids:
            bm25_hits = [h for h in bm25_hits if h["metadata"].get("doc_id") in doc_ids]

        # Fuse with RRF
        fused = _rrf_fusion(vector_hits, bm25_hits, top_n=n_results)
        all_results.extend(fused)

    # Deduplicate across all queries by doc_id, keep highest RRF score
    seen: dict[str, dict] = {}
    for r in all_results:
        doc_id = r["id"]
        if doc_id not in seen or r["rrf_score"] > seen[doc_id]["rrf_score"]:
            seen[doc_id] = r

    final = sorted(seen.values(), key=lambda x: x["rrf_score"], reverse=True)[:n_results]
    return final
