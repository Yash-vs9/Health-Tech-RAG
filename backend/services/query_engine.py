from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.language_models.fake import FakeListLLM
from langchain_classic.retrievers.multi_query import MultiQueryRetriever


@dataclass
class RetrievedChunk:
    doc_id: str
    text: str
    page: int | None = None
    section: str | None = None
    score: float | None = None


class MultiQueryService:
    def __init__(self) -> None:
        self._embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self._documents = self._build_documents()
        self._vectorstore = Chroma.from_documents(
            documents=self._documents,
            embedding=self._embedding_model,
            collection_name="tejasva_multiquery_health",
        )
        self._base_retriever = self._vectorstore.as_retriever(search_kwargs={"k": 5})
        self._llm = self._build_llm()
        self._multi_query_retriever = MultiQueryRetriever.from_llm(
            retriever=self._base_retriever,
            llm=self._llm,
        )

    def generate_queries(self, question: str) -> List[str]:
        return self._build_generated_queries(question)

    def retrieve(self, generated_queries: List[str], doc_ids: List[str]) -> List[RetrievedChunk]:
        allowed_doc_ids = set(doc_ids) if doc_ids else None
        retrieved_documents = self._multi_query_retriever.invoke(generated_queries[0])
        ranked: Dict[tuple[str, int | None, str | None], RetrievedChunk] = {}

        for index, document in enumerate(retrieved_documents):
            metadata = document.metadata or {}
            doc_id = str(metadata.get("doc_id", "unknown"))
            if allowed_doc_ids and doc_id not in allowed_doc_ids:
                continue

            key = (doc_id, metadata.get("page"), metadata.get("section"))
            score = self._score_document(document, generated_queries)
            if score <= 0:
                continue
            current = ranked.get(key)
            if current is None or (current.score or 0.0) < score:
                ranked[key] = RetrievedChunk(
                    doc_id=doc_id,
                    page=metadata.get("page"),
                    section=metadata.get("section"),
                    score=round(score, 3),
                    text=document.page_content,
                )

        results = sorted(
            ranked.values(),
            key=lambda chunk: (chunk.score or 0.0, -(chunk.page or 0)),
            reverse=True,
        )
        return results[:5]

    def answer_question(self, question: str, doc_ids: List[str]) -> Dict[str, Any]:
        generated_queries = self.generate_queries(question)
        sources = self.retrieve(generated_queries, doc_ids)

        if not sources:
            return {
                "answer": "I don't have that information in the provided documents.",
                "generated_queries": generated_queries,
                "sources": [],
            }

        answer = self._compose_answer(question, sources)
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

    def _build_llm(self):
        return FakeListLLM(
            responses=[
                "1. type 2 diabetes symptoms\n2. diabetes complications\n3. diabetes screening",
                "1. medical evidence\n2. health document citations\n3. patient screening",
                "1. symptom query\n2. complication query\n3. screening query",
            ]
        )

    @staticmethod
    def _build_documents() -> List[Document]:
        return [
            Document(
                page_content=(
                    "Type 2 diabetes commonly presents with increased thirst, frequent urination, fatigue, "
                    "and blurred vision."
                ),
                metadata={"doc_id": "who_health_guidelines.pdf", "page": 12, "section": "Type 2 diabetes"},
            ),
            Document(
                page_content=(
                    "Early diagnosis helps reduce the risk of kidney, nerve, and eye complications. Follow-up "
                    "care is important after abnormal test results."
                ),
                metadata={"doc_id": "who_health_guidelines.pdf", "page": 13, "section": "Complications"},
            ),
            Document(
                page_content=(
                    "Regular screening is recommended for adults with risk factors and family history."
                ),
                metadata={"doc_id": "who_health_guidelines.pdf", "page": 14, "section": "Prevention"},
            ),
            Document(
                page_content=(
                    "Balanced meals, portion control, and limiting high-sugar foods can help patients manage blood sugar levels."
                ),
                metadata={"doc_id": "medical_report.pdf", "page": 8, "section": "Nutrition"},
            ),
        ]

    @staticmethod
    def _build_generated_queries(question: str) -> List[str]:
        normalized = question.strip()
        return [
            normalized,
            f"medical evidence for {normalized}",
            f"health document citations for {normalized}",
        ]

    @staticmethod
    def _score_document(document: Document, generated_queries: Sequence[str]) -> float:
        text = document.page_content.lower()
        score = 0.0
        for query in generated_queries:
            query_lower = query.lower()
            if "symptom" in query_lower and any(
                keyword in text for keyword in ("symptom", "frequent urination", "fatigue", "blurred vision")
            ):
                score += 1.0
            if "complication" in query_lower and any(
                keyword in text for keyword in ("complication", "follow-up", "diagnosis")
            ):
                score += 1.0
            if "screen" in query_lower and any(keyword in text for keyword in ("screening", "risk factors")):
                score += 1.0
            if "nutrition" in query_lower and any(
                keyword in text for keyword in ("balanced meals", "portion control", "high-sugar")
            ):
                score += 1.0
        return score

    @staticmethod
    def _compose_answer(question: str, sources: Sequence[RetrievedChunk]) -> str:
        question_lower = question.lower()
        top_texts = [source.text for source in sources[:2]]

        if "symptom" in question_lower or "sign" in question_lower:
            return top_texts[0]
        if "complication" in question_lower or "follow" in question_lower:
            return " ".join(top_texts[:2])
        if "screen" in question_lower or "risk" in question_lower:
            return top_texts[0]
        if "nutrition" in question_lower or "blood sugar" in question_lower:
            return top_texts[0]
        return " ".join(top_texts)
