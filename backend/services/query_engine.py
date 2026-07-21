"""
RAG query pipeline — retrieve, rerank, and generate an answer.

This is the core query engine. It takes a user question, runs it through
safety guardrails, retrieves relevant chunks via hybrid search, generates
an answer with citations, and filters sources to only those cited.

Pipeline:
    1. Input guardrails (regex — injection, jailbreak, harmful)
    2. NeMo Guardrails (LLM-based — mortgage domain + safety)
    3. Greeting detection (short-circuit for small talk)
    4. Multi-query expansion (N=3 reformulated queries)
    5. Hybrid retrieval (Vector + BM25 + Multi-Query)
    6. RRF fusion + CrossEncoder reranking
    7. Build context with citation tags
    8. LLM call (NVIDIA NIM — meta/llama-3.1-70b-instruct)
    9. Output guardrails (prompt leakage, length)
    10. Citation filtering (parse [Source N] tags, match to chunks)

Functions:
    query_rag(question, doc_ids, conversation_context) -> dict
        Returns: {"answer": str, "sources": list[dict], "blocked"?: bool}

System prompt:
    Enforces mortgage-domain-only responses, mandatory citation format:
    [Source N: filename.pdf, Page X, Section: Section Name]
"""

from __future__ import annotations

import os
import re
import time
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import PromptTemplate
from backend.logging_config import get_logger
from .llm import get_llm
from .retriever import hybrid_retrieve
from .guardrails import get_input_guardrails, get_output_guardrails, get_nemo_guardrails

logger = get_logger("backend.query_engine")

# Patterns that indicate greetings / small talk (skip retrieval)
_GREETING_PATTERN = re.compile(
    r"^\s*(hi|hello|hey|howdy|good\s*(morning|afternoon|evening|day)"
    r"|greetings|sup|yo|hola|namaste|what'?s\s*up"
    r"|thanks|thank\s*you|thx|bye|goodbye|see\s*ya|later"
    r"|how\s*are\s*you|what\s*can\s*you\s*do|who\s*are\s*you"
    r"|help|start|menu)\s*[!.?]*\s*$",
    re.IGNORECASE,
)

SYSTEM_PROMPT = """You are a Mortgage Document Assistant — a friendly, helpful chatbot for mortgage-related questions.

Behavior:
- For greetings (hi, hello, hey, good morning, etc.), respond warmly and briefly introduce yourself. Do NOT cite sources for greetings.
- For small talk (how are you, what can you do, thanks, goodbye, etc.), respond naturally and guide the user toward asking mortgage questions.
- For mortgage-related questions, answer ONLY from the provided documents with source citations.

Learning from Feedback:
- Look for [USER_RATING: POSITIVE] or [USER_RATING: NEGATIVE] markers in conversation history.
- POSITIVE rating: The user found that answer helpful. Match the style, format, and detail level.
- NEGATIVE rating: The user found that answer unhelpful. Common issues to fix:
  * Missing or weak source citations → add more specific citations with page/section
  * Too verbose → be more concise and direct
  * Too brief → add more detail and context
  * Unclear → simplify language and structure
  * Wrong information → double-check facts against provided documents
- [CONVERSATION_FEEDBACK_SUMMARY] shows overall satisfaction — use this to gauge if you're on the right track.

Rules for mortgage questions:
1. Carefully read ALL the provided context chunks. The answer may span multiple chunks — piece it together.
2. Extract exact figures, dates, and names from the context. Do not round numbers.
3. Never use external knowledge or assumptions. Stay strictly within the provided documents.
4. **CITATION FORMAT (MANDATORY):** Every fact MUST be followed by a citation in this exact format:
   [Source N: filename.pdf, Page X, Section: Section Name]
   - N = the source number from the context (1-based)
   - filename.pdf = the document filename from the source metadata
   - Page X = the page number from the source metadata
   - Section: Section Name = the section from the source metadata
   Example: [Source 1: ABC_Bank_Annual_Report_2024_Full.pdf, Page 15, Section: 11. BUSINESS SEGMENT REVIEW]
5. If you cannot find the answer after thoroughly checking ALL context chunks, reply:
   "I don't have that information in the provided documents."
6. Do not make up information.

Few-shot Examples:

Example 1: Greeting
Question: hi
Answer: Hello! I'm your Mortgage Document Assistant. I can help you find information from your mortgage documents — things like loan terms, fees, rates, and compliance requirements. What would you like to know?

Example 2: Factual Lookup with Citation
Question: What is the late fee percentage for PNB Housing loan?
Answer: The late fee is 2% per month on the overdue amount [Source 1: PNB_Housing_Loan_Agreement.pdf, Page 14, Section: 4.2 - Late Payment Charges].

Example 3: Refusal
Question: What is the current RBI repo rate?
Answer: I don't have that information in the provided documents.

Example 4: Comparison Across Documents
Question: Which bank charges a lower processing fee — PNB or HDFC?
Answer: PNB Housing charges a 0.50% processing fee [Source 1: PNB_Housing_Annual_Report.pdf, Page 8, Section: Processing Fee], while HDFC charges 0.75% [Source 2: HDFC_Annual_Report.pdf, Page 22, Section: Loan Processing Charges]. PNB Housing has the lower processing fee.

Example 5: Small Talk
Question: what can you do?
Answer: I can help you find information from your uploaded mortgage documents — loan terms, interest rates, fees, compliance requirements, and more. Just ask a question about your mortgage documents and I'll look it up for you!"""

