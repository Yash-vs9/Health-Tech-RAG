from __future__ import annotations

import os
import time
from langchain_core.prompts import PromptTemplate
from backend.logging_config import get_logger
from .llm import get_llm
from .retriever import hybrid_retrieve

logger = get_logger("backend.query_engine")

SYSTEM_PROMPT = """You are a Mortgage Document Assistant.

Your role is to answer mortgage-related questions only from the provided mortgage documents.

Rules:
1. Answer only from the provided documents.
2. Never use external knowledge or assumptions.
3. Every factual answer must include the source document name, page number, and section whenever available.
4. Keep answers short and precise (2-4 sentences maximum).
5. If the answer is not found in the provided documents, reply exactly:
   "I don't have that information in the provided documents."
6. Do not make up information.
7. Never include information that is not supported by the provided documents.

Few-shot Examples:

Example 1: Factual Lookup with Citation
Question: What is the late fee percentage for PNB Housing loan?
Answer: The late fee is 2% per month on the overdue amount, as stated in the PNB Housing Loan Agreement (Page 14, Section 4.2 - Late Payment Charges).

Example 2: Refusal
Question: What is the current RBI repo rate?
Answer: I don't have that information in the provided documents.

Example 3: Comparison Across Documents
Question: Which bank charges a lower processing fee — PNB or HDFC?
Answer: PNB Housing charges a 0.50% processing fee (PNB Housing Annual Report, Page 8, Section: Processing Fee), while HDFC charges 0.75% (HDFC Annual Report, Page 22, Section: Loan Processing Charges). PNB Housing has the lower processing fee.

Example 4: Summary Request
Question: Summarize the RESPA disclosure requirements.
Answer: Based on the RBI KYC Document (Pages 5–7, Section: Disclosure Requirements):
1. Lenders must provide the loan estimate within 3 business days of application.
2. Closing disclosure must be provided 3 business days before closing.
3. Borrowers have the right to cancel within 3 business days of closing.

Context:
{context}

Question: {question}
Answer:"""


def query_rag(question: str, doc_ids: list[str] | None = None, conversation_context: str = "") -> dict:
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

    # Build context with metadata for citation
    context_parts = []
    for i, r in enumerate(results):
        meta = r["metadata"]
        page = meta.get("page_number", meta.get("page", "?"))
        section = meta.get("section", "")
        filename = meta.get("filename", "unknown")
        source_tag = f"[Source {i+1}: {filename}, Page {page}"
        if section:
            source_tag += f", Section: {section}"
        source_tag += "]"
        context_parts.append(f"{source_tag}\n{r['content']}")
    context = "\n\n".join(context_parts)
    logger.debug("Context built — chars=%d, chunks=%d", len(context), len(results))

    # Log full context at DEBUG level for troubleshooting
    for i, r in enumerate(results):
        logger.debug("  chunk[%d] content: %s", i, r["content"][:300])

    # Prepend conversation history if available
    if conversation_context:
        context = f"Conversation history:\n{conversation_context}\n\nRelevant documents:\n{context}"

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
