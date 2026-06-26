from __future__ import annotations

import os
from langchain_core.prompts import PromptTemplate
from .llm import get_llm
from . import vectorstore

SYSTEM_PROMPT = """You are a health information assistant.
Answer only from the provided medical documents.
Always cite the source document and page number.
Think step by step before answering.
If the answer is not found in the provided context,
respond with: 'I don't have that information in the provided documents.'
Do not make up medical information.
Do not provide personal medical advice.

Context:
{context}

Question: {question}
Answer:"""


def query_rag(question: str, doc_ids: list[str] | None = None) -> dict:
    results = vectorstore.query_documents(query_text=question, n_results=5, doc_ids=doc_ids or None)

    if not results["documents"][0]:
        return {
            "answer": "I don't have that information in the provided documents.",
            "sources": [],
        }

    sources = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        sources.append({
            "content": doc,
            "metadata": meta,
            "distance": dist,
        })

    context = "\n\n".join(results["documents"][0])
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