USER_PROMPT = """Context:
{context}

Question: {question}
Answer:"""


async def query_rag(question: str, doc_ids: list[str] | None = None, conversation_context: str = "") -> dict:
    # ── Input guardrails ────────────────────────────────────────────────
    input_guard = get_input_guardrails()
    guard_result = input_guard.check(question)
    if not guard_result.passed:
        logger.warning(
            "Input blocked by guardrails — reason=%s, severity=%s",
            guard_result.reason, guard_result.severity,
        )
        return {
            "answer": guard_result.reason,
            "sources": [],
            "blocked": True,
        }

    # ── NeMo input safety check (injection/jailbreak) ─────────────────
    nemo = get_nemo_guardrails()
    nemo_blocked = await nemo.check_input(question)
    if nemo_blocked is not None:
        logger.warning("Input blocked by NeMo Guardrails")
        return {
            "answer": nemo_blocked,
            "sources": [],
            "blocked": True,
        }

    # ── Greeting / small talk short-circuit (skip retrieval) ───────────
    if _GREETING_PATTERN.match(question):
        logger.info("Greeting detected — skipping retrieval")
        llm = get_llm()
        greeting_prompt = (
            "You are a friendly Mortgage Document Assistant. "
            "Respond warmly to the user's greeting. Keep it short (1-2 sentences). "
            "If appropriate, mention what you can help with.\n\n"
            f"User: {question}\nAssistant:"
        )
        llm_start = time.time()
        answer = llm.invoke(greeting_prompt)
        llm_elapsed = time.time() - llm_start
        if hasattr(answer, "content"):
            answer = answer.content
        logger.info("Greeting response — len=%d, elapsed=%.2fs", len(answer), llm_elapsed)
        return {
            "answer": answer,
            "sources": [],
        }

    use_multi_query = os.getenv("MULTI_QUERY_ENABLED", "true").lower() == "true"
    multi_query_n = int(os.getenv("MULTI_QUERY_N", "3"))
    retrieve_k = int(os.getenv("RETRIEVER_TOP_K", "10"))

    logger.info(
        "RAG query — q=%s, doc_ids=%s, multi_query=%s (n=%d), top_k=%d",
        question[:80], doc_ids, use_multi_query, multi_query_n, retrieve_k,
    )

    # Retrieve
    retrieve_start = time.time()
    results = hybrid_retrieve(
        query=question,
        n_results=retrieve_k,
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

    # LLM call with proper SystemMessage + HumanMessage
    llm = get_llm()
    user_prompt = PromptTemplate(template=USER_PROMPT, input_variables=["context", "question"])
    user_content = user_prompt.format(context=context, question=question)
    logger.debug("Prompt built — tokens≈%d", len(user_content.split()))

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]

    llm_start = time.time()
    answer = llm.invoke(messages)
    llm_elapsed = time.time() - llm_start

    if hasattr(answer, "content"):
        answer = answer.content

    # ── Output guardrails ──────────────────────────────────────────────
    output_guard = get_output_guardrails()
    out_result = output_guard.check(answer)
    if not out_result.passed:
        logger.warning(
            "Output blocked by guardrails — reason=%s", out_result.reason,
        )
        answer = out_result.reason
    else:
        answer = output_guard.sanitize(answer)
        if out_result.reason:
            logger.info("Output guardrail note — %s", out_result.reason)

    logger.info(
        "LLM response — answer_len=%d, elapsed=%.2fs",
        len(answer), llm_elapsed,
    )

    # ── Filter sources to only those cited in the answer ─────────────
    cited_indices = set()

    # Extract all citations from answer: [Source N: filename.pdf, Page X, Section: ...]
    citation_pattern = r"\[Source\s+(\d+):\s+([^\],]+),\s*Page\s+(\d+)(?:,\s*Section:\s*([^\]]+))?\]"
    citations = []
    for match in re.finditer(citation_pattern, answer, re.IGNORECASE):
        source_num = int(match.group(1))
        filename = match.group(2).strip()
        page = int(match.group(3))
        section = match.group(4).strip() if match.group(4) else None
        citations.append({
            "source_num": source_num,
            "filename": filename,
            "page": page,
            "section": section,
        })
        logger.debug("Citation parsed — source_num=%d, filename=%s, page=%d, section=%s", 
                     source_num, filename, page, section)

    # Match citations to sources by filename + page (not by index!)
    for citation in citations:
        for i, s in enumerate(sources):
            meta = s.get("metadata", {})
            src_filename = meta.get("filename", "")
            src_page = meta.get("page_number", meta.get("page"))
            
            filename_match = citation["filename"].lower() == src_filename.lower()
            page_match = str(src_page) == str(citation["page"]) if src_page is not None else False
            
            if filename_match and page_match:
                cited_indices.add(i)
                logger.debug("Matched citation to source index %d — filename=%s, page=%d", 
                             i, src_filename, src_page)
                break
        else:
            # Fallback: try just filename match (but ONLY for the specific cited source)
            for i, s in enumerate(sources):
                meta = s.get("metadata", {})
                src_filename = meta.get("filename", "")
                if citation["filename"].lower() == src_filename.lower():
                    # Only add if this source's page matches the citation's page OR if it's the only source with this filename
                    src_page = meta.get("page_number", meta.get("page"))
                    if str(src_page) == str(citation["page"]) or src_page is None:
                        cited_indices.add(i)
                        logger.debug("Fallback filename match — index=%d, filename=%s", i, src_filename)
                        break

    # Match page numbers mentioned near document references (but only if already in cited_indices or filename matches)
    for match in re.finditer(r"[Pp]age\s+(\d+)", answer):
        page_num = int(match.group(1))
        for i, s in enumerate(sources):
            meta = s.get("metadata", {})
            src_page = meta.get("page_number", meta.get("page"))
            if src_page is not None:
                try:
                    if int(src_page) == page_num:
                        # Only add if this source's filename was already cited
                        meta = s.get("metadata", {})
                        src_filename = meta.get("filename", "")
                        # Check if any citation mentions this filename
                        for citation in citations:
                            if citation["filename"].lower() == src_filename.lower():
                                cited_indices.add(i)
                                logger.debug("Page match with cited filename — index=%d, page=%d", i, page_num)
                                break
                except (ValueError, TypeError):
                    pass

    logger.info("Cited indices after filtering: %s", cited_indices)
    if cited_indices:
        filtered_sources = [s for i, s in enumerate(sources) if i in cited_indices]
        
        # Deduplicate by filename + page (keep highest scored chunk per page)
        seen_pages = {}  # key: (filename, page) -> source
        for s in filtered_sources:
            meta = s.get("metadata", {})
            filename = meta.get("filename", "")
            page = meta.get("page_number", meta.get("page", "unknown"))
            key = (filename, page)
            if key not in seen_pages or s.get("rrf_score", 0) > seen_pages[key].get("rrf_score", 0):
                seen_pages[key] = s
        
        # Convert back to list and sort by score
        filtered_sources = list(seen_pages.values())
        filtered_sources.sort(key=lambda x: x.get("rrf_score", 0), reverse=True)
        logger.info("Filtered sources (deduped by filename+page) — cited=%d, total=%d", len(filtered_sources), len(sources))
    else:
        # No citations found — return top 3 by reranker score
        filtered_sources = sorted(sources, key=lambda x: x.get("rrf_score", 0), reverse=True)[:3]
        logger.info("No citations found — returning top 3 by score")

    return {
        "answer": answer,
        "sources": filtered_sources,
    }
