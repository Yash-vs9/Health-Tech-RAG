from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    doc_ids: List[str] = Field(default_factory=list)


class Source(BaseModel):
    doc_id: str
    page: Optional[int] = None
    section: Optional[str] = None
    score: Optional[float] = None
    text: str


class QueryResponse(BaseModel):
    answer: str
    generated_queries: List[str]
    sources: List[Source]
