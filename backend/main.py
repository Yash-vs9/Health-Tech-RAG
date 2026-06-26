from __future__ import annotations

from fastapi import FastAPI

from backend.schemas import QueryRequest, QueryResponse, Source
from backend.services.query_engine import MultiQueryService

app = FastAPI(title="Health RAG API")
service = MultiQueryService()


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    result = service.answer_question(request.question, request.doc_ids)
    return QueryResponse(
        answer=result["answer"],
        generated_queries=result["generated_queries"],
        sources=[Source(**source) for source in result["sources"]],
    )
