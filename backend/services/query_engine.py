from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class RetrievedChunk:
    doc_id: str
    text: str
    page: int | None = None
    section: str | None = None
    score: float | None = None


class MultiQueryService:
    def __init__(self) -> None:
        self._seed_docs = [
            RetrievedChunk(
                doc_id="who_health_guidelines.pdf",
                page=12,
                section="Type 2 diabetes",
                score=0.93,
                text="Common symptoms include increased thirst, frequent urination, and fatigue.",
            ),
            RetrievedChunk(
                doc_id="who_health_guidelines.pdf",
                page=13,
                section="Complications",
                score=0.89,
                text="Early diagnosis helps reduce the risk of kidney, nerve, and eye complications.",
            ),
            RetrievedChunk(
                doc_id="who_health_guidelines.pdf",
                page=14,
                section="Prevention",
                score=0.88,
                text="Regular screening is recommended for adults with risk factors.",
            ),
        ]

    def generate_queries(self, question: str) -> List[str]:
        return [
            question,
            f"What evidence in the documents answers: {question}",
            f"Find supporting health document sections for: {question}",
        ]

    def retrieve(self, generated_queries: List[str], doc_ids: List[str]) -> List[RetrievedChunk]:
        allowed_doc_ids = set(doc_ids) if doc_ids else None
        results: List[RetrievedChunk] = []
        for chunk in self._seed_docs:
            if allowed_doc_ids and chunk.doc_id not in allowed_doc_ids:
                continue
            results.append(chunk)
        return results

    def answer_question(self, question: str, doc_ids: List[str]) -> Dict[str, Any]:
        generated_queries = self.generate_queries(question)
        sources = self.retrieve(generated_queries, doc_ids)
        answer = (
            "Common symptoms include increased thirst, frequent urination, and fatigue. "
            "Early diagnosis helps reduce complications."
        )
        return {
            "answer": answer,
            "generated_queries": generated_queries,
            "sources": [
                {
                    "doc_id": source.doc_id,
                    "page": source.page,
                    "section": source.section,
                    "score": source.score,
                    "text": source.text,
                }
                for source in sources
            ],
        }
