from __future__ import annotations

import os
import time
from langchain_core.prompts import PromptTemplate
from backend.logging_config import get_logger
from .llm import get_llm
from .retriever import hybrid_retrieve

logger = get_logger("backend.query_engine")

SYSTEM_PROMPT = """You are a mortgage document intelligence assistant.
Answer only from the provided mortgage-related documents.
Always cite the source document, page number, and section when available.
Think step by step before answering.
If the answer is not found in the provided context,
respond with: 'I don't have that information in the provided documents.'
Do not fabricate loan terms, rates, or compliance requirements.
Do not provide legal or financial advice — only retrieve and summarize document content.

Context:
{context}

Question: {question}
Answer:"""


def query_rag(question: str, doc_ids: list[str] | None = None) -> dict:
    use_multi_query = os.getenv("MULTI_QUERY_ENABLED", "true").lower() == "true"
    multi_query_n = int(os.getenv("MULTI_QUERY_N", "3"))

    logger.info(
        "RAG query — q=%s, doc_ids=%s, multi_query=%s (n=%d)",
        question[:80], doc_ids, use_multi_query, multi_query_n,
    )

    # Retrieve
    retrieve_start = time.time()
    results = hybrid_retrieve(
        query=question,
        n_results=5,
        doc_ids=doc_ids or None,
        use_multi_query=use_multi_query,
        multi_query_n=multi_query_n,
    )
    retrieve_elapsed = time.time() - retrieve_start
    logger.info("Retrieval done — chunks=%d, elapsed=%.2fs", len(results), retrieve_elapsed)

    if not results:
        logger.info("No results found — returning refusal")
        return {
            "answer": "I don't have that information in the provided documents.",
            "sources": [],
        }

    # Log retrieval scores
    for i, r in enumerate(results):
        logger.debug(
            "  chunk[%d] — doc_id=%s, rrf_score=%.4f, content_len=%d",
            i, r.get("id", "?"), r.get("rrf_score", 0), len(r.get("content", "")),
        )

    sources = []
    for r in results:
        sources.append({
            "content": r["content"],
            "metadata": r["metadata"],
            "rrf_score": r.get("rrf_score", 0),
        })

    # Build context
    context = "\n\n".join([r["content"] for r in results])
    logger.debug("Context built — chars=%d, chunks=%d", len(context), len(results))

    # LLM call
    llm = get_llm()
    prompt = PromptTemplate(template=SYSTEM_PROMPT, input_variables=["context", "question"])
    filled = prompt.format(context=context, question=question)
    logger.debug("Prompt built — tokens≈%d", len(filled.split()))

    llm_start = time.time()
    answer = llm.invoke(filled)
    llm_elapsed = time.time() - llm_start

    if hasattr(answer, "content"):
        answer = answer.content

    logger.info(
        "LLM response — answer_len=%d, elapsed=%.2fs",
        len(answer), llm_elapsed,
    )

    return {
        "answer": answer,
        "sources": sources,
    }
