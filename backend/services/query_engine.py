from __future__ import annotations

import os
from langchain_core.prompts import PromptTemplate
from .llm import get_llm
from .retriever import hybrid_retrieve

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

    results = hybrid_retrieve(
        query=question,
        n_results=5,
        doc_ids=doc_ids or None,
        use_multi_query=use_multi_query,
        multi_query_n=multi_query_n,
    )

    if not results:
        return {
            "answer": "I don't have that information in the provided documents.",
            "sources": [],
        }

    sources = []
    for r in results:
        sources.append({
            "content": r["content"],
            "metadata": r["metadata"],
            "rrf_score": r.get("rrf_score", 0),
        })

    context = "\n\n".join([r["content"] for r in results])
    llm = get_llm()
    prompt = PromptTemplate(template=SYSTEM_PROMPT, input_variables=["context", "question"])
    filled = prompt.format(context=context, question=question)
    answer = llm.invoke(filled)

    if hasattr(answer, "content"):
        answer = answer.content

    return {
        "answer": answer,
        "sources": sources,
    }
