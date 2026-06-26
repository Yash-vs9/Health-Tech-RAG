from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import Any, Dict, Iterable, List, Sequence


@dataclass(frozen=True)
class CorpusChunk:
    doc_id: str
    page: int
    section: str
    text: str


@dataclass
class RetrievedChunk:
    doc_id: str
    text: str
    page: int | None = None
    section: str | None = None
    score: float | None = None


class MultiQueryService:
    _STOPWORDS = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "by",
        "do",
        "does",
        "for",
        "from",
        "had",
        "has",
        "have",
        "how",
        "i",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "our",
        "should",
        "that",
        "the",
        "their",
        "there",
        "to",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
        "would",
        "could",
        "was",
        "were",
        "will",
        "you",
        "your",
    }

    def __init__(self) -> None:
        self._corpus: List[CorpusChunk] = [
            CorpusChunk(
                doc_id="who_health_guidelines.pdf",
                page=12,
                section="Type 2 diabetes",
                text=(
                    "Type 2 diabetes commonly presents with increased thirst, frequent urination, fatigue, "
                    "and blurred vision."
                ),
            ),
            CorpusChunk(
                doc_id="who_health_guidelines.pdf",
                page=13,
                section="Complications",
                text=(
                    "Early diagnosis helps reduce the risk of kidney, nerve, and eye complications. "
                    "Follow-up care is important after abnormal test results."
                ),
            ),
            CorpusChunk(
                doc_id="who_health_guidelines.pdf",
                page=14,
                section="Prevention",
                text="Regular screening is recommended for adults with risk factors and family history.",
            ),
            CorpusChunk(
                doc_id="medical_report.pdf",
                page=8,
                section="Nutrition",
                text=(
                    "Balanced meals, portion control, and limiting high-sugar foods can help patients manage "
                    "blood sugar levels."
                ),
            ),
        ]
        self._default_top_k = 3

    def generate_queries(self, question: str) -> List[str]:
        normalized = question.strip()
        query_variants = [normalized]
        query_variants.append(f"medical evidence for {normalized}")
        query_variants.append(f"health document citations for {normalized}")

        lowered = normalized.lower()
        if "symptom" in lowered or "sign" in lowered:
            query_variants.append(f"type 2 diabetes symptoms signs {normalized}")
        if "complication" in lowered or "follow" in lowered:
            query_variants.append(f"diagnosis complications follow-up {normalized}")
        if "screen" in lowered or "risk" in lowered:
            query_variants.append(f"screening risk factors prevention {normalized}")
        if "nutrition" in lowered or "blood sugar" in lowered:
            query_variants.append(f"diet blood sugar management {normalized}")

        deduplicated: List[str] = []
        seen = set()
        for variant in query_variants:
            key = variant.lower()
            if key not in seen:
                deduplicated.append(variant)
                seen.add(key)
        return deduplicated[:3]

    def retrieve(self, generated_queries: List[str], doc_ids: List[str]) -> List[RetrievedChunk]:
        allowed_doc_ids = set(doc_ids) if doc_ids else None
        ranked: Dict[tuple[str, int, str], RetrievedChunk] = {}

        for query in generated_queries:
            for chunk, score in self._score_query_against_corpus(query, self._corpus):
                if allowed_doc_ids and chunk.doc_id not in allowed_doc_ids:
                    continue
                key = (chunk.doc_id, chunk.page, chunk.section)
                current = ranked.get(key)
                if current is None or (current.score or 0.0) < score:
                    ranked[key] = RetrievedChunk(
                        doc_id=chunk.doc_id,
                        page=chunk.page,
                        section=chunk.section,
                        score=round(score, 3),
                        text=chunk.text,
                    )

        results = sorted(
            ranked.values(),
            key=lambda chunk: (chunk.score or 0.0, -chunk.page),
            reverse=True,
        )
        return results[: self._default_top_k]

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

    def _compose_answer(self, question: str, sources: Sequence[RetrievedChunk]) -> str:
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

    @staticmethod
    def _score_query_against_corpus(
        query: str,
        corpus: Iterable[CorpusChunk],
    ) -> List[tuple[CorpusChunk, float]]:
        query_tokens = MultiQueryService._tokenize(query)
        if not query_tokens:
            return []

        query_bigrams = MultiQueryService._bigrams(query_tokens)
        ranked: List[tuple[CorpusChunk, float]] = []
        for chunk in corpus:
            chunk_tokens = MultiQueryService._tokenize(chunk.text)
            chunk_token_counts = Counter(chunk_tokens)
            overlap = sum(min(chunk_token_counts[token], 1) for token in query_tokens)
            chunk_bigrams = MultiQueryService._bigrams(chunk_tokens)
            phrase_overlap = len(query_bigrams & chunk_bigrams)

            score = overlap / max(len(query_tokens), 1)
            score += phrase_overlap * 0.3

            query_lower = query.lower()
            text_lower = chunk.text.lower()
            if any(keyword in query_lower for keyword in ("symptom", "sign")) and any(
                keyword in text_lower for keyword in ("symptom", "frequent urination", "fatigue")
            ):
                score += 0.6
            if any(keyword in query_lower for keyword in ("complication", "follow")) and any(
                keyword in text_lower for keyword in ("complication", "follow-up", "diagnosis")
            ):
                score += 0.6
            if any(keyword in query_lower for keyword in ("screen", "risk")) and any(
                keyword in text_lower for keyword in ("screening", "risk factors")
            ):
                score += 0.6
            if any(keyword in query_lower for keyword in ("nutrition", "blood sugar")) and any(
                keyword in text_lower for keyword in ("balanced meals", "portion control", "high-sugar")
            ):
                score += 0.6

            if score > 0:
                ranked.append((chunk, score))

        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        tokens = re.findall(r"[a-z0-9']+", text.lower())
        return [token for token in tokens if token not in MultiQueryService._STOPWORDS]

    @staticmethod
    def _bigrams(tokens: Sequence[str]) -> set[tuple[str, str]]:
        return {(tokens[index], tokens[index + 1]) for index in range(len(tokens) - 1)}
